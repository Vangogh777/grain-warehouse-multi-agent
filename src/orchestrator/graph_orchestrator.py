"""LangGraph 状态机编排器 — 替代手写 if/else 的 GrainOrchestrator"""
import asyncio
import json
from datetime import datetime
from typing import TypedDict, Annotated, Optional, Any

from langgraph.graph import StateGraph, END

from src.tools.observability import (
    new_request_id,
    record_conversation,
    record_llm_call,
    record_tool_call,
)
from src.agents.base_agent import BaseGrainAgent
from src.tools.rag_tool import QueryKnowledgeTool


# ========== Graph 状态定义 ==========

class AgentState(TypedDict):
    request_id: str
    query: str
    scenario: str
    agents_used: list[str]
    tool_calls: list[dict]
    total_tokens: int
    duration_ms: int
    results: dict[str, dict]  # agent_name -> run result
    final_answer: str
    error: Optional[str]


# ========== 场景检测（与原 orchestrator 一致） ==========

def detect_scenario(query: str) -> str:
    q = query.lower()
    # 作业管理（通风/熏蒸/设备操作）
    if any(k in q for k in ["通风", "作业", "作业条件", "满足条件", "能开风机", "开风机",
                             "熏蒸", "虫害", "杀虫", "设备", "风机", "电动窗"]):
        return "ventilation"
    # 出入库
    if any(k in q for k in ["出入库", "入库", "出库", "车辆", "业务量", "今天业务"]):
        return "inoutbound"
    # 报表/统计
    if any(k in q for k in ["报表", "报告", "统计", "库存", "日报", "月报", "汇总"]):
        return "report"
    # 质量检测
    if any(k in q for k in ["质量", "质检", "等级", "品质", "扦样", "国标", "指标", "水分超标", "杂质"]):
        return "quality"
    # 粮情分析
    if any(k in q for k in ["粮情", "异常", "温度", "湿度", "粮温", "变化", "粮情变化", "分析"]):
        return "grain_analysis"
    return "general"


def extract_silo_id(query: str) -> Optional[str]:
    import re
    match = re.search(r'S-\d{1,2}', query.upper())
    return match.group(0) if match else None


# ========== 图节点函数 ==========

def router_node(state: AgentState) -> dict:
    """意图识别节点 — 确定走哪个场景"""
    scenario = detect_scenario(state["query"])
    return {"scenario": scenario}


def build_agent_nodes(
    agents: dict[str, BaseGrainAgent],
) -> dict[str, Any]:
    """为每个 Agent 创建图节点函数"""

    async def run_agent(agent_name: str, state: AgentState) -> dict:
        agent = agents[agent_name]
        agent.request_id = state["request_id"]
        start = datetime.now()
        try:
            result = await agent.run(state["query"])
            elapsed = int((datetime.now() - start).total_seconds() * 1000)
            tokens = result.get("input_tokens", 0) + result.get("output_tokens", 0)
            return {
                "results": {agent_name: result},
                "agents_used": [agent_name],
                "total_tokens": tokens,
                "duration_ms": elapsed,
                "tool_calls": result.get("tool_calls", []),
            }
        except Exception as e:
            return {
                "results": {agent_name: {
                    "agent": agent_name, "success": False,
                    "output": f"Agent 执行出错: {str(e)}", "tool_calls": [],
                }},
                "agents_used": [agent_name],
                "error": str(e),
            }

    def make_agent_node(name: str):
        async def node(state: AgentState) -> dict:
            return await run_agent(name, state)
        node.__name__ = f"{name}_node"
        return node

    return {name: make_agent_node(name) for name in agents}


def build_graph(agents: dict[str, BaseGrainAgent]) -> StateGraph:
    """构建 LangGraph StateGraph"""

    graph = StateGraph(AgentState)

    # ---- 添加节点 ----
    graph.add_node("router", router_node)

    agent_nodes = build_agent_nodes(agents)
    for name, node_fn in agent_nodes.items():
        graph.add_node(name, node_fn)

    # ---- 通用聚合节点 ----
    async def aggregator_node(state: AgentState) -> dict:
        """聚合所有 Agent 结果"""
        parts = []
        for aname, aresult in state.get("results", {}).items():
            status = "✅" if aresult.get("success") else "❌"
            tc = len(aresult.get("tool_calls", []))
            output = aresult.get("output", "")
            parts.append(f"【{aname}】{status} (工具调用 {tc}次)\n{output[:500]}")

        combined = "\n\n".join(parts)
        if len(state.get("results", {})) > 1:
            # 多 Agent 时让主 Agent 聚合
            main_agent_name = list(agents.keys())[0]
            main_agent = agents[main_agent_name]
            main_agent.request_id = state["request_id"]
            agg_task = f"用户问题：{state['query']}\n\n各 Agent 分析：\n{combined}\n\n请综合以上信息给出完整回答。"
            agg_result = await main_agent.run(agg_task)
            return {"final_answer": agg_result.get("output", combined)}
        else:
            return {"final_answer": combined}

    graph.add_node("aggregator", aggregator_node)

    # ---- 边：路由 ----
    def route_from_router(state: AgentState) -> str:
        scenario = state.get("scenario", "general")
        if scenario == "ventilation":
            # 通风场景需要粮情分析 + 智能作业
            # LangGraph 0.2.x 不支持多目标并行，走先粮情再作业
            if "粮情分析" in agents:
                return "粮情分析"
            return list(agents.keys())[0]
        if scenario == "grain_analysis":
            return "粮情分析" if "粮情分析" in agents else list(agents.keys())[0]
        if scenario == "inoutbound":
            return "出入库" if "出入库" in agents else list(agents.keys())[0]
        if scenario == "report":
            return "报表分析" if "报表分析" in agents else list(agents.keys())[0]
        if scenario == "quality":
            return "质量检测" if "质量检测" in agents else list(agents.keys())[0]
        # general: 走第一个 Agent 处理
        return list(agents.keys())[0]

    graph.add_conditional_edges("router", route_from_router, {name: name for name in agents})

    # 每个 Agent 完成后 -> aggregator
    for name in agents:
        graph.add_edge(name, "aggregator")

    graph.add_edge("aggregator", END)

    # 入口
    graph.set_entry_point("router")

    return graph.compile()


# ========== LangGraphOrchestrator（接口与原 GrainOrchestrator 一致） ==========

class LangGraphOrchestrator:
    """基于 LangGraph 的状态机编排器"""

    def __init__(self):
        self.agents: dict[str, BaseGrainAgent] = {}
        self._app = None

    def register_agent(self, agent: BaseGrainAgent):
        self.agents[agent.name] = agent
        self._app = None  # 强制重建

    def _ensure_graph(self):
        if self._app is None:
            self._app = build_graph(self.agents)

    async def process(self, query: str, role: str = "keeper", session_id: str = "default", model: str = "") -> dict:
        """处理用户查询（带角色感知 + 记忆 + 模型选择）"""
        from src.config import ROLES, MEMORY_MAX_EXCHANGES
        from src.tools.memory import format_history, save_exchange, compress_history

        self._ensure_graph()
        rid = new_request_id()
        start = datetime.now()

        # 注入角色 prompt + 历史记忆（增强版：压缩 + 语义召回）
        role_info = ROLES.get(role, ROLES["keeper"])
        memory_context = format_history(session_id, MEMORY_MAX_EXCHANGES, query=query)
        role_prefix = f"【当前角色：{role_info['icon']} {role_info['label']}】\n{role_info['prompt']}"
        if model:
            role_prefix += f"\n【当前模型：{model}】"
        if memory_context:
            role_prefix += f"\n\n{memory_context}"
        enhanced_query = f"{role_prefix}\n\n用户问题：{query}"

        initial_state: AgentState = {
            "request_id": rid,
            "query": enhanced_query,
            "scenario": "",
            "agents_used": [],
            "tool_calls": [],
            "total_tokens": 0,
            "duration_ms": 0,
            "results": {},
            "final_answer": "",
            "error": None,
        }

        try:
            final_state = await self._app.ainvoke(initial_state)
        except Exception as e:
            # fallback: 如果 Graph 执行失败，用第一个 Agent 兜底
            agent = list(self.agents.values())[0]
            agent.request_id = rid
            result = await agent.run(query, model=model)
            elapsed = int((datetime.now() - start).total_seconds() * 1000)
            record_conversation(rid, query, "fallback", [agent.name],
                                len(result.get("tool_calls", [])), 0, elapsed)
            return {
                "answer": result.get("output", str(e)),
                "request_id": rid,
                "scenario": "fallback",
                "agents_used": [agent.name],
                "processes": [],
                "tool_calls": result.get("tool_calls", []),
            }

        # 保存到记忆 + 尝试压缩
        answer = final_state.get("final_answer", "")
        save_exchange(session_id, query, answer, role,
                      final_state.get("scenario", "general"),
                      final_state.get("agents_used", []))
        compress_history(session_id)

        elapsed = int((datetime.now() - start).total_seconds() * 1000)
        agents_used = final_state.get("agents_used", [])
        tool_calls = final_state.get("tool_calls", [])
        total_tokens = final_state.get("total_tokens", 0)

        record_conversation(
            rid, query, final_state.get("scenario", "general"),
            agents_used, len(tool_calls), total_tokens, elapsed,
        )

        return {
            "answer": final_state.get("final_answer", ""),
            "request_id": rid,
            "scenario": final_state.get("scenario", "general"),
            "agents_used": list(set(agents_used)),
            "processes": [{
                "step": 1,
                "agents": list(set(agents_used)),
                "mode": "LangGraph 状态机",
                "results": [
                    {"agent": an, "success": ar.get("success", False),
                     "output": ar.get("output", "")[:300],
                     "tool_calls": ar.get("tool_calls", []),
                     "elapsed": ar.get("duration_ms", 0) / 1000}
                    for an, ar in final_state.get("results", {}).items()
                ],
            }],
            "tool_calls": tool_calls,
        }

    async def process_stream(self, query: str, role: str = "keeper", session_id: str = "default", model: str = ""):
        """流式处理 — 逐步 yield thinking / tool_calls / conclusion（带角色 + 记忆 + 模型）"""
        from src.config import ROLES, MEMORY_MAX_EXCHANGES
        from src.tools.memory import format_history, save_exchange, compress_history

        self._ensure_graph()
        rid = new_request_id()
        scenario = detect_scenario(query)

        # 注入角色 + 记忆（增强版）
        role_info = ROLES.get(role, ROLES["keeper"])
        memory_context = format_history(session_id, MEMORY_MAX_EXCHANGES, query=query)

        # 构造增强查询
        role_prefix = f"【当前角色：{role_info['icon']} {role_info['label']}】\n{role_info['prompt']}"
        if model:
            role_prefix += f"\n【当前模型：{model}】"
        if memory_context:
            role_prefix += f"\n\n{memory_context}"
        enhanced_query = f"{role_prefix}\n\n用户问题：{query}"

        yield {"type": "plan", "scenario": scenario, "request_id": rid,
               "role": role_info['label'], "session": session_id}
        yield {"type": "step", "step": 1, "agents": list(self.agents.keys()),
               "mode": "LangGraph", "desc": f"{role_info['icon']} {role_info['label']} · {scenario}"}

        # 确定哪些 Agent 参与
        if scenario == "ventilation":
            agent_names = ["粮情分析", "智能作业"]
        elif scenario == "grain_analysis":
            agent_names = ["粮情分析"]
        elif scenario == "inoutbound":
            agent_names = ["出入库"]
        elif scenario == "report":
            agent_names = ["报表分析", "粮情分析"]
        elif scenario == "quality":
            agent_names = ["质量检测"]
        else:
            agent_names = ["智能作业"]  # 通用场景只跑主Agent，避免全部跑一遍耗时

        results = {}
        tool_calls_all = []

        for name in agent_names:
            if name not in self.agents:
                continue
            agent = self.agents[name]
            agent.request_id = rid

            # yield thinking 事件（真正在 Agent 执行前发出）
            yield {"type": "thinking", "agent": name, "task": "分析中..."}

            # 执行 Agent
            from datetime import datetime
            st = datetime.now()
            try:
                result = await agent.run(enhanced_query, model=model)
                elapsed = (datetime.now() - st).total_seconds()
                results[name] = result
                tc = result.get("tool_calls", [])
                tool_calls_all.extend(tc)

                # yield 工具调用摘要
                yield {"type": "tool_calls", "agent": name,
                       "calls": [{"tool": t["tool"], "input": str(t["input"])[:40]} for t in tc[:5]]}

                # yield 完成事件
                yield {"type": "agent_done", "agent": name,
                       "elapsed": round(elapsed, 1), "tool_count": len(tc)}
            except Exception as e:
                yield {"type": "agent_error", "agent": name, "error": str(e)}

        # yield 结论
        combined = "\n\n".join([
            f"【{r['agent']}】\n{r['output'][:500]}" for r in results.values()
        ])
        if len(results) > 1 and "智能作业" in self.agents:
            main = self.agents["智能作业"]
            main.request_id = rid
            agg = f"用户问题:{query}\n各Agent结果:\n{combined}\n请综合回答"
            final = await main.run(agg)
            answer = final["output"]
        elif results:
            answer = list(results.values())[0]["output"]
        else:
            answer = "没有 Agent 能处理该查询。"

        # 存记忆 + 尝试压缩
        save_exchange(session_id, query, answer, role, scenario, agent_names)
        compress_history(session_id)

        yield {"type": "conclusion", "text": answer}
        yield {"type": "done", "agents_used": agent_names,
               "role": role_info['label'],
               "tool_calls_count": len(tool_calls_all)}
