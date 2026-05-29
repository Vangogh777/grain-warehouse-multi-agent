"""FastAPI 接口 — 供前端 UI 调用（4 Agent 完整版）"""
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.mock_data import refresh_sensor_data, get_sensor_data, get_silo_info
from src.agents.grain_condition import create_grain_condition_agent
from src.agents.operation import create_operation_agent
from src.agents.inoutbound import create_inoutbound_agent
from src.agents.report import create_report_agent
from src.agents.quality import create_quality_agent
from src.orchestrator.graph_orchestrator import LangGraphOrchestrator
from src.orchestrator.debate import DebateOrchestrator

app = FastAPI(title="粮库多智能体系统 API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_orchestrator: Optional[LangGraphOrchestrator] = None
_debater: Optional[DebateOrchestrator] = None


class QueryRequest(BaseModel):
    query: str
    role: str = "keeper"
    session_id: str = "default"
    model: str = ""


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
    qual = create_quality_agent()
    _orchestrator = LangGraphOrchestrator()
    _orchestrator.register_agent(grain)
    _orchestrator.register_agent(op)
    _orchestrator.register_agent(io)
    _orchestrator.register_agent(rpt)
    _orchestrator.register_agent(qual)

    # 初始化辩论器
    global _debater
    _debater = DebateOrchestrator()
    _debater.register_agent(grain)
    _debater.register_agent(op)
    _debater.register_agent(io)
    _debater.register_agent(rpt)
    _debater.register_agent(qual)


@app.get("/")
async def root():
    return {"service": "粮库多智能体系统", "status": "running",
            "agents": ["粮情分析", "智能作业", "出入库", "报表分析", "质量检测"]}


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="系统未初始化")
    try:
        result = await _orchestrator.process(req.query, role=req.role, session_id=req.session_id, model=req.model)
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


@app.post("/api/query/stream")
async def query_stream(req: QueryRequest):
    """流式查询 — SSE 事件流"""
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="系统未初始化")
    async def event_stream():
        async for event in _orchestrator.process_stream(req.query, role=req.role, session_id=req.session_id, model=req.model):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/silos")
async def get_all_silos():
    """快速返回所有仓房传感器数据（不经过 LLM，毫秒级响应）"""
    silos = []
    for i in range(1, 13):
        sid = f"S-{i:02d}"
        data = get_sensor_data(sid)
        info = get_silo_info(sid)
        if data and info:
            silos.append({
                "id": sid,
                "grain_type": info["grain_type"],
                "grade": info["grade"],
                "capacity": info["capacity"],
                "current_qty": info["current_qty"],
                "temperature": {
                    "upper": round(data["temperature"]["upper"], 1),
                    "middle": round(data["temperature"]["middle"], 1),
                    "lower": round(data["temperature"]["lower"], 1),
                },
                "humidity": round(data["humidity"], 1),
                "moisture": round(data["moisture"], 1),
                "pest_density": round(data["pest_density"], 1),
                "co2_ppm": data["co2_ppm"],
                "timestamp": data["timestamp"],
            })
    return {"silos": silos, "count": len(silos), "refreshed_at": silos[0]["timestamp"] if silos else ""}


@app.post("/api/refresh")
async def refresh():
    refresh_sensor_data()
    return {"status": "ok", "message": "传感器数据已刷新"}


@app.get("/api/history")
async def get_history(session_id: str = "default", limit: int = 20):
    """获取对话历史"""
    from src.tools.memory import get_conversation_list
    items = get_conversation_list(session_id, limit)
    return {"session_id": session_id, "count": len(items), "items": items}


@app.post("/api/debate")
async def debate(req: QueryRequest):
    """多 Agent 辩论"""
    if not _debater:
        raise HTTPException(status_code=503, detail="辩论器未初始化")
    try:
        result = await _debater.debate(req.query, role=req.role, session_id=req.session_id, model=req.model)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trace/{request_id}")
async def get_trace(request_id: str):
    """获取工具调用 DAG 数据"""
    from src.tools.observability import get_trace_dag
    nodes = get_trace_dag(request_id)
    return {"request_id": request_id, "nodes": nodes, "count": len(nodes)}


@app.get("/api/sessions")
async def get_sessions():
    """获取所有会话列表"""
    from src.tools.memory import get_all_sessions
    sessions = get_all_sessions()
    return {"sessions": sessions}
