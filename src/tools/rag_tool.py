"""知识库检索工具 — Agent 通过它查国标和操作规程"""
from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from src.tools.knowledge_base import format_knowledge


class KnowledgeQueryInput(BaseModel):
    query: str = Field(description="检索关键词，例如'小麦一等水分标准'或'通风作业条件'")


class QueryKnowledgeTool(BaseTool):
    name: str = "query_knowledge_base"
    description: str = """检索粮库知识库（国家标准、仓储操作规程）。
    当需要查国标等级判定、操作规范、储存要求时使用。
    输入自然语言问题，返回相关标准条文。"""
    args_schema: Type[BaseModel] = KnowledgeQueryInput

    def _run(self, query: str) -> str:
        return format_knowledge(query)

    async def _arun(self, query: str) -> str:
        return self._run(query)
