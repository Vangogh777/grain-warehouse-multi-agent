"""设备状态查询与控制工具"""
from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from src.tools.mock_data import get_device_status, get_silo_info

class DeviceQueryInput(BaseModel):
    silo_id: str = Field(description="仓房编号，例如 S-01, S-07")

class CheckDeviceTool(BaseTool):
    name: str = "check_device_status"
    description: str = """检查指定仓房的所有设备运行状态，包括风机、电动窗、温度传感器、气体传感器等。
    输入仓房编号，返回各设备是否在线及上次维护时间。"""
    args_schema: Type[BaseModel] = DeviceQueryInput

    def _run(self, silo_id: str) -> str:
        devices = get_device_status(silo_id)
        if not devices:
            return f"错误：未找到仓房 {silo_id} 的设备信息"
        silo = get_silo_info(silo_id)
        lines = [f"🔧 仓房 {silo_id} 设备状态"]
        for name, info in devices.items():
            icon = "✅" if info["status"] == "online" else "❌"
            status_text = "在线 ✓" if info["status"] == "online" else f"离线 ✗ {info.get('note', '')}"
            lines.append(f"  {icon} {name}: {status_text}")
        lines.append(f"📅 风机上次维护: {devices['fan']['last_maintain'][:10]}")
        return "\n".join(lines)

    async def _arun(self, silo_id: str) -> str:
        return self._run(silo_id)

class ControlDeviceInput(BaseModel):
    silo_id: str = Field(description="仓房编号")
    device: str = Field(description="设备名称: fan(风机), window(电动窗)")
    command: str = Field(description="控制指令: start/stop(风机), open/close(窗户)")

class ControlDeviceTool(BaseTool):
    name: str = "control_device"
    description: str = """远程控制仓房设备。支持：风机 (start/stop)，电动窗 (open/close)。
    注意：该操作需要管理员权限，调用后返回执行结果。"""
    args_schema: Type[BaseModel] = ControlDeviceInput

    def _run(self, silo_id: str, device: str, command: str) -> str:
        valid_devices = {"fan": ["start", "stop"], "window": ["open", "close"]}
        if device not in valid_devices:
            return f"错误：不支持的设备 '{device}'，支持: {', '.join(valid_devices.keys())}"
        if command not in valid_devices[device]:
            return f"错误：不支持的命令 '{command}'，{device} 支持: {', '.join(valid_devices[device])}"

        # 检查设备是否在线
        devices = get_device_status(silo_id)
        if not devices or devices.get(device, {}).get("status") != "online":
            return f"错误：{silo_id} 的 {device} 当前离线，无法执行操作"

        cmd_map = {"start": "启动", "stop": "停止", "open": "打开", "close": "关闭"}
        return (
            f"✅ 设备控制指令已发送\n"
            f"📍 {silo_id} → {device} → {cmd_map.get(command, command)}\n"
            f"⏱ 指令已提交，预计 5 秒内执行完毕"
        )

    async def _arun(self, silo_id: str, device: str, command: str) -> str:
        return self._run(silo_id, device, command)
