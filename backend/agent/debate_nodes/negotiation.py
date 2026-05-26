"""Negotiation Scripts Node - 逐条谈判话术生成"""
import json
from langchain_core.messages import HumanMessage, SystemMessage
from agent.debate_state import DebateState
from agent.prompts.debate import NEGOTIATION_PROMPT
from agent.utils import get_llm, _parse_json_response


def negotiation_node(state: DebateState) -> DebateState:
    """
    谈判话术生成节点
    职责：根据 challenger 发现的风险点，生成每条可直接发给房东/中介的微信话术
    """
    challenger_record = state.get("challenger_opening", "")

    if not challenger_record:
        return {
            **state,
            "negotiation_scripts": [],
            "current_step": "negotiation_done",
        }

    try:
        llm = get_llm(temperature=0.5)

        try:
            challenger_data = json.loads(challenger_record)
            risk_points = challenger_data.get("risk_points", [])
        except Exception:
            risk_points = []

        if not risk_points:
            return {
                **state,
                "negotiation_scripts": [],
                "current_step": "negotiation_done",
            }

        # 构造传递给 LLM 的风险点摘要
        risk_summary_lines = []
        for i, rp in enumerate(risk_points):
            risk_summary_lines.append(
                f"风险点{i+1}：{rp.get('clause','')}（等级：{rp.get('risk_level','')}）\n"
                f"  影响：{rp.get('impact','')}\n"
                f"  说明：{rp.get('severity_note','')}"
            )
        risk_summary = "\n\n".join(risk_summary_lines)

        contract_type = challenger_data.get("contract_type", "housing")
        contract_label = "租房合同" if contract_type == "housing" else "劳动合同"

        messages = [
            SystemMessage(content=NEGOTIATION_PROMPT),
            HumanMessage(
                content=f"合同类型：{contract_label}\n\n发现的风险点如下：\n\n{risk_summary}\n\n请为每个风险点生成一条谈判话术："
            ),
        ]

        response = llm.invoke(messages)
        result = _parse_json_response(response.content)

        scripts = result.get("scripts", [])
        # 确保每个 script 有 clause 字段（如果 LLM 没返回，就用原始 risk_point 的）
        for script in scripts:
            idx = script.get("risk_index", -1)
            if idx >= 0 and idx < len(risk_points) and not script.get("clause"):
                script["clause"] = risk_points[idx].get("clause", "")

        return {
            **state,
            "negotiation_scripts": scripts,
            "current_step": "negotiation_done",
        }

    except Exception as e:
        return {
            **state,
            "negotiation_scripts": [],
            "current_step": "negotiation_done",
        }
