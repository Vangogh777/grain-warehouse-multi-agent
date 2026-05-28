"""天气和电价查询工具"""
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
from src.tools.mock_data import get_weather, get_electricity_price

class WeatherTool(BaseTool):
    name: str = "get_weather_forecast"
    description: str = """查询当前天气和未来 72 小时天气预报，用于判断是否适合进行通风、熏蒸等户外作业。
    返回当前温度、湿度、风向风力以及未来几个时间段的详细预报。"""
    args_schema: Optional[Type[BaseModel]] = None

    def _run(self) -> str:
        w = get_weather()
        lines = [
            f"🌤 当前天气: {w['current_temp']:.1f}°C, 湿度 {w['current_humidity']:.0f}%RH, "
            f"{w['wind_direction']}风 {w['wind_level']} 级",
            f"📡 更新时间: {w['timestamp']}",
            "━━━ 未来预报 ━━━",
        ]
        for f in w["forecast"]:
            lines.append(f"  {f['period']}: {f['temp']}, {f['humidity']}, {f['wind']}")
        return "\n".join(lines)

    async def _arun(self) -> str:
        return self._run()

class ElectricityPriceTool(BaseTool):
    name: str = "get_electricity_price"
    description: str = """查询当前电价和时段（峰电/平电/谷电），用于判断何时启动通风设备最经济。"""
    args_schema: Optional[Type[BaseModel]] = None

    def _run(self) -> str:
        e = get_electricity_price()
        return (
            f"⚡ 当前电价: ¥{e['current_price']}/kWh\n"
            f"📊 时段: {e['period']} (当前 {e['hour']}:00)\n"
            f"💡 建议: {'👍 当前为谷电时段，适合启动设备' if '谷' in e['period'] else '⏳ 谷电时段 (22:00~06:00) 电费更低'}"
        )

    async def _arun(self) -> str:
        return self._run()
