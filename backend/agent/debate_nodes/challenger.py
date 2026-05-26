"""Challenger Node（红方）- 应届生公益律师，RAG 增强版"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm_client import get_llm
from agent.debate_state import DebateState
from agent.prompts.debate import CHALLENGER_PROMPT


def _parse_json_response(content: str) -> dict:
    """解析 LLM 返回的 JSON（容错版）"""
    # 去掉可能的 <think> 标签块
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


def _retrieve_legal_provisions(contract_text: str, contract_type: str | None = None, top_k: int = 5) -> str:
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


def challenger_node(state: DebateState) -> DebateState:
    """红方节点：应届生公益律师（RAG 增强）"""
    raw_text = state.get("raw_contract", "")

    if not raw_text or len(raw_text.strip()) < 20:
        return {
            **state,
            "contract_type": "unknown",
            "is_valid_contract": False,
            "challenger_opening": "",
            "error_message": "合同文本过短或为空。",
            "current_step": "challenger",
        }

    try:
        llm = get_llm(temperature=0.1)
        provisions = _retrieve_legal_provisions(raw_text, top_k=5)

        user_content = f"请分析以下合同文本：\n\n{raw_text}"
        if provisions and provisions != "未找到相关法律条文。":
            user_content = (
                f"【相关法律条文】（引用法条时优先使用以下条文）\n{provisions}\n\n"
                f"请分析以下合同文本：\n\n{raw_text}"
            )

        messages = [
            SystemMessage(content=CHALLENGER_PROMPT),
            HumanMessage(content=user_content),
        ]
        response = llm.invoke(messages)
        result = _parse_json_response(response.content)

        return {
            **state,
            "contract_type": result.get("contract_type", "unknown"),
            "is_valid_contract": True,
            "challenger_opening": json.dumps({
                "risk_points": result.get("risk_points", []),
                "opening_statement": result.get("opening_statement", ""),
            }, ensure_ascii=False),
            "current_step": "challenger_done",
            "error_message": "",
        }

    except Exception as e:
        return {
            **state,
            "contract_type": "unknown",
            "is_valid_contract": False,
            "challenger_opening": "",
            "current_step": "challenger_done",
            "error_message": f"红方分析出错：{str(e)}",
        }
