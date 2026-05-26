"""Debate Multi-Agent 系统 - LangGraph 工作流"""
from langgraph.graph import StateGraph, END
from agent.debate_state import DebateState
from agent.debate_nodes import challenger_node, defender_node, judge_node, negotiation_node
from agent.guardrail import guardrail_check


def create_debate_graph():
    """
    创建红蓝对抗辩论工作流图

    流程：START → Challenger → Defender → Judge → Negotiation → END
    """

    workflow = StateGraph(DebateState)

    # 添加节点
    workflow.add_node("challenger", challenger_node)
    workflow.add_node("defender", defender_node)
    workflow.add_node("judge", judge_node)
    workflow.add_node("negotiation", negotiation_node)

    # 设置入口点
    workflow.set_entry_point("challenger")

    # 线性流转：Challenger → Defender → Judge → Negotiation → END
    workflow.add_edge("challenger", "defender")
    workflow.add_edge("defender", "judge")
    workflow.add_edge("judge", "negotiation")
    workflow.add_edge("negotiation", END)

    return workflow.compile()


def run_debate(raw_contract: str, user_id: str = "anonymous") -> DebateState:
    """
    运行完整的红蓝对抗辩论流程

    Args:
        raw_contract: 原始合同文本
        user_id: 用户标识

    Returns:
        DebateState: 包含完整辩论结果的辩论状态
    """
    # Guardrail 检查
    is_contract, reason = guardrail_check(raw_contract)

    if not is_contract:
        return DebateState(
            raw_contract=raw_contract,
            contract_type="unknown",
            user_id=user_id,
            is_valid_contract=False,
            error_message=f"文本验证未通过：{reason}",
            challenger_opening="",
            defender_response="",
            judge_verdict="",
            final_action_guide={},
            negotiation_scripts=[],
            current_step="rejected",
        )

    # 初始状态
    initial_state = DebateState(
        raw_contract=raw_contract,
        contract_type="employment",
        user_id=user_id,
        is_valid_contract=True,
        error_message="",
        challenger_opening="",
        defender_response="",
        judge_verdict="",
        final_action_guide={},
        negotiation_scripts=[],
        current_step="initial",
    )

    # 执行工作流
    graph = create_debate_graph()
    final_state = graph.invoke(initial_state)

    return final_state


# 预编译图实例
debate_graph = create_debate_graph()
