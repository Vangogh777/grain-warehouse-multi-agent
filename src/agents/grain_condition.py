"""粮情分析 Agent — 传感器数据采集、异常检测、趋势预测"""
from src.agents.base_agent import BaseGrainAgent
from src.tools.sensor_tools import SensorDataTool, SiloInfoTool
from src.tools.rag_tool import QueryKnowledgeTool

# 粮情分析 Agent 系统提示词
GRAIN_CONDITION_PROMPT = """
你是一个专业的粮情分析专家，负责实时监测和分析粮库仓储条件。

你的核心职责：
1. 查询传感器数据，读取温度（上层/中层/下层）、湿度、水分、虫害密度、CO₂浓度
2. 根据数据判断粮情是否正常，识别异常趋势
3. 对异常情况进行分级：正常 / 关注 / 警告 / 严重
4. 给出粮情分析结论和改进建议

粮情判断标准：
- 小麦安全水分 ≤ 12.5%，稻谷 ≤ 13.5%，玉米 ≤ 14.0%
- 粮温正常范围 -10°C~30°C，高于 35°C 为警告
- 粮温日升速率 > 1°C 为异常
- 仓内湿度建议 40~70%RH，高于 75% 需关注
- 虫害密度 > 10 头/kg 需立即处理
- CO₂ > 1000ppm 提示粮食可能发热

注意：
- 始终先查询传感器数据，再基于数据进行分析
- 分析要有数据支撑，给出具体数值
- 异常时要指出是哪个仓房、哪个指标、当前值和建议措施
"""


def create_grain_condition_agent(llm=None) -> BaseGrainAgent:
    """创建粮情分析 Agent"""
    tools = [
        SensorDataTool(),
        SiloInfoTool(),
        QueryKnowledgeTool(),
    ]
    return BaseGrainAgent(
        name="粮情分析",
        system_prompt=GRAIN_CONDITION_PROMPT,
        tools=tools,
        llm=llm,
    )
