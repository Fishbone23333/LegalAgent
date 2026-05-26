from typing import Annotated, List, TypedDict, Literal


class RiskPoint(TypedDict):
    """单个风险点"""
    clause: str                       # 涉及条款原文
    risk_level: Literal["low", "medium", "high", "critical"]  # 风险等级
    risk_type: str                    # 风险类型
    legal_basis: str                  # 法律依据
    recommendation: str               # 修改建议
    severity_note: str                # 严重程度说明


class ContractSegment(TypedDict):
    """拆解后的合同条款模块"""
    title: str                        # 条款标题
    content: str                      # 条款内容
    key_items: dict                   # 关键要素提取


class AgentState(TypedDict):
    """LangGraph 全局状态"""
    raw_contract: str                # 原始合同文本
    contract_type: Literal["employment", "housing", "unknown"]  # 合同类型
    user_id: str                     # 用户ID
    segments: List[ContractSegment]  # 拆解后的条款模块
    risks: List[RiskPoint]            # 判定出的风险点
    action_plans: List[str]           # 执行建议
    final_documents: dict             # 最终生成文案
    current_step: str                 # 当前处理步骤（用于流式输出）
    error_message: str                # 错误信息（如有）
    is_valid_contract: bool          # 是否为有效合同
