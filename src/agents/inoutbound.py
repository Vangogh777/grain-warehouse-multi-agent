"""出入库 Agent — 预约、质检、称重、结算全流程管理"""
from src.agents.base_agent import BaseGrainAgent
from src.tools.inout_tools import QueryInboundsTool, QueryOutboundsTool, GetScaleTool, AllocateSiloTool, SettlementTool
from src.tools.sensor_tools import SiloInfoTool

INOUT_PROMPT = """
你是一个粮库出入库管理专家，负责粮食入库和出库的全流程管理。

你的核心职责：
1. 查询今日入库/出库订单，了解业务量和进度
2. 查询地磅读数，掌握当前排队和作业状态
3. 根据粮食品种和数量，智能推荐合适的仓房
4. 计算结算金额（自动扣水分、杂质、等级差价）
5. 回答用户关于出入库业务的各类问题

流程说明：
- 入库流程：预约 → 排队 → 扦样质检 → 称毛重 → 分配仓房 → 卸粮 → 称皮重 → 结算
- 出库流程：出库指令 → 排队 → 出仓装粮 → 称毛重 → 结算 → 出门证

注意：
- 查询时先获取今日订单列表了解整体情况
- 分配仓房需考虑品种匹配和仓容利用率
- 回答要给出具体数据（车次、重量、金额等）
"""

def create_inoutbound_agent(llm=None) -> BaseGrainAgent:
    tools = [
        QueryInboundsTool(),
        QueryOutboundsTool(),
        GetScaleTool(),
        AllocateSiloTool(),
        SettlementTool(),
        SiloInfoTool(),
    ]
    return BaseGrainAgent(
        name="出入库",
        system_prompt=INOUT_PROMPT,
        tools=tools,
        llm=llm,
    )
