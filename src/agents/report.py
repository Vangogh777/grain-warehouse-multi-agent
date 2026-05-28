"""报表分析 Agent — NL2SQL、报表生成、趋势分析"""
from src.agents.base_agent import BaseGrainAgent
from src.tools.report_tools import QueryInventoryTool, QueryTrendTool, GenerateReportTool, AnalyzeAnomalyTool
from src.tools.sensor_tools import SensorDataTool, SiloInfoTool

REPORT_PROMPT = """
你是一个粮库报表分析专家，负责数据查询、报表生成和趋势分析。

你的核心职责：
1. 查询库存汇总数据（总库存、分品种、分仓房）
2. 分析粮情趋势（温度/湿度随时间变化）
3. 分析异常仓房（高温、高湿、虫害问题）
4. 生成日报、月报等格式化报表
5. 回答用户关于粮库运营数据的各类问题

注意：
- 根据用户问题自动选择合适的查询工具
- 分析要给出具体数据和对比
- 生成报表要格式清晰、便于阅读
"""

def create_report_agent(llm=None) -> BaseGrainAgent:
    tools = [
        QueryInventoryTool(),
        QueryTrendTool(),
        GenerateReportTool(),
        AnalyzeAnomalyTool(),
        SensorDataTool(),
        SiloInfoTool(),
    ]
    return BaseGrainAgent(
        name="报表分析",
        system_prompt=REPORT_PROMPT,
        tools=tools,
        llm=llm,
    )
