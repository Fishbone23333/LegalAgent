"""DraftGenerator Node - 执行生成器（Executor）"""
import json, re
from langchain_core.messages import HumanMessage, SystemMessage
from agent.llm_client import get_llm
from agent.state import AgentState
from agent.prompts import DRAFT_GENERATOR_PROMPT


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


def _get_empty_documents():
    return {
        "revision_suggestions": [],
        "negotiation_script": "恭喜！本合同未发现明显违法条款。\n\n建议：\n1. 签署前仔细阅读每一条款\n2. 要求对方对模糊条款进行明确\n3. 保留合同原件和沟通记录",
        "evidence_checklist": [
            {"evidence": "合同原件", "how_to_obtain": "签署后立即获取", "note": "确保双方签字盖章"},
            {"evidence": "签署过程沟通记录", "how_to_obtain": "保留邮件、微信截图等", "note": "如有口头承诺，尽量书面确认"}
        ]
    }


def draft_generator_node(state: AgentState) -> AgentState:
    """节点C: 执行生成器"""
    risks = state.get("risks", [])
    
    if not risks:
        return {**state, "final_documents": _get_empty_documents(), "current_step": "draft_generator_done", "error_message": ""}
    
    try:
        llm = get_llm(temperature=0.3)
        contract_type = state.get("contract_type", "unknown")
        segments = state.get("segments", [])
        
        risks_text = json.dumps(risks, ensure_ascii=False, indent=2)
        segments_text = json.dumps(segments, ensure_ascii=False, indent=2)
        
        messages = [
            SystemMessage(content=DRAFT_GENERATOR_PROMPT),
            HumanMessage(content=f"合同类型：{contract_type}\n\n已识别的风险点：\n{risks_text}\n\n合同条款摘要：\n{segments_text}\n\n请生成三份法律文书。")
        ]
        
        response = llm.invoke(messages)
        result = _parse_json_response(response.content)
        
        return {
            **state,
            "final_documents": {
                "revision_suggestions": result.get("revision_suggestions", []),
                "negotiation_script": result.get("negotiation_script", ""),
                "evidence_checklist": result.get("evidence_checklist", [])
            },
            "current_step": "draft_generator_done",
            "error_message": ""
        }
        
    except Exception as e:
        return {**state, "final_documents": _get_empty_documents(), "current_step": "draft_generator_done", "error_message": f"法律文书生成出错：{str(e)}"}
