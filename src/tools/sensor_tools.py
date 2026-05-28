"""传感器数据查询工具 — LangChain BaseTool 实现"""
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
from src.tools.mock_data import get_sensor_data, get_silo_info

class SensorQueryInput(BaseModel):
    silo_id: str = Field(description="仓房编号，例如 S-01, S-07")

class SensorDataTool(BaseTool):
    name: str = "get_sensor_data"
    description: str = """查询指定仓房的实时传感器数据，包括温度(上层/中层/下层)、湿度、粮食水分、虫害密度、CO2浓度。
    输入仓房编号如 S-01，返回完整的传感器读数。"""
    args_schema: Type[BaseModel] = SensorQueryInput

    def _run(self, silo_id: str) -> str:
        data = get_sensor_data(silo_id)
        if not data:
            return f"错误：未找到仓房 {silo_id}"
        silo = get_silo_info(silo_id)
        grain_info = f" ({silo['grain_type']} {silo['grade']})" if silo else ""

        return (
            f"🆔 仓房 {silo_id}{grain_info}\n"
            f"🌡 温度: 上层 {data['temperature']['upper']}°C | "
            f"中层 {data['temperature']['middle']}°C | "
            f"下层 {data['temperature']['lower']}°C\n"
            f"💧 湿度: {data['humidity']}%RH\n"
            f"💦 水分: {data['moisture']}%\n"
            f"🐛 虫害密度: {data['pest_density']} 头/kg\n"
            f"💨 CO₂: {data['co2_ppm']} ppm\n"
            f"🕐 采集时间: {data['timestamp']}"
        )

    async def _arun(self, silo_id: str) -> str:
        return self._run(silo_id)

class SiloInfoTool(BaseTool):
    name: str = "get_silo_info"
    description: str = """查询仓房基础信息，包括仓号、粮食品种、等级、容量、当前存量、建成年份等。"""
    args_schema: Type[BaseModel] = SensorQueryInput

    def _run(self, silo_id: str) -> str:
        silo = get_silo_info(silo_id)
        if not silo:
            return f"错误：未找到仓房 {silo_id}"
        usage = round(silo["current_qty"] / silo["capacity"] * 100, 1)
        return (
            f"🏭 仓房 {silo['id']}\n"
            f"🌾 品种: {silo['grain_type']} | 等级: {silo['grade']}\n"
            f"📦 容量: {silo['capacity']} 吨 | 当前存量: {silo['current_qty']} 吨 ({usage}%)\n"
            f"📅 建成: {silo['build_year']} 年"
        )

    async def _arun(self, silo_id: str) -> str:
        return self._run(silo_id)
