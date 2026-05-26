"""Debate Multi-Agent 状态定义"""
from typing import Literal


class DebateState(dict):
    """LangGraph 辩论系统全局状态"""

    # 原始输入
    raw_contract: str                      # 原始合同文本
    contract_type: Literal["employment", "housing", "unknown"]  # 合同类型
    user_id: str                           # 用户标识

    # 验证
    is_valid_contract: bool                 # 是否为有效合同
    error_message: str                     # 错误信息

    # 辩论记录
    challenger_opening: str                 # 红方（应届生律师）开篇陈词
    defender_response: str                  # 蓝方（企业法务/中介）反驳
    judge_verdict: str                     # 裁决官总结

    # 裁决结果
    final_action_guide: dict               # 维权行动指南

    # 谈判话术
    negotiation_scripts: list             # 逐条谈判话术

    # 元信息
    current_step: str                      # 当前节点（challenger / defender / judge / negotiation）
