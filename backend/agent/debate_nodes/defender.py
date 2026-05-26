"""Defender Node（蓝方）- 企业法务 / 中介代理，RAG 增强版"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm_client import get_llm
from agent.debate_state import DebateState
from agent.prompts.debate import DEFENDER_PROMPT


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


def defender_node(state: DebateState) -> DebateState:
    """蓝方节点：企业法务 / 中介代理（RAG 增强）"""
    challenger_record = state.get("challenger_opening", "")
    raw_text = state.get("raw_contract", "")
    contract_type = state.get("contract_type", "unknown")

    if not challenger_record:
        return {
            **state,
            "defender_response": json.dumps({
                "responses": [],
                "overall_stance": "红方未提出有效质疑，无需反驳。"
            }, ensure_ascii=False),
            "current_step": "defender_done",
            "error_message": "",
        }

    try:
        llm = get_llm(temperature=0.2)
        provisions = _retrieve_legal_provisions(raw_text, contract_type, top_k=3)

        user_content = f"红方（Challenger）对合同的质疑内容如下：\n\n{challenger_record}"
        if provisions and provisions != "未找到相关法律条文。":
            user_content = (
                f"【相关法律条文】（辩护时请结合以下条文）\n{provisions}\n\n"
                f"红方（Challenger）对合同的质疑内容如下：\n\n{challenger_record}"
            )
        user_content += "\n\n请给出你的辩护和反驳。"

        messages = [
            SystemMessage(content=DEFENDER_PROMPT),
            HumanMessage(content=user_content),
        ]
        response = llm.invoke(messages)
        result = _parse_json_response(response.content)

        return {
            **state,
            "defender_response": json.dumps({
                "responses": result.get("responses", []),
                "overall_stance": result.get("overall_stance", ""),
            }, ensure_ascii=False),
            "current_step": "defender_done",
            "error_message": "",
        }

    except Exception as e:
        return {
            **state,
            "defender_response": json.dumps({
                "responses": [],
                "overall_stance": f"辩护分析出错：{str(e)}"
            }, ensure_ascii=False),
            "current_step": "defender_done",
            "error_message": f"蓝方分析出错：{str(e)}",
        }
