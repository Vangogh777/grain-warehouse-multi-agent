"""报表工具 — 数据函数 + LangChain 工具"""
import random
from datetime import datetime, timedelta
from typing import Type, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from src.tools.mock_data import SILOS

# ====== 数据层 ======
def query_inventory_summary():
    tc=sum(s["capacity"] for s in SILOS); tq=sum(s["current_qty"] for s in SILOS); bt={}
    for s in SILOS:
        t=s["grain_type"]
        if t not in bt: bt[t]={"capacity":0,"qty":0,"silos":0}
        bt[t]["capacity"]+=s["capacity"]; bt[t]["qty"]+=s["current_qty"]; bt[t]["silos"]+=1
    return dict(total_silos=len(SILOS),total_capacity=tc,total_inventory=tq,utilization=f"{tq/tc*100:.1f}%",by_type=bt)

def query_grain_trend(silo_id=None,days=7):
    bd={"S-01":{"temp":[22.1,22.3,22.0,22.5,22.4,22.6,22.2],"humidity":[62,63,61,64,62,65,63]},
        "S-07":{"temp":[28.5,29.2,30.1,31.0,31.8,32.5,32.9],"humidity":[58,60,62,63,64,65,65]},
        "S-03":{"temp":[25.0,25.2,25.1,25.3,25.0,25.4,25.2],"humidity":[68,70,71,72,72,73,73]}}
    if silo_id and silo_id in bd:
        d=bd[silo_id]
    else:
        at=[v["temp"] for v in bd.values()]; ah=[v["humidity"] for v in bd.values()]
        d={"temp":[sum(x)/len(x) for x in zip(*at)],"humidity":[sum(x)/len(x) for x in zip(*ah)]}
    t=d["temp"]; h=d["humidity"]
    return dict(silo_id=silo_id or "ALL",period=f"{days}天",dates=[(datetime.now()-timedelta(days=days-i-1)).strftime("%m-%d") for i in range(days)],
        temperature=dict(values=t,avg=round(sum(t)/len(t),1),max=max(t),min=min(t),trend="上升"if t[-1]>t[0]else"下降"),
        humidity=dict(values=h,avg=round(sum(h)/len(h),1),trend="上升"if h[-1]>h[0]else"下降"),anomaly=max(t)>30)

def generate_report(rt="daily",params=None):
    if rt=="daily":
        inv=query_inventory_summary()
        return f"📋 粮库日报 ({datetime.now().strftime('%Y-%m-%d')})\n━━━━━━━━━━\n🏭 {inv['total_silos']}仓 | 📦 {inv['total_inventory']}/{inv['total_capacity']}吨({inv['utilization']})\n🌾 小麦:{inv['by_type']['小麦']['qty']}t | 稻谷:{inv['by_type']['稻谷']['qty']}t | 玉米:{inv['by_type']['玉米']['qty']}t"
    return f"📊 {(params or {}).get('month','本月')}月报 - 请查询详细数据"

def analyze_anomaly_silos():
    return [dict(silo_id="S-07",level="warning",type="temperature",message="上中层温度32.9°C超出安全储粮温度",suggestion="建议立即机械通风降温"),
            dict(silo_id="S-03",level="attention",type="humidity",message="湿度73%RH持续偏高，7天趋势上升",suggestion="建议通风排湿或启用除湿")]

# ====== LangChain 工具层 ======
class QueryInventoryTool(BaseTool):
    name:str="query_inventory_summary"; description:str="查询粮库库存汇总：总仓数、总容量、总库存、按品种分类明细。"
    args_schema:Optional[Type[BaseModel]]=None
    def _run(self)->str:
        r=query_inventory_summary()
        return "\n".join([f"📦 库存: {r['total_inventory']}/{r['total_capacity']}t ({r['utilization']})"]+
            [f"  🌾 {t}: {v['qty']}t/{v['capacity']}t ({v['silos']}仓)" for t,v in r["by_type"].items()])
    async def _arun(self)->str: return self._run()

class TrendInput(BaseModel):
    silo_id:str=Field(default="",description="仓房编号"); days:int=Field(default=7,description="天数")

class QueryTrendTool(BaseTool):
    name:str="query_grain_trend"; description:str="查询仓房或全库粮情趋势（温度/湿度逐日变化）。"
    args_schema:Type[BaseModel]=TrendInput
    def _run(self,silo_id:str="",days:int=7)->str:
        r=query_grain_trend(silo_id or None,days); t=r["temperature"]; h=r["humidity"]
        return f"📈 {r['period']}趋势 - {r['silo_id']}\n🌡 {t['avg']}°C(↑{t['max']}/↓{t['min']}) {t['trend']}\n💧 {h['avg']}%RH {h['trend']}\n{'⚠️高温'if t['anomaly']else'✅正常'}"
    async def _arun(self,silo_id:str="",days:int=7)->str: return self._run(silo_id,days)

class ReportInput(BaseModel):
    report_type:str=Field(description="daily日报/monthly月报")

class GenerateReportTool(BaseTool):
    name:str="generate_report"; description:str="生成粮库报表：daily=日报，monthly=月报。"
    args_schema:Type[BaseModel]=ReportInput
    def _run(self,report_type:str="daily")->str: return generate_report(report_type)
    async def _arun(self,report_type:str="daily")->str: return self._run(report_type)

class AnalyzeAnomalyTool(BaseTool):
    name:str="analyze_anomaly_silos"; description:str="分析全部仓房异常情况，返回高温/高湿等问题仓房。"
    args_schema:Optional[Type[BaseModel]]=None
    def _run(self)->str:
        a=analyze_anomaly_silos()
        if not a: return "✅ 所有仓房正常"
        return "\n".join([f"⚠️ {len(a)}处异常:"]+[f"  {'🔴'if x['level']=='warning'else'🟡'} {x['silo_id']} {x['type']}: {x['message']}\n    → {x['suggestion']}" for x in a])
    async def _arun(self)->str: return self._run()
