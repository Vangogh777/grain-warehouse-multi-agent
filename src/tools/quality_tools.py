"""粮食品质质检工具 — LangChain BaseTool 实现"""
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
from src.tools.mock_data import (
    query_quality_records,
    get_quality_stats,
    get_quality_alerts,
    get_silo_info,
)


class SiloQueryInput(BaseModel):
    silo_id: str = Field(description="仓房编号，例如 S-01, S-07")


class DateRangeInput(BaseModel):
    grain_type: Optional[str] = Field(default=None, description="粮食品种：小麦/稻谷/玉米，不传查全部")
    start_date: Optional[str] = Field(default=None, description="开始日期，格式 YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="结束日期，格式 YYYY-MM-DD")


class TrendInput(BaseModel):
    indicator: str = Field(description="分析指标：moisture/impurity/damaged_ratio/test_weight/protein/brown_rice_rate")
    grain_type: Optional[str] = Field(default=None, description="粮食品种：小麦/稻谷/玉米")
    silo_id: Optional[str] = Field(default=None, description="仓房编号（可选），不传查全部")


class StandardCheckInput(BaseModel):
    grain_type: str = Field(description="粮食品种：小麦/稻谷/玉米")
    moisture: float = Field(description="水分百分比")
    impurity: float = Field(description="杂质百分比")
    damaged_ratio: float = Field(description="不完善粒百分比")
    test_weight: Optional[float] = Field(default=None, description="容重 g/L（小麦/玉米必填）")
    brown_rice_rate: Optional[float] = Field(default=None, description="出糙率 %（稻谷必填）")


# ========== 工具 1：质检记录查询 ==========

class QuerySampleRecordsTool(BaseTool):
    name: str = "query_sample_records"
    description: str = """查询粮食扦样质检记录。可按仓房、品种、批次、日期范围筛选。
    返回批次号、水分、杂质、不完善粒、容重、出糙率、蛋白质、等级等指标。"""
    args_schema: Type[BaseModel] = None

    # 用 Pydantic 动态构造带可选参数的 schema
    class QuerySampleInput(BaseModel):
        silo_id: Optional[str] = Field(default=None, description="仓房编号，例如 S-01，不传查全部")
        grain_type: Optional[str] = Field(default=None, description="粮食品种：小麦/稻谷/玉米")
        batch: Optional[str] = Field(default=None, description="批次号关键字")
        start_date: Optional[str] = Field(default=None, description="开始日期 YYYY-MM-DD")
        end_date: Optional[str] = Field(default=None, description="结束日期 YYYY-MM-DD")

    args_schema: Type[BaseModel] = QuerySampleInput

    def _run(self, silo_id: Optional[str] = None, grain_type: Optional[str] = None,
             batch: Optional[str] = None, start_date: Optional[str] = None,
             end_date: Optional[str] = None) -> str:
        records = query_quality_records(silo_id, grain_type, batch, start_date, end_date)
        if not records:
            return "未找到匹配的质检记录。"

        lines = [f"📋 共找到 {len(records)} 条质检记录：\n"]
        for r in records:
            parts = [
                f"🔹 {r['id']} | {r['silo_id']} | {r['grain_type']} | {r['batch']} | {r['date']}",
                f"   水分: {r['moisture']}% | 杂质: {r['impurity']}% | 不完善粒: {r['damaged_ratio']}%",
            ]
            if "test_weight" in r:
                parts.append(f"容重: {r['test_weight']} g/L")
            if "brown_rice_rate" in r:
                parts.append(f"出糙率: {r['brown_rice_rate']}%")
            if "protein" in r:
                parts.append(f"蛋白质: {r['protein']}%")
            parts.append(f"等级: {r['grade']} | 检验员: {r['inspector']}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)


# ========== 工具 2：质量统计 ==========

class QueryQualityStatsTool(BaseTool):
    name: str = "query_quality_stats"
    description: str = """查询粮食品质统计数据，包括等级分布、各指标均值。
    可按品种筛选（小麦/稻谷/玉米），不传则统计全部品种。"""
    args_schema: Type[BaseModel] = DateRangeInput

    def _run(self, grain_type: Optional[str] = None, **_) -> str:
        stats = get_quality_stats(grain_type)
        if "error" in stats:
            return stats["error"]

        label = f"「{grain_type}」" if grain_type else "全部品种"
        lines = [f"📊 {label} 质量统计：\n"]
        lines.append(f"总质检批次: {stats['total_records']}")
        lines.append(f"\n等级分布:")
        for grade, count in sorted(stats["grade_distribution"].items()):
            pct = round(count / stats["total_records"] * 100, 1)
            lines.append(f"  {grade}: {count} 批 ({pct}%)")

        lines.append(f"\n平均指标:")
        for key, val in stats["average_indicators"].items():
            label_map = {
                "moisture": "水分", "impurity": "杂质", "damaged_ratio": "不完善粒",
                "test_weight": "容重(g/L)", "protein": "蛋白质(%)",
                "brown_rice_rate": "出糙率(%)",
            }
            lines.append(f"  {label_map.get(key, key)}: {val}")
        return "\n".join(lines)

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)


# ========== 工具 3：质量趋势分析 ==========

class AnalyzeQualityTrendTool(BaseTool):
    name: str = "analyze_quality_trend"
    description: str = """分析某个质量指标随时间的变化趋势。
    支持指标：moisture(水分), impurity(杂质), damaged_ratio(不完善粒), test_weight(容重),
    protein(蛋白质), brown_rice_rate(出糙率)。
    可按品种和仓号筛选。"""
    args_schema: Type[BaseModel] = TrendInput

    def _run(self, indicator: str, grain_type: Optional[str] = None,
             silo_id: Optional[str] = None) -> str:
        records = query_quality_records(silo_id=silo_id, grain_type=grain_type)
        if not records:
            return f"未找到匹配的质检记录，无法分析趋势。"
        if indicator not in ["moisture", "impurity", "damaged_ratio", "test_weight",
                              "protein", "brown_rice_rate"]:
            return f"不支持的指标: {indicator}。支持: moisture/impurity/damaged_ratio/test_weight/protein/brown_rice_rate"

        # 过滤出包含该指标的记录，按日期排序
        valid = [(r["date"], r[indicator]) for r in records if indicator in r]
        valid.sort(key=lambda x: x[0])

        if len(valid) < 2:
            return f"质检记录不足（{len(valid)} 条），无法分析趋势。"

        label_map = {
            "moisture": "水分", "impurity": "杂质", "damaged_ratio": "不完善粒",
            "test_weight": "容重", "protein": "蛋白质", "brown_rice_rate": "出糙率",
        }
        label = label_map.get(indicator, indicator)
        unit = "%" if indicator != "test_weight" and indicator != "brown_rice_rate" else ""
        if indicator == "brown_rice_rate":
            unit = "%"

        lines = [f"📈 {label} 趋势分析：\n"]
        vals = [v for _, v in valid]
        lines.append(f"  最早 ({valid[0][0]}): {vals[0]}{unit}")
        lines.append(f"  最新 ({valid[-1][0]}): {vals[-1]}{unit}")
        lines.append(f"  均值: {round(sum(vals)/len(vals), 2)}{unit}")
        lines.append(f"  最高: {max(vals)}{unit} | 最低: {min(vals)}{unit}")

        # 变化方向
        change = vals[-1] - vals[0]
        direction = "上升" if change > 0 else ("下降" if change < 0 else "持平")
        lines.append(f"  整体趋势: {direction}（变化 {change:+.2f}{unit}）")

        # 逐项变化
        lines.append(f"\n逐次变化:")
        for i in range(1, len(valid)):
            delta = valid[i][1] - valid[i-1][1]
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
            lines.append(f"  {valid[i-1][0]} → {valid[i][0]}: {valid[i-1][1]} → {valid[i][1]} {arrow}")

        return "\n".join(lines)

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)


# ========== 工具 4：国标合规判定 ==========

class CheckQualityStandardTool(BaseTool):
    name: str = "check_quality_standard"
    description: str = """输入质检指标，对照国家标准判定粮食品级。
    小麦需传入容重(test_weight)，稻谷需传入出糙率(brown_rice_rate)。"""
    args_schema: Type[BaseModel] = StandardCheckInput

    def _run(self, grain_type: str, moisture: float, impurity: float,
             damaged_ratio: float, test_weight: Optional[float] = None,
             brown_rice_rate: Optional[float] = None) -> str:
        issues = []
        determined_grade = "一等"
        grade_reasons = []

        if grain_type == "小麦":
            if not test_weight:
                return "小麦判定需要传入容重(test_weight)参数。"
            # 容重定等
            if test_weight >= 790:
                grade_by_tw = "一等"
            elif test_weight >= 770:
                grade_by_tw = "二等"
            elif test_weight >= 750:
                grade_by_tw = "三等"
            else:
                grade_by_tw = "等外"
            grade_reasons.append(f"容重 {test_weight} g/L → {grade_by_tw}")
            determined_grade = grade_by_tw

            if moisture > 12.5:
                issues.append(f"水分 {moisture}% 超国标 ≤12.5%")
            if impurity > 2.0:
                issues.append(f"杂质 {impurity}% 超国标 ≤2.0%")
            if damaged_ratio > 8.0:
                issues.append(f"不完善粒 {damaged_ratio}% 超国标 ≤8.0%")

        elif grain_type == "稻谷":
            if not brown_rice_rate:
                return "稻谷判定需要传入出糙率(brown_rice_rate)参数。"
            # 出糙率定等
            if brown_rice_rate >= 79.0:
                grade_by_brr = "一等"
            elif brown_rice_rate >= 77.0:
                grade_by_brr = "二等"
            elif brown_rice_rate >= 75.0:
                grade_by_brr = "三等"
            else:
                grade_by_brr = "等外"
            grade_reasons.append(f"出糙率 {brown_rice_rate}% → {grade_by_brr}")
            determined_grade = grade_by_brr

            if moisture > 13.5:
                issues.append(f"水分 {moisture}% 超国标 ≤13.5%")
            if impurity > 2.0:
                issues.append(f"杂质 {impurity}% 超国标 ≤2.0%")
            if damaged_ratio > 8.0:
                issues.append(f"不完善粒 {damaged_ratio}% 超国标 ≤8.0%")

        elif grain_type == "玉米":
            if not test_weight:
                return "玉米判定需要传入容重(test_weight)参数。"
            # 容重定等
            if test_weight >= 720:
                grade_by_tw = "一等"
            elif test_weight >= 690:
                grade_by_tw = "二等"
            elif test_weight >= 660:
                grade_by_tw = "三等"
            else:
                grade_by_tw = "等外"
            grade_reasons.append(f"容重 {test_weight} g/L → {grade_by_tw}")
            determined_grade = grade_by_tw

            if moisture > 14.0:
                issues.append(f"水分 {moisture}% 超国标 ≤14.0%")
            if impurity > 2.0:
                issues.append(f"杂质 {impurity}% 超国标 ≤2.0%")
            if damaged_ratio > 8.0:
                issues.append(f"不完善粒 {damaged_ratio}% 超国标 ≤8.0%")
        else:
            return f"不支持的品种: {grain_type}。支持: 小麦/稻谷/玉米"

        lines = [f"📋 国标质量判定 — {grain_type}\n"]
        lines.append(f"输入指标:")
        lines.append(f"  水分: {moisture}% | 杂质: {impurity}% | 不完善粒: {damaged_ratio}%")
        if test_weight is not None:
            lines.append(f"  容重: {test_weight} g/L")
        if brown_rice_rate is not None:
            lines.append(f"  出糙率: {brown_rice_rate}%")
        lines.append(f"\n{chr(10).join(grade_reasons)}")
        lines.append(f"\n判定等级: {determined_grade}")
        if issues:
            lines.append(f"\n⚠️ 注意事项:")
            for iss in issues:
                lines.append(f"  ❌ {iss}")
        else:
            lines.append(f"\n✅ 所有指标均在国标范围内。")
        return "\n".join(lines)

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)


# ========== 工具 5：质量异常预警 ==========

class QueryQualityAlertsTool(BaseTool):
    name: str = "query_quality_alerts"
    description: str = """检查所有质检记录中存在的质量异常，包括水分超标、杂质偏高、不完善粒超标等问题。"""
    args_schema: Type[BaseModel] = None

    class EmptyInput(BaseModel):
        pass

    args_schema: Type[BaseModel] = EmptyInput

    def _run(self, **_) -> str:
        alerts = get_quality_alerts()
        if not alerts:
            return "✅ 当前无质量异常预警，所有批次的质检指标均在国标范围内。"

        lines = [f"⚠️ 发现 {len(alerts)} 条质量异常预警：\n"]
        for a in alerts:
            lines.append(f"🔴 {a['silo_id']} | {a['grain_type']} | 批次 {a['batch']} | {a['date']}")
            lines.append(f"   当前等级: {a['grade']}")
            for iss in a['issues']:
                lines.append(f"   ❌ {iss}")
            lines.append("")
        lines.append("💡 建议: 对上述批次安排复检，必要时调整等级或进行处理。")
        return "\n".join(lines)

    async def _arun(self, **_) -> str:
        return self._run()
