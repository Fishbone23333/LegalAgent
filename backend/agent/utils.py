"""通用工具函数"""
import json
import re
from typing import Any

from .llm_client import get_llm


def _parse_json_response(content: str) -> Any:
    """
    从 LLM 返回内容中提取 JSON。
    支持 markdown 代码块包裹的 JSON，也支持纯 JSON 字符串。
    会自动过滤 LangChain 的 <排除 Think> 标签。
    """
    import re as _re

    # 过滤 LangChain 内部注释标签
    content = _re.sub(r"<think>[\s\S]*?</think>", "", content)

    content = content.strip()

    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 提取 markdown 代码块中的 JSON
    code_block_match = _re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```", content, _re.DOTALL
    )
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试找到第一个 { ... } 块
    brace_match = _re.search(r"\{[\s\S]*\}", content)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从响应中解析 JSON: {content[:200]}")
