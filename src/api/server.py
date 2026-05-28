"""FastAPI 接口 — 供前端 UI 调用（4 Agent 完整版）"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.mock_data import refresh_sensor_data
from src.agents.grain_condition import create_grain_condition_agent
from src.agents.operation import create_operation_agent
from src.agents.inoutbound import create_inoutbound_agent
from src.agents.report import create_report_agent
from src.orchestrator.orchestrator import GrainOrchestrator

app = FastAPI(title="粮库多智能体系统 API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_orchestrator: Optional[GrainOrchestrator] = None


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    agents_used: list[str]
    tool_calls_count: int
    processes: list[dict] = []


@app.on_event("startup")
async def startup():
    global _orchestrator
    refresh_sensor_data()
    grain = create_grain_condition_agent()
    op = create_operation_agent()
    io = create_inoutbound_agent()
    rpt = create_report_agent()
    _orchestrator = GrainOrchestrator()
    _orchestrator.register_agent(grain)
    _orchestrator.register_agent(op)
    _orchestrator.register_agent(io)
    _orchestrator.register_agent(rpt)


@app.get("/")
async def root():
    return {"service": "粮库多智能体系统", "status": "running",
            "agents": ["粮情分析", "智能作业", "出入库", "报表分析"]}


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="系统未初始化")
    try:
        result = await _orchestrator.process(req.query)
        return QueryResponse(
            answer=result["answer"],
            agents_used=result["agents_used"],
            tool_calls_count=len(result["tool_calls"]),
            processes=[{
                "step": p["step"], "agents": p["agents"], "mode": p["mode"],
                "results": [{"agent": r["agent"], "success": r["success"],
                             "output": r["output"][:300],
                             "tool_calls": r.get("tool_calls", []),
                             "elapsed": r.get("elapsed_seconds", 0)}
                            for r in p["results"]],
            } for p in result["processes"]],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refresh")
async def refresh():
    refresh_sensor_data()
    return {"status": "ok", "message": "传感器数据已刷新"}
