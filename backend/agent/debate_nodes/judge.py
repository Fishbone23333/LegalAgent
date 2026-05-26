"""Judge Node（裁决官）- 首席仲裁员，RAG 增强版"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm_client import get_llm
from agent.debate_state import DebateState
from agent.prompts.debate import JUDGE_PROMPT


def _parse_json_response(content: str) -> dict:
    """解析 LLM 返回的 JSON（容错版）"""
    content = re.sub(r'<think>[\s\S]*?</think>', '', content)
    content = content.strip()

    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    first_brace = content.find('{')
    last_brace = content.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(content[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    return {}


def _retrieve_legal_provisions(contract_text: str, contract_type: str | None = None, top_k: int = 3) -> str:
    """根据合同文本检索相关法律条文。Ollama 不可用时返回空字符串。"""
    try:
        from rag.legal_kb import get_legal_kb
        kb = get_legal_kb()
        kb.initialize()
    except Exception:
        return ""

    query = contract_text[:500]
    try:
        return kb.search_as_text(
            query=query,
            top_k=top_k,
            mode="hybrid",
            contract_type=contract_type if contract_type != "unknown" else None,
        )
    except Exception:
        return ""


def judge_node(state: DebateState) -> DebateState:
    """裁决官节点：首席仲裁员（RAG 增强）"""
    challenger_record = state.get("challenger_opening", "")
    defender_record = state.get("defender_response", "")
    raw_text = state.get("raw_contract", "")
    contract_type = state.get("contract_type", "unknown")

    if not challenger_record and not defender_record:
        return {
            **state,
            "judge_verdict": json.dumps({
                "verdict_summary": "双方未能提供有效辩论记录。"
            }, ensure_ascii=False),
            "final_action_guide": {},
            "current_step": "judge_done",
            "error_message": "无辩论记录可裁决。",
        }

    try:
        llm = get_llm(temperature=0.1)

        debate_record = f"""【红方（Challenger）开篇陈词】
{challenger_record}

【蓝方（Defender）辩护与反驳】
{defender_record}"""

        provisions = _retrieve_legal_provisions(raw_text, contract_type, top_k=3)
        if provisions and provisions != "未找到相关法律条文。":
            debate_record = (
                f"【相关法律条文】（裁决时请严格依据以下条文）\n{provisions}\n\n"
                + debate_record
            )

        messages = [
            SystemMessage(content=JUDGE_PROMPT),
            HumanMessage(content=f"请根据以下红蓝双方辩论记录，做出客观裁决：\n\n{debate_record}"),
        ]
        response = llm.invoke(messages)
        result = _parse_json_response(response.content)

        return {
            **state,
            "judge_verdict": json.dumps({
                "verdict_summary": result.get("verdict_summary", ""),
                "void_clauses": result.get("void_clauses", []),
                "unfair_but_legal": result.get("unfair_but_legal", []),
            }, ensure_ascii=False),
            "final_action_guide": {
                "action_plan": result.get("action_plan", {}),
                "evidence_checklist": result.get("evidence_checklist", []),
            },
            "current_step": "judge_done",
            "error_message": "",
        }

    except Exception as e:
        return {
            **state,
            "judge_verdict": json.dumps({
                "verdict_summary": f"裁决出错：{str(e)}"
            }, ensure_ascii=False),
            "final_action_guide": {},
            "current_step": "judge_done",
            "error_message": f"裁决官出错：{str(e)}",
        }
