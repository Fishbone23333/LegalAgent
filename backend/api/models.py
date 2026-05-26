"""Pydantic 模型定义"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class AnalyzeRequest(BaseModel):
    """合同分析请求"""
    text: str = Field(..., min_length=20, description="合同全文")
    user_id: str = Field(default="anonymous", description="用户ID")


class StepUpdate(BaseModel):
    """流式步骤更新"""
    step: str
    status: Literal["running", "done", "error"]
    message: str
    progress: float = Field(ge=0, le=1)


class RiskPointResponse(BaseModel):
    """风险点响应"""
    clause: str
    risk_level: str
    risk_type: str
    legal_basis: str
    recommendation: str
    severity_note: str


class RevisionSuggestion(BaseModel):
    """修订建议"""
    original_clause: str
    suggested_revision: str
    reason: str


class EvidenceItem(BaseModel):
    """证据清单项"""
    evidence: str
    how_to_obtain: str
    note: str


class AnalyzeResponse(BaseModel):
    """分析完成响应"""
    success: bool
    contract_type: str
    is_valid_contract: bool
    segments: List[dict] = []
    risks: List[RiskPointResponse] = []
    action_plans: List[str] = []
    final_documents: dict = {}
    error_message: str = ""


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: str
    suggestion: str = "请检查输入内容是否为有效的劳动合同或租赁合同文本。"
