"""Extractor Node - 合同条款提取器（Thinker）"""
import json, re
from langchain_core.messages import HumanMessage, SystemMessage
from agent.llm_client import get_llm
from agent.state import AgentState
from agent.prompts import EXTRACTOR_PROMPT


def _parse_json_response(content: str) -> dict:
    """解析LLM返回的JSON响应，处理思考块和markdown，容错处理"""
    # 1. 去掉思考块
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    
    # 2. 去掉markdown代码块
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()
    
    # 3. 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 4. 容错：提取JSON部分
    first_brace = content.find('{')
    last_brace = content.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = content[first_brace:last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    return {}


def extractor_node(state: AgentState) -> AgentState:
    """节点A: 提取器"""
    raw_text = state.get("raw_contract", "")
    
    if not raw_text or len(raw_text.strip()) < 50:
        return {
            **state,
            "contract_type": "unknown",
            "is_valid_contract": False,
            "segments": [],
            "current_step": "extractor",
            "error_message": "合同文本过短或为空。"
        }
    
    try:
        llm = get_llm(temperature=0.1)
        messages = [
            SystemMessage(content=EXTRACTOR_PROMPT),
            HumanMessage(content=f"请分析以下合同文本：\n\n{raw_text}")
        ]
        
        response = llm.invoke(messages)
        result = _parse_json_response(response.content)
        
        return {
            **state,
            "contract_type": result.get("contract_type", "unknown"),
            "is_valid_contract": result.get("is_valid_contract", False),
            "segments": result.get("segments", []),
            "current_step": "extractor_done",
            "error_message": ""
        }
        
    except Exception as e:
        return {
            **state,
            "contract_type": "unknown",
            "is_valid_contract": False,
            "segments": [],
            "current_step": "extractor_done",
            "error_message": f"分析出错：{str(e)}"
        }
