"""Pydantic 数据模型"""
from pydantic import BaseModel
from typing import Optional

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

class OrchestratorResponse(BaseModel):
    """系统响应"""
    answer: str
    processes: list[dict] = []
    agents_involved: list[str] = []
