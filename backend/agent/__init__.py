"""LegalShield Agent - 核心模块"""
from .state import AgentState, RiskPoint, ContractSegment
from .graph import create_legal_agent_graph, run_analysis, legal_agent_graph
from .nodes import extractor_node, risk_checker_node, draft_generator_node
from .guardrail import guardrail_check, validate_contract_text
from .llm_client import get_llm
from .utils import _parse_json_response

# 辩论 Multi-Agent 系统
from .debate_state import DebateState
from .debate_graph import create_debate_graph, run_debate, debate_graph

__all__ = [
    "AgentState",
    "RiskPoint",
    "ContractSegment",
    "create_legal_agent_graph",
    "run_analysis",
    "legal_agent_graph",
    "extractor_node",
    "risk_checker_node",
    "draft_generator_node",
    "guardrail_check",
    "validate_contract_text",
    "get_llm",
    # 辩论系统
    "DebateState",
    "create_debate_graph",
    "run_debate",
    "debate_graph",
]
