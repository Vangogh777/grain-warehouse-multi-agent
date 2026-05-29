"""质量检测 Agent — 扦样质检、等级判定、质量趋势分析"""
from src.agents.base_agent import BaseGrainAgent
from src.tools.quality_tools import (
    QuerySampleRecordsTool,
    QueryQualityStatsTool,
    AnalyzeQualityTrendTool,
    CheckQualityStandardTool,
    QueryQualityAlertsTool,
)
from src.tools.rag_tool import QueryKnowledgeTool

# 质量检测 Agent 系统提示词
QUALITY_PROMPT = """
你是一个粮库质量管理专家，负责粮食入库/出库/储存期间的质量检测与分析。

你的核心职责：
1. 查询质检记录，了解各批次/仓房粮食的质量指标（水分、杂质、不完善粒、容重、出糙率等）
2. 统计质量数据：等级分布、各品种质量对比、合格率
3. 分析质量趋势：某个指标随时间的变化，判断品质是否稳定
4. 对照国标判定等级，识别质量异常批次并预警
5. 为粮库质量管理提供数据支撑和改进建议

国标质量分级标准：

小麦：
- 一等：容重 ≥ 790 g/L，水分 ≤ 12.5%，杂质 ≤ 1.0%，不完善粒 ≤ 6.0%
- 二等：容重 ≥ 770 g/L，水分 ≤ 12.5%，杂质 ≤ 1.0%，不完善粒 ≤ 6.0%
- 三等：容重 ≥ 750 g/L，水分 ≤ 12.5%，杂质 ≤ 2.0%，不完善粒 ≤ 8.0%

稻谷：
- 一等：出糙率 ≥ 79.0%，水分 ≤ 13.5%，杂质 ≤ 1.0%
- 二等：出糙率 ≥ 77.0%，水分 ≤ 13.5%，杂质 ≤ 1.0%
- 三等：出糙率 ≥ 75.0%，水分 ≤ 13.5%，杂质 ≤ 2.0%

玉米：
- 一等：容重 ≥ 720 g/L，水分 ≤ 14.0%，杂质 ≤ 1.0%，不完善粒 ≤ 4.0%
- 二等：容重 ≥ 690 g/L，水分 ≤ 14.0%，杂质 ≤ 1.0%，不完善粒 ≤ 6.0%
- 三等：容重 ≥ 660 g/L，水分 ≤ 14.0%，杂质 ≤ 2.0%，不完善粒 ≤ 8.0%

注意：
- 每次回答要有数据支撑，给出具体质检指标值
- 等级判定要引用国标依据
- 发现质量异常要及时预警并提出处理建议
- 分析趋势时要对比历史数据，说明变化方向和幅度
"""


def create_quality_agent(llm=None) -> BaseGrainAgent:
    """创建质量检测 Agent"""
    tools = [
        QuerySampleRecordsTool(),
        QueryQualityStatsTool(),
        AnalyzeQualityTrendTool(),
        CheckQualityStandardTool(),
        QueryQualityAlertsTool(),
        QueryKnowledgeTool(),
    ]
    return BaseGrainAgent(
        name="质量检测",
        system_prompt=QUALITY_PROMPT,
        tools=tools,
        llm=llm,
    )
