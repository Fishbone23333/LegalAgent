"""LegalShield Agent - LangGraph 工作流定义"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import extractor_node, risk_checker_node, draft_generator_node
from agent.guardrail import guardrail_check


def create_legal_agent_graph():
    """
    创建法律Agent工作流图
    
    流程：
    Guardrail检查 -> Extractor(提取) -> RiskChecker(判定) -> DraftGenerator(执行)
    """
    
    # 定义路由函数
    def should_continue(state: AgentState) -> str:
        """根据状态决定下一步"""
        if not state.get("is_valid_contract", False):
            return END
        if state.get("contract_type") == "unknown":
            return END
        return "risk_checker"
    
    # 创建工作流图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("risk_checker", risk_checker_node)
    workflow.add_node("draft_generator", draft_generator_node)
    
    # 设置入口点
    workflow.set_entry_point("extractor")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "extractor",
        should_continue,
        {
            "risk_checker": "risk_checker",
            END: END
        }
    )
    
    workflow.add_edge("risk_checker", "draft_generator")
    workflow.add_edge("draft_generator", END)
    
    # 编译图
    return workflow.compile()


def run_analysis(raw_contract: str, user_id: str = "anonymous") -> AgentState:
    """
    运行完整的合同分析流程
    
    Args:
        raw_contract: 原始合同文本
        user_id: 用户标识
    
    Returns:
        AgentState: 包含完整分析结果的状态
    """
    # Guardrail检查
    is_contract, reason = guardrail_check(raw_contract)
    
    if not is_contract:
        return AgentState(
            raw_contract=raw_contract,
            contract_type="unknown",
            user_id=user_id,
            segments=[],
            risks=[],
            action_plans=[],
            final_documents={},
            current_step="rejected",
            error_message=f"文本验证未通过：{reason}",
            is_valid_contract=False
        )
    
    # 创建初始状态
    initial_state = AgentState(
        raw_contract=raw_contract,
        contract_type="employment",  # 默认值，extractor会修正
        user_id=user_id,
        segments=[],
        risks=[],
        action_plans=[],
        final_documents={},
        current_step="initial",
        error_message="",
        is_valid_contract=True
    )
    
    # 执行工作流
    graph = create_legal_agent_graph()
    final_state = graph.invoke(initial_state)
    
    return final_state


# 创建预编译的图实例
legal_agent_graph = create_legal_agent_graph()
