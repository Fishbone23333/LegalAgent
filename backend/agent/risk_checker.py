"""风险判定器 - 带 RAG 检索增强"""

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.state import AgentState
from agent.llm_client import get_llm
from agent.prompts.core import RISK_CHECKER_PROMPT


def _parse_json_response(content: str) -> dict:
    """解析 LLM 返回的 JSON 内容"""
    content = content.strip()

    # 去掉 markdown 代码块
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

    fixed = _fix_json_content(content)
    if fixed:
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
    return {}


def _fix_json_content(content: str) -> str | None:
    """尝试修复不完整的 JSON 内容"""
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('#'):
            continue
        cleaned_lines.append(line)
    content = '\n'.join(cleaned_lines)

    start = content.find('{"')
    end = content.rfind('"}') + 2
    if start == -1 or end == -1:
        start = content.find('{')
        end = content.rfind('}') + 1
    if start != -1 and end > start:
        return content[start:end]
    return None


def _retrieve_legal_provisions(state: AgentState, top_k: int = 5) -> str:
    """
    根据合同条款内容，从法律知识库检索相关法条。
    若 RAG 模块未初始化（Ollama 未运行），返回空字符串。
    """
    try:
        from rag.legal_kb import get_legal_kb
        kb = get_legal_kb()
        kb.initialize()
    except Exception:
        return ""

    contract_type = state.get("contract_type", "unknown")
    segments = state.get("segments", [])

    if not segments:
        return ""

    # 从条款内容中构造检索 query
    # 取前 3 个条款的 title + content 组合作为检索 query
    query_parts = []
    for seg in segments[:3]:
        title = seg.get("title", "")
        content = seg.get("content", "")[:200]
        if title:
            query_parts.append(f"{title} {content}")
        else:
            query_parts.append(content[:200])
    query = " | ".join(query_parts)

    try:
        provisions_text = kb.search_as_text(
            query=query,
            top_k=top_k,
            mode="hybrid",
            contract_type=contract_type if contract_type != "unknown" else None,
        )
        return provisions_text
    except Exception:
        return ""


def risk_checker_node(state: AgentState) -> AgentState:
    """节点B: 风险判定器（RAG 增强版）"""
    contract_type = state.get("contract_type", "unknown")
    segments = state.get("segments", [])

    if contract_type == "unknown" or not segments:
        return {
            **state,
            "risks": [],
            "action_plans": [],
            "current_step": "risk_checker_done",
            "error_message": "",
        }

    try:
        llm = get_llm(temperature=0.1)
        segments_text = json.dumps(segments, ensure_ascii=False, indent=2)

        # RAG: 检索相关法律条文
        provisions = _retrieve_legal_provisions(state, top_k=5)

        # 构建提示词
        user_content = f"合同类型：{contract_type}\n\n"
        if provisions and provisions != "未找到相关法律条文。":
            user_content += f"【相关法律条文】（以下条文仅供参考，最终判定请结合具体条款）\n{provisions}\n\n"
        user_content += f"条款内容：\n{segments_text}\n\n请进行风险判定。"

        messages = [
            SystemMessage(content=RISK_CHECKER_PROMPT),
            HumanMessage(content=user_content),
        ]

        response = llm.invoke(messages)
        result = _parse_json_response(response.content)

        return {
            **state,
            "risks": result.get("risks", []),
            "action_plans": result.get("action_plans", []),
            "current_step": "risk_checker_done",
            "error_message": "",
        }

    except Exception as e:
        return {
            **state,
            "risks": [],
            "action_plans": [],
            "current_step": "risk_checker_done",
            "error_message": f"风险分析出错：{str(e)}",
        }
