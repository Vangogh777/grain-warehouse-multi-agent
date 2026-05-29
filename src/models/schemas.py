"""Pydantic 数据模型"""
from pydantic import BaseModel
from typing import Optional, Literal

class AgentTask(BaseModel):
    """Agent 任务"""
    task_id: str
    agent_name: str
    input_text: str
    context: dict = {}

class AgentResult(BaseModel):
    """Agent 执行结果"""
    task_id: str
    agent_name: str
    success: bool
    output: str
    tool_calls: list[dict] = []

class OrchestratorRequest(BaseModel):
    """用户请求"""
    query: str
    conversation_id: Optional[str] = None
    role: str = "keeper"
    session_id: str = "default"

class OrchestratorResponse(BaseModel):
    """系统响应"""
    answer: str
    processes: list[dict] = []
    agents_involved: list[str] = []

# ========== 结构化输出模型 ==========

class GrainAnalysisOutput(BaseModel):
    """粮情分析结构化输出"""
    silo_id: str
    status: Literal["正常", "关注", "警告", "严重"]
    temperature_upper: Optional[float] = None
    temperature_middle: Optional[float] = None
    temperature_lower: Optional[float] = None
    humidity: Optional[float] = None
    moisture: Optional[float] = None
    pest_density: Optional[float] = None
    abnormal_indicators: list[str] = []
    suggestions: list[str] = []

class QualityOutput(BaseModel):
    """质量检测结构化输出"""
    silo_id: str
    grain_type: str
    sample_count: int
    grade_distribution: dict[str, int] = {}
    abnormal_records: list[dict] = []
    overall_assessment: str
    suggestions: list[str] = []

class ReportOutput(BaseModel):
    """报表结构化输出"""
    report_type: str
    period: str
    total_inventory: float = 0
    alert_count: int = 0
    summary: str = ""
    sections: list[dict] = []

class ToolCallRecord(BaseModel):
    """工具调用记录（可观测性）"""
    tool_name: str
    input_preview: str = ""
    output_preview: str = ""
    duration_ms: int = 0
    success: bool = True

class TraceRecord(BaseModel):
    """单次请求全链路追踪"""
    request_id: str
    scenario: str
    query: str
    agents_used: list[str] = []
    tool_calls: list[ToolCallRecord] = []
    total_tokens: int = 0
    total_duration_ms: int = 0
    answer_preview: str = ""
