"""出入库数据函数 + LangChain 工具"""
import random
from datetime import datetime, timedelta
from typing import Type, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from src.tools.mock_data import SILOS

# ====== 数据层 ======
_inbound_orders = []
_outbound_orders = []

def _gen():
    global _inbound_orders, _outbound_orders
    now = datetime.now()
    vec_in = [("豫A·67890","小麦","二等",32500,8500,"新乡"),("豫B·12345","玉米","一等",28600,8200,"周口"),
              ("鲁C·56789","稻谷","二等",22400,7800,"信阳"),("皖D·90123","小麦","一等",34200,8800,"阜阳"),
              ("豫E·34567","玉米","二等",29800,8100,"驻马店"),("苏F·78901","稻谷","一等",21500,7600,"淮安"),
              ("鲁G·23456","小麦","二等",31800,8400,"菏泽"),("豫H·89012","小麦","一等",35600,9000,"安阳"),
              ("皖J·45678","玉米","一等",27500,8000,"宿州"),("冀K·01234","稻谷","三等",23800,7900,"邯郸")]
    vec_out = [("冀R·11111","小麦","一等",26000,8200,"北京面粉厂"),("苏M·22222","玉米","二等",24000,8000,"南京饲料厂"),
               ("浙N·33333","稻谷","一等",22000,7800,"杭州米业"),("京P·44444","小麦","二等",28000,8500,"北京食品厂"),
               ("粤Q·55555","玉米","一等",25500,8100,"广州饲料厂")]
    _inbound_orders.clear()
    _outbound_orders.clear()
    for i,(p,g,gr,gr_w,t,o) in enumerate(vec_in):
        n=gr_w-t; md=round(n*random.uniform(.003,.008),1); id_=round(n*random.uniform(.001,.005),1)
        gd={"一等":0,"二等":.5,"三等":1.5}[gr]*n/100; td=round(md+id_+gd,1)
        up={"小麦":2.36,"玉米":2.12,"稻谷":2.58}[g]
        _inbound_orders.append(dict(order_id=f"IN-{now.strftime('%Y%m%d')}-{i+1:03d}",vehicle_plate=p,grain_type=g,grade=gr,
            origin=o,gross_weight=gr_w,tare_weight=t,net_weight=n,moisture_deduct=md,impurity_deduct=id_,
            total_deduct=td,net_settled=round(n-td,1),unit_price=up,total_amount=round((n-td)*up/10000,2),
            status=random.choice(["已完成","已完成","已完成","进行中"]),silo=random.choice([s["id"] for s in SILOS[:8]]),
            inspector=random.choice(["张工","李工","王工","赵工"]),timestamp=(now-timedelta(hours=random.randint(1,12))).isoformat()))
    for i,(p,g,gr,gr_w,t,d) in enumerate(vec_out):
        n=gr_w-t; up={"小麦":2.42,"玉米":2.18,"稻谷":2.65}[g]
        _outbound_orders.append(dict(order_id=f"OUT-{now.strftime('%Y%m%d')}-{i+1:03d}",vehicle_plate=p,grain_type=g,grade=gr,
            destination=d,gross_weight=gr_w,tare_weight=t,net_weight=n,unit_price=up,total_amount=round(n*up/10000,2),
            status=random.choice(["已完成","已完成","进行中"]),silo=random.choice([s["id"] for s in SILOS[:8]]),
            timestamp=(now-timedelta(hours=random.randint(1,10))).isoformat()))

def get_today_inbounds():
    if not _inbound_orders: _gen()
    return _inbound_orders
def get_today_outbounds():
    if not _outbound_orders: _gen()
    return _outbound_orders
def get_scale_reading(sid="地磅01"):
    return dict(scale_id=sid,status="normal",current_weight=random.randint(0,35000),unit="kg",last_calibration=(datetime.now()-timedelta(days=15)).isoformat())
def allocate_silo(grain_type,quantity):
    cs=[s for s in SILOS if s["grain_type"]==grain_type and (s["capacity"]-s["current_qty"])*1000>=quantity]
    if cs:
        b=min(cs,key=lambda s:s["current_qty"]/s["capacity"])
        return dict(recommended_silo=b["id"],available_capacity=b["capacity"]-b["current_qty"],utilization=f"{b['current_qty']/b['capacity']*100:.1f}%",reason=f"同品种{grain_type}，利用率最低")
    cs=[s for s in SILOS if (s["capacity"]-s["current_qty"])*1000>=quantity]
    if cs:
        b=max(cs,key=lambda s:s["capacity"]-s["current_qty"])
        return dict(recommended_silo=b["id"],available_capacity=b["capacity"]-b["current_qty"],utilization=f"{b['current_qty']/b['capacity']*100:.1f}%",warning=f"该仓现存{b['grain_type']}，混装需确认")
    return dict(error="无可用仓房",suggestion="建议尽快出库释放仓容")
def calculate_settlement(gross,tare,grade,grain_type="小麦"):
    n=gross-tare; up={"小麦":2.36,"玉米":2.12,"稻谷":2.58}[grain_type]
    gd={"一等":0,"二等":.5,"三等":1.5}[grade]*n/100; md=round(n*random.uniform(.003,.006),1); id_=round(n*random.uniform(.001,.003),1)
    td=round(gd+md+id_,1); ns=round(n-td,1)
    return dict(gross_weight=gross,tare_weight=tare,net_weight=n,deductions=dict(grade_deduct=round(gd,1),moisture=md,impurity=id_,total=td),unit_price=up,net_settled=ns,total_amount=round(ns*up,2),unit="kg / 元")

# ====== LangChain 工具层 ======
class QueryInboundsTool(BaseTool):
    name:str="query_today_inbounds"
    description:str="查询今日入库订单列表，返回每车的车牌号、品种、等级、毛重、皮重、净重、结算金额等信息。"
    args_schema:Optional[Type[BaseModel]]=None
    def _run(self)->str:
        o=get_today_inbounds()
        return "\n".join([f"📥 今日入库 {len(o)} 车:"]+[f"  {x['vehicle_plate']} {x['grain_type']}{x['grade']} 净重{x['net_weight']}kg → ¥{x['total_amount']}万 {x['silo']} {x['status']}" for x in o])
    async def _arun(self)->str: return self._run()

class QueryOutboundsTool(BaseTool):
    name:str="query_today_outbounds"; description:str="查询今日出库订单列表，返回每车的去向、品种、净重等信息。"
    args_schema:Optional[Type[BaseModel]]=None
    def _run(self)->str:
        o=get_today_outbounds()
        return "\n".join([f"📤 今日出库 {len(o)} 车:"]+[f"  {x['vehicle_plate']} → {x['destination']} {x['grain_type']} 净重{x['net_weight']}kg {x['status']}" for x in o])
    async def _arun(self)->str: return self._run()

class ScaleInput(BaseModel):
    scale_id:str=Field(default="地磅01",description="地磅编号")

class GetScaleTool(BaseTool):
    name:str="get_scale_reading"; description:str="读取地磅当前读数，返回当前称重重量和状态。"
    args_schema:Type[BaseModel]=ScaleInput
    def _run(self,scale_id:str="地磅01")->str:
        r=get_scale_reading(scale_id)
        return f"⚖ {r['scale_id']}: {r['status']}，当前{r['current_weight']}kg，校准{r['last_calibration'][:10]}"
    async def _arun(self,scale_id:str="地磅01")->str: return self._run(scale_id)

class AllocateInput(BaseModel):
    grain_type:str=Field(description="品种：小麦/稻谷/玉米"); quantity:float=Field(description="数量(kg)")

class AllocateSiloTool(BaseTool):
    name:str="allocate_silo"; description:str="根据粮食品种和数量推荐合适的仓房。"
    args_schema:Type[BaseModel]=AllocateInput
    def _run(self,grain_type:str,quantity:float)->str:
        r=allocate_silo(grain_type,quantity)
        if "error"in r: return f"❌ {r['error']}。{r.get('suggestion','')}"
        m=f"🏭 推荐{r['recommended_silo']}（可用{r['available_capacity']}吨，利用率{r['utilization']}）原因:{r['reason']}"
        if "warning"in r: m+=f"\n⚠️ {r['warning']}"
        return m
    async def _arun(self,grain_type:str,quantity:float)->str: return self._run(grain_type,quantity)

class SettlementInput(BaseModel):
    gross:float=Field(description="毛重kg"); tare:float=Field(description="皮重kg"); grade:str=Field(description="等级")
    grain_type:str=Field(default="小麦",description="品种")

class SettlementTool(BaseTool):
    name:str="calculate_settlement"; description:str="计算结算金额，自动扣水分/杂质/等级差价。"
    args_schema:Type[BaseModel]=SettlementInput
    def _run(self,gross:float,tare:float,grade:str,grain_type:str="小麦")->str:
        r=calculate_settlement(gross,tare,grade,grain_type); d=r["deductions"]
        return f"🧾 结算: 毛{r['gross_weight']}kg-皮{r['tare_weight']}kg=净{r['net_weight']}kg | 扣等级{d['grade_deduct']}+水{d['moisture']}+杂{d['impurity']}={d['total']}kg | 结{r['net_settled']}kg×¥{r['unit_price']}=¥{r['total_amount']:,.2f}"
    async def _arun(self,gross:float,tare:float,grade:str,grain_type:str="小麦")->str: return self._run(gross,tare,grade,grain_type)
