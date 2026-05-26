"""Guardrail - 输入验证模块"""
import json
from langchain_core.messages import HumanMessage, SystemMessage
from agent.llm_client import get_llm
from agent.prompts import GUARDRAIL_PROMPT


def guardrail_check(text: str) -> tuple[bool, str]:
    """
    验证输入是否为有效合同文本
    
    Args:
        text: 输入文本
    
    Returns:
        tuple[bool, str]: (是否为合同, 原因)
    """
    if not text or len(text.strip()) < 20:
        return False, "文本内容过短，无法识别为合同"
    
    # 简单的关键词预检
    contract_keywords = ["合同", "协议", "甲方", "乙方", "签署", "约定", "条款"]
    
    # 如果没有任何合同相关关键词，尝试用LLM判断
    has_keyword = any(kw in text for kw in contract_keywords)
    
    if not has_keyword:
        try:
            llm = get_llm(temperature=0)
            messages = [
                SystemMessage(content=GUARDRAIL_PROMPT),
                HumanMessage(content=f"请判断：{text[:500]}")
            ]
            response = llm.invoke(messages)
            result = json.loads(response.content.strip())
            return result.get("is_contract", False), result.get("reason", "无法确定")
        except:
            return False, "未检测到合同相关特征"
    
    return True, "通过初步验证"


def validate_contract_text(text: str) -> dict:
    """
    完整验证合同文本
    
    Returns:
        dict: 验证结果详情
    """
    is_valid, reason = guardrail_check(text)
    
    return {
        "is_valid": is_valid,
        "reason": reason,
        "text_length": len(text),
        "has_keywords": any(kw in text for kw in ["合同", "协议", "甲方", "乙方"])
    }
