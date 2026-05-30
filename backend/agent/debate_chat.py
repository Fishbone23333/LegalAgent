"""Streaming follow-up chat for debate agents."""
import json
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.llm_client import get_llm


VALID_AGENTS = {"challenger", "defender", "judge"}

ROLE_PROMPTS = {
    "challenger": (
        "你是红方 Challenger：一名长期帮助应届生和租房青年维权的公益律师。"
        "你的发言必须始终站在用户一方，像用户的代理律师一样说话。"
        "你的任务不是中立解释，而是从弱势方权益出发，继续追打合同中对用户不利、显失公平、"
        "可能违法或难以执行的条款。回答追问时要优先指出对用户的风险、损失后果、谈判抓手和可要求修改的方向；"
        "语气可以坚定、有立场，但不能夸大法律后果，也不能编造合同中没有的事实。"
    ),
    "defender": (
        "你是蓝方 Defender：对方律师、企业法务、房东代理人或中介代理人。"
        "你的发言必须模拟合同相对方的辩护立场，而不是替用户做风险提示。"
        "你的任务是理性、冷静、专业地为合同条款寻找商业合理性、管理必要性和可执行依据，"
        "说明对方可能如何解释、如何反驳红方质疑、如何维护自身利益。"
        "但你不是无底线狡辩：如果某条款明显违法、显失公平或实务上站不住脚，要承认其辩护边界，"
        "再从对方可接受的角度提出更稳妥的折中表述。回答时不要主动替用户设计维权策略，"
        "而是帮助用户看清对方可能怎么说、底线在哪里、哪些让步对方更可能接受。"
    ),
    "judge": (
        "你是 Judge：首席仲裁员。你的立场是客观、公正、权威地综合红方质疑和蓝方回应。"
        "你的发言必须保持裁判者视角，不替红方情绪化进攻，也不替蓝方商业辩护。"
        "回答追问时必须区分“可能无效或违法的条款”和“不利但可能合法的条款”，说明双方观点哪一边更有说服力，"
        "并给出用户下一步可执行的沟通、取证、修改或维权建议。"
    ),
}

ROLE_OUTPUT_RULES = {
    "challenger": (
        "本轮回答要像红方代理律师：先说用户最该坚持的点，再说明为什么这个点对用户不利，最后给出可谈判的修改方向。"
    ),
    "defender": (
        "本轮回答要像蓝方代理律师：先给出对方最可能采用的辩护理由，再说明该理由的法律或商业边界，最后给出对方更可能接受的折中方案。"
    ),
    "judge": (
        "本轮回答要像裁决官：先归纳争议焦点，再判断双方观点强弱，最后给出清晰的行动建议。"
    ),
}


def _event(event_type: str, **payload: str) -> dict[str, str]:
    """Build a single NDJSON event payload."""
    return {"type": event_type, **payload}


def _stringify(value: Any) -> str:
    """Convert context values to readable text for prompts."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def _get_context_value(context: dict[str, Any], *keys: str) -> Any:
    """Return the first present context value from candidate keys."""
    for key in keys:
        if key in context:
            return context.get(key)
    return ""


def _format_context(context: dict[str, Any]) -> str:
    """Format contract and prior debate result for the chat prompt."""
    raw_contract = _get_context_value(context, "raw_contract", "text", "contract")
    contract_type = _get_context_value(context, "contract_type")
    challenger_opening = _get_context_value(context, "challenger_opening")
    defender_response = _get_context_value(context, "defender_response")
    judge_verdict = _get_context_value(context, "judge_verdict")
    final_action_guide = _get_context_value(context, "final_action_guide")
    negotiation_scripts = _get_context_value(context, "negotiation_scripts")

    return "\n\n".join([
        "【原始合同】\n" + _stringify(raw_contract),
        "【合同类型】\n" + _stringify(contract_type),
        "【红方 Challenger 分析结果】\n" + _stringify(challenger_opening),
        "【蓝方 Defender 回应结果】\n" + _stringify(defender_response),
        "【裁决官 Judge 裁决结果】\n" + _stringify(judge_verdict),
        "【最终行动指南】\n" + _stringify(final_action_guide),
        "【谈判话术】\n" + _stringify(negotiation_scripts),
    ])


def _history_messages(history: Any) -> list[HumanMessage | AIMessage]:
    """Convert current agent chat history into LangChain messages."""
    if not isinstance(history, list):
        return []

    messages: list[HumanMessage | AIMessage] = []
    for item in history[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
            continue
        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def _build_messages(
    agent: str,
    question: str,
    context: dict[str, Any],
    history: Any,
) -> list[SystemMessage | HumanMessage | AIMessage]:
    """Build messages for a role-consistent follow-up answer."""
    system_content = (
        f"{ROLE_PROMPTS[agent]}\n\n"
        "通用要求：\n"
        "1. 必须优先依据下方【原始合同】和刚才红蓝分析结果回答，避免脱离上下文泛泛而谈。\n"
        "2. 如果上下文缺少关键信息，要明确说明无法确认的部分，并基于已有信息给出条件化建议。\n"
        "3. 保持当前 agent 的角色立场，不要切换成其他角色。\n"
        f"4. {ROLE_OUTPUT_RULES[agent]}\n"
        "5. 默认用中文回答，内容要可直接给用户参考。"
    )

    messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=system_content),
        HumanMessage(content="以下是本轮红蓝对抗完成后的上下文：\n\n" + _format_context(context)),
    ]
    messages.extend(_history_messages(history))
    messages.append(HumanMessage(content=f"用户追问：\n{question}"))
    return messages


def _chunk_content(chunk: Any) -> str:
    """Extract text content from a LangChain streaming chunk."""
    content = getattr(chunk, "content", chunk)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)


async def stream_debate_chat(
    agent: str,
    question: str,
    context: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> AsyncGenerator[dict[str, str], None]:
    """Stream a follow-up answer from one debate agent."""
    agent = (agent or "").strip().lower()
    question = (question or "").strip()
    context = context if isinstance(context, dict) else {}
    history = history if isinstance(history, list) else []

    if agent not in VALID_AGENTS:
        yield _event("error", message="agent must be one of: challenger, defender, judge")
        return
    if not question:
        yield _event("error", message="question is required")
        return

    try:
        llm = get_llm(temperature=0.2 if agent == "defender" else 0.1)
        messages = _build_messages(agent, question, context, history)
        streamed = False

        if hasattr(llm, "astream"):
            try:
                async for chunk in llm.astream(messages):
                    content = _chunk_content(chunk)
                    if content:
                        streamed = True
                        yield _event("token", content=content)
                yield _event("done")
                return
            except (AttributeError, NotImplementedError, TypeError):
                streamed = False
            except Exception as exc:
                if streamed:
                    yield _event("error", message=str(exc))
                    return
                streamed = False

        if hasattr(llm, "stream"):
            try:
                for chunk in llm.stream(messages):
                    content = _chunk_content(chunk)
                    if content:
                        streamed = True
                        yield _event("token", content=content)
                yield _event("done")
                return
            except (AttributeError, NotImplementedError, TypeError):
                streamed = False
            except Exception as exc:
                if streamed:
                    yield _event("error", message=str(exc))
                    return
                streamed = False

        response = llm.invoke(messages)
        content = _chunk_content(response)
        if content:
            yield _event("token", content=content)
        yield _event("done")

    except Exception as exc:
        yield _event("error", message=str(exc))
