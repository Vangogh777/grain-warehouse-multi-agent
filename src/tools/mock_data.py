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


# ========== 质检记录数据 ==========

QUALITY_RECORDS = [
    # 小麦
    {"id": "Q-2401", "silo_id": "S-01", "grain_type": "小麦", "batch": "B20240115",
     "moisture": 12.0, "impurity": 1.2, "damaged_ratio": 0.5, "protein": 13.5,
     "test_weight": 775, "grade": "一等", "inspector": "张工", "date": "2024-01-15"},
    {"id": "Q-2402", "silo_id": "S-01", "grain_type": "小麦", "batch": "B20240320",
     "moisture": 11.8, "impurity": 1.0, "damaged_ratio": 0.4, "protein": 13.8,
     "test_weight": 780, "grade": "一等", "inspector": "张工", "date": "2024-03-20"},
    {"id": "Q-2403", "silo_id": "S-02", "grain_type": "小麦", "batch": "B20240210",
     "moisture": 12.5, "impurity": 1.5, "damaged_ratio": 0.8, "protein": 12.8,
     "test_weight": 758, "grade": "二等", "inspector": "李工", "date": "2024-02-10"},
    {"id": "Q-2404", "silo_id": "S-05", "grain_type": "小麦", "batch": "B20240120",
     "moisture": 12.2, "impurity": 1.4, "damaged_ratio": 0.6, "protein": 13.2,
     "test_weight": 765, "grade": "二等", "inspector": "王工", "date": "2024-01-20"},
    {"id": "Q-2405", "silo_id": "S-07", "grain_type": "小麦", "batch": "B20240305",
     "moisture": 11.8, "impurity": 0.9, "damaged_ratio": 0.3, "protein": 14.0,
     "test_weight": 785, "grade": "一等", "inspector": "张工", "date": "2024-03-05"},
    {"id": "Q-2406", "silo_id": "S-10", "grain_type": "小麦", "batch": "B20240225",
     "moisture": 12.1, "impurity": 1.1, "damaged_ratio": 0.5, "protein": 13.6,
     "test_weight": 778, "grade": "一等", "inspector": "李工", "date": "2024-02-25"},
    # 稻谷
    {"id": "Q-2407", "silo_id": "S-03", "grain_type": "稻谷", "batch": "B20240110",
     "moisture": 13.8, "impurity": 1.3, "damaged_ratio": 0.7, "brown_rice_rate": 78.5,
     "test_weight": 560, "grade": "二等", "inspector": "赵工", "date": "2024-01-10"},
    {"id": "Q-2408", "silo_id": "S-03", "grain_type": "稻谷", "batch": "B20240315",
     "moisture": 14.0, "impurity": 1.5, "damaged_ratio": 0.9, "brown_rice_rate": 77.2,
     "test_weight": 555, "grade": "三等", "inspector": "赵工", "date": "2024-03-15"},
    {"id": "Q-2409", "silo_id": "S-03", "grain_type": "稻谷", "batch": "B20240420",
     "moisture": 14.2, "impurity": 1.8, "damaged_ratio": 1.1, "brown_rice_rate": 76.5,
     "test_weight": 548, "grade": "三等", "inspector": "赵工", "date": "2024-04-20"},
    {"id": "Q-2410", "silo_id": "S-04", "grain_type": "稻谷", "batch": "B20240220",
     "moisture": 11.5, "impurity": 0.8, "damaged_ratio": 0.3, "brown_rice_rate": 80.2,
     "test_weight": 572, "grade": "一等", "inspector": "钱工", "date": "2024-02-20"},
    {"id": "Q-2411", "silo_id": "S-04", "grain_type": "稻谷", "batch": "B20240401",
     "moisture": 11.6, "impurity": 0.9, "damaged_ratio": 0.4, "brown_rice_rate": 79.8,
     "test_weight": 570, "grade": "一等", "inspector": "钱工", "date": "2024-04-01"},
    {"id": "Q-2412", "silo_id": "S-09", "grain_type": "稻谷", "batch": "B20240301",
     "moisture": 14.2, "impurity": 2.1, "damaged_ratio": 1.5, "brown_rice_rate": 74.8,
     "test_weight": 535, "grade": "三等", "inspector": "孙工", "date": "2024-03-01"},
    # 玉米
    {"id": "Q-2413", "silo_id": "S-06", "grain_type": "玉米", "batch": "B20240125",
     "moisture": 13.0, "impurity": 1.0, "damaged_ratio": 0.8, "protein": 9.5,
     "test_weight": 725, "grade": "一等", "inspector": "周工", "date": "2024-01-25"},
    {"id": "Q-2414", "silo_id": "S-08", "grain_type": "玉米", "batch": "B20240228",
     "moisture": 12.8, "impurity": 1.6, "damaged_ratio": 1.2, "protein": 9.0,
     "test_weight": 695, "grade": "二等", "inspector": "吴工", "date": "2024-02-28"},
    {"id": "Q-2415", "silo_id": "S-11", "grain_type": "玉米", "batch": "B20240310",
     "moisture": 12.6, "impurity": 1.4, "damaged_ratio": 1.0, "protein": 9.2,
     "test_weight": 700, "grade": "二等", "inspector": "吴工", "date": "2024-03-10"},
]


def query_quality_records(
    silo_id: Optional[str] = None,
    grain_type: Optional[str] = None,
    batch: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict]:
    """按条件查询质检记录"""
    results = list(QUALITY_RECORDS)
    if silo_id:
        results = [r for r in results if r["silo_id"] == silo_id]
    if grain_type:
        results = [r for r in results if r["grain_type"] == grain_type]
    if batch:
        results = [r for r in results if batch.lower() in r["batch"].lower()]
    if start_date:
        results = [r for r in results if r["date"] >= start_date]
    if end_date:
        results = [r for r in results if r["date"] <= end_date]
    return results


def get_quality_stats(grain_type: Optional[str] = None) -> dict:
    """统计质量数据：等级分布、指标均值"""
    records = list(QUALITY_RECORDS)
    if grain_type:
        records = [r for r in records if r["grain_type"] == grain_type]

    if not records:
        return {"error": "没有匹配的质检记录"}

    # 等级分布
    grade_dist = {}
    for r in records:
        g = r["grade"]
        grade_dist[g] = grade_dist.get(g, 0) + 1

    # 各指标均值（仅对共有的数值字段统计）
    # 小麦/玉米有 test_weight/protein，稻谷有 brown_rice_rate
    numeric_keys = ["moisture", "impurity", "damaged_ratio", "test_weight"]
    avg = {}
    for key in numeric_keys:
        vals = [r[key] for r in records if key in r]
        if vals:
            avg[key] = round(sum(vals) / len(vals), 2)

    # 稻谷特有指标
    brr_vals = [r["brown_rice_rate"] for r in records if "brown_rice_rate" in r]
    if brr_vals:
        avg["brown_rice_rate"] = round(sum(brr_vals) / len(brr_vals), 2)

    # 蛋白质
    prot_vals = [r["protein"] for r in records if "protein" in r]
    if prot_vals:
        avg["protein"] = round(sum(prot_vals) / len(prot_vals), 2)

    return {
        "total_records": len(records),
        "grade_distribution": grade_dist,
        "average_indicators": avg,
    }


def get_quality_alerts() -> list[dict]:
    """检查质量异常预警"""
    alerts = []
    for r in QUALITY_RECORDS:
        reasons = []
        gt = r["grain_type"]
        m = r["moisture"]
        imp = r["impurity"]
        dr = r["damaged_ratio"]

        # 小麦水分安全线 ≤ 12.5%
        if gt == "小麦" and m > 12.5:
            reasons.append(f"水分 {m}% 超标（≤12.5%）")
        # 稻谷 ≤ 13.5%
        if gt == "稻谷" and m > 13.5:
            reasons.append(f"水分 {m}% 超标（≤13.5%）")
        # 玉米 ≤ 14.0%
        if gt == "玉米" and m > 14.0:
            reasons.append(f"水分 {m}% 超标（≤14.0%）")
        # 杂质 > 2.0% 预警
        if imp > 2.0:
            reasons.append(f"杂质 {imp}% 偏高")
        # 不完善粒 > 8.0% 预警
        if dr > 8.0:
            reasons.append(f"不完善粒 {dr}% 偏高")

        if reasons:
            alerts.append({
                "record_id": r["id"],
                "silo_id": r["silo_id"],
                "grain_type": r["grain_type"],
                "batch": r["batch"],
                "date": r["date"],
                "grade": r["grade"],
                "issues": reasons,
            })
    return alerts
