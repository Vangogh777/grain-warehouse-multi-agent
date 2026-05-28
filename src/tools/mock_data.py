"""Mock 数据 — 模拟粮库传感器、天气、设备等数据"""
import random
import math
from datetime import datetime, timedelta
from typing import Optional

# ========== 仓房基础数据 ==========
SILOS = [
    {"id": "S-01", "grain_type": "小麦", "grade": "一等", "capacity": 3000, "current_qty": 2400, "build_year": 2018},
    {"id": "S-02", "grain_type": "小麦", "grade": "二等", "capacity": 3000, "current_qty": 2200, "build_year": 2018},
    {"id": "S-03", "grain_type": "稻谷", "grade": "二等", "capacity": 2500, "current_qty": 2100, "build_year": 2019},
    {"id": "S-04", "grain_type": "稻谷", "grade": "一等", "capacity": 2500, "current_qty": 1800, "build_year": 2019},
    {"id": "S-05", "grain_type": "小麦", "grade": "二等", "capacity": 3000, "current_qty": 2600, "build_year": 2020},
    {"id": "S-06", "grain_type": "玉米", "grade": "一等", "capacity": 2800, "current_qty": 2000, "build_year": 2020},
    {"id": "S-07", "grain_type": "小麦", "grade": "一等", "capacity": 3000, "current_qty": 2800, "build_year": 2019},
    {"id": "S-08", "grain_type": "玉米", "grade": "二等", "capacity": 2800, "current_qty": 1500, "build_year": 2021},
    {"id": "S-09", "grain_type": "稻谷", "grade": "三等", "capacity": 2500, "current_qty": 1200, "build_year": 2021},
    {"id": "S-10", "grain_type": "小麦", "grade": "一等", "capacity": 3000, "current_qty": 1900, "build_year": 2020},
    {"id": "S-11", "grain_type": "玉米", "grade": "二等", "capacity": 2800, "current_qty": 2300, "build_year": 2019},
    {"id": "S-12", "grain_type": "稻谷", "grade": "一等", "capacity": 2500, "current_qty": 1600, "build_year": 2021},
]

SILO_MAP = {s["id"]: s for s in SILOS}

# ========== 传感器数据生成 ==========
_sensor_cache: dict = {}
_last_refresh: Optional[datetime] = None

def _get_base_temp(silo_id: str) -> float:
    """根据仓房返回基础温度"""
    base = {
        "S-01": 22.0, "S-02": 23.5, "S-03": 25.0, "S-04": 21.5,
        "S-05": 24.0, "S-06": 20.5, "S-07": 32.5,   # ← S-07 高温异常！
        "S-08": 19.0, "S-09": 26.5, "S-10": 23.0, "S-11": 21.0, "S-12": 24.5,
    }
    return base.get(silo_id, 22.0)

def _get_base_humidity(silo_id: str) -> float:
    """根据仓房返回基础湿度"""
    base = {
        "S-01": 62.0, "S-02": 58.0, "S-03": 73.0,   # ← S-03 高湿！
        "S-04": 55.0, "S-05": 60.0, "S-06": 52.0, "S-07": 65.0,
        "S-08": 48.0, "S-09": 70.0, "S-10": 59.0, "S-11": 54.0, "S-12": 61.0,
    }
    return base.get(silo_id, 60.0)

def _get_base_pest(silo_id: str) -> float:
    """虫害密度 (头/kg)"""
    base = {
        "S-01": 1.2, "S-02": 0.8, "S-03": 7.2,     # ← S-03 虫害上升！
        "S-04": 0.5, "S-05": 1.8, "S-06": 0.3, "S-07": 2.1,
        "S-08": 0.2, "S-09": 3.5, "S-10": 1.0, "S-11": 0.6, "S-12": 0.9,
    }
    return base.get(silo_id, 1.0)

def _get_base_moisture(silo_id: str) -> float:
    """粮食水分 (%)"""
    base = {
        "S-01": 12.0, "S-02": 12.5, "S-03": 13.8,   # ← S-03 水分偏高
        "S-04": 11.5, "S-05": 12.2, "S-06": 13.0, "S-07": 11.8,
        "S-08": 12.8, "S-09": 14.2, "S-10": 12.1, "S-11": 12.6, "S-12": 11.9,
    }
    return base.get(silo_id, 12.0)

def refresh_sensor_data():
    """刷新所有传感器数据（模拟实时采集）"""
    global _last_refresh
    now = datetime.now()
    noise_temp = random.uniform(-0.5, 0.5)
    noise_hum = random.uniform(-1.0, 1.0)

    for silo in SILOS:
        sid = silo["id"]
        base_temp = _get_base_temp(sid)
        base_hum = _get_base_humidity(sid)

        # 模拟温度分层（上层高、下层低）
        _sensor_cache[sid] = {
            "temperature": {
                "upper": round(base_temp + noise_temp + random.uniform(-0.3, 0.3), 1),
                "middle": round(base_temp + noise_temp * 0.7 + random.uniform(-0.2, 0.2), 1),
                "lower": round(base_temp * 0.85 + noise_temp * 0.3 + random.uniform(-0.2, 0.2), 1),
            },
            "humidity": round(base_hum + noise_hum + random.uniform(-0.5, 0.5), 1),
            "moisture": round(_get_base_moisture(sid) + random.uniform(-0.2, 0.2), 1),
            "pest_density": round(_get_base_pest(sid) + random.uniform(-0.1, 0.1), 1),
            "co2_ppm": random.randint(380, 600),
            "timestamp": now.isoformat(),
        }

    # 天气
    _sensor_cache["weather"] = {
        "current_temp": 28.0 + random.uniform(-3, 3),
        "current_humidity": 55.0 + random.uniform(-10, 10),
        "wind_direction": random.choice(["东北", "东南", "西南", "西北"]),
        "wind_level": random.randint(2, 4),
        "forecast": [
            {"period": "今晚 20:00~24:00", "temp": "22~26°C", "humidity": "50~65%", "wind": "东北风 2~3 级"},
            {"period": "明日 00:00~06:00", "temp": "19~23°C", "humidity": "55~70%", "wind": "东北风 2 级"},
            {"period": "明日 06:00~12:00", "temp": "24~30°C", "humidity": "45~60%", "wind": "东南风 2~3 级"},
            {"period": "明日 12:00~18:00", "temp": "28~33°C", "humidity": "40~55%", "wind": "南风 3 级"},
        ],
        "timestamp": now.isoformat(),
    }

    # 电价
    hour = now.hour
    if 22 <= hour or hour < 6:
        price = 0.35
        period = "谷电"
    elif hour in (6, 7, 8, 11, 12, 13, 14, 15, 16, 21):
        price = 0.70
        period = "平电"
    else:
        price = 1.15
        period = "峰电"

    _sensor_cache["electricity"] = {
        "current_price": price,
        "period": period,
        "hour": hour,
    }

    # 设备状态
    _sensor_cache["devices"] = {}
    for silo in SILOS:
        sid = silo["id"]
        _sensor_cache["devices"][sid] = {
            "fan": {"status": "online", "last_maintain": (now - timedelta(days=random.randint(10, 90))).isoformat()},
            "window": {"status": "online", "position": "closed"},
            "temp_sensor": {"status": "online", "accuracy": "0.1°C"},
            "gas_sensor": {"status": "online" if sid != "S-09" else "offline", "note": "" if sid != "S-09" else "S-09 气体传感器离线维修中"},
        }

    _last_refresh = now

def ensure_data():
    """确保数据已初始化"""
    if not _sensor_cache:
        refresh_sensor_data()

# ========== 对外查询接口 ==========

def get_silo_list() -> list[dict]:
    return SILOS

def get_silo_info(silo_id: str) -> Optional[dict]:
    return SILO_MAP.get(silo_id)

def get_sensor_data(silo_id: str) -> Optional[dict]:
    """获取某个仓房的传感器读数"""
    ensure_data()
    return _sensor_cache.get(silo_id)

def get_weather() -> dict:
    """获取当前天气和预报"""
    ensure_data()
    return _sensor_cache.get("weather", {})

def get_electricity_price() -> dict:
    """获取当前电价"""
    ensure_data()
    return _sensor_cache.get("electricity", {})

def get_device_status(silo_id: str) -> Optional[dict]:
    """获取仓房设备状态"""
    ensure_data()
    devices = _sensor_cache.get("devices", {})
    return devices.get(silo_id)
