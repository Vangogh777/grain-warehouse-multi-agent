"""Orchestrator 编排器 — 多 Agent 并行调度、消息路由、结果聚合"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional
from src.agents.base_agent import BaseGrainAgent


class GrainOrchestrator:
    """粮库多智能体编排器

    职责：
    - 接收用户请求，解析意图
    - 将任务分发给对应的 Agent
    - 支持多个 Agent 并行执行
    - 聚合各 Agent 结果，生成最终回答
    """

    def __init__(self):
        self.agents: dict[str, BaseGrainAgent] = {}
        self.conversation_history: list[dict] = []

    def register_agent(self, agent: BaseGrainAgent):
        """注册一个 Agent"""
        self.agents[agent.name] = agent

    def _detect_scenario(self, query: str) -> str:
        """检测用户意图场景"""
        q = query.lower()
        has_ventilation = any(k in q for k in ["通风", "作业条件", "满足条件", "能开风机"])
        has_grain = any(k in q for k in ["粮情", "异常", "温度", "湿度", "粮温", "变化", "粮情变化"])
        has_fumigation = any(k in q for k in ["熏蒸", "虫害", "杀虫"])
        has_inout = any(k in q for k in ["出入库", "入库", "出库", "车辆", "业务量", "今天业务"])
        has_report = any(k in q for k in ["报表", "报告", "统计", "库存", "日报", "月报", "汇总"])

        if has_ventilation or has_fumigation:
            return "ventilation"
        if has_inout:
            return "inoutbound"
        if has_report:
            return "report"
        if has_grain:
            return "grain_analysis"
        return "general"

    def _extract_silo_id(self, query: str) -> Optional[str]:
        """从查询中提取仓房编号"""
        import re
        match = re.search(r'S-\d{1,2}', query.upper())
        return match.group(0) if match else None

    async def _run_agent(self, agent: BaseGrainAgent, task: str) -> dict:
        """运行单个 Agent"""
        start = datetime.now()
        try:
            result = await agent.run(task)
            elapsed = (datetime.now() - start).total_seconds()
            return {
                **result,
                "elapsed_seconds": round(elapsed, 2),
            }
        except Exception as e:
            return {
                "agent": agent.name,
                "success": False,
                "output": f"Agent 执行出错: {str(e)}",
                "tool_calls": [],
                "elapsed_seconds": 0,
            }

    async def process(self, query: str) -> dict:
        """处理用户查询 — 主入口"""
        request_id = str(uuid.uuid4())[:8]
        scenario = self._detect_scenario(query)
        silo_id = self._extract_silo_id(query)
        processes = []
        agents_used = []

        # ========== 通风条件判断场景 ==========
        if scenario == "ventilation":
            sid = silo_id or "S-07"
            # 并行 Step 1: 粮情分析 + 天气/电价查询（不依赖）
            grain_task = f"请分析仓房 {sid} 的当前粮情状态，包括温度（各层）、湿度、水分，并给出是否正常的判断。"
            weather_task = "请查询当前天气、未来24小时预报和当前电价，判断是否适合进行通风作业。"

            grain_future = self._run_agent(self.agents["粮情分析"], grain_task)
            weather_future = self._run_agent(self.agents["智能作业"], weather_task)

            results = await asyncio.gather(grain_future, weather_future)
            grain_result = results[0]
            weather_result = results[1]

            processes.append({
                "step": 1,
                "agents": ["粮情分析", "智能作业"],
                "mode": "并行",
                "results": [grain_result, weather_result],
            })
            agents_used.extend(["粮情分析", "智能作业"])

            # Step 2: 基于粮情和天气，做综合判断（依赖 Step 1 结果）
            combined_context = f"""
粮情分析结果：
{grain_result['output']}

天气和电价信息：
{weather_result['output']}

请基于以上信息，综合判断仓房 {sid} 是否满足通风条件。
如满足，请给出具体的作业方案（时间、设备、参数）。
如不满足，请说明原因和建议。
"""
            decision_result = await self._run_agent(
                self.agents["智能作业"], combined_context
            )
            processes.append({
                "step": 2,
                "agents": ["智能作业"],
                "mode": "串行（综合决策）",
                "results": [decision_result],
            })

            final_answer = decision_result["output"]
            all_tool_calls = (
                grain_result.get("tool_calls", [])
                + weather_result.get("tool_calls", [])
                + decision_result.get("tool_calls", [])
            )

        # ========== 粮情分析场景 ==========
        elif scenario == "grain_analysis":
            sid_hint = f"重点关注 {silo_id}" if silo_id else "分析全部仓房"
            task = f"请分析最近粮情变化和异常情况。{sid_hint}。查询传感器数据，检查温度异常、湿度异常、虫害情况。"
            result = await self._run_agent(self.agents["粮情分析"], task)
            processes.append({
                "step": 1,
                "agents": ["粮情分析"],
                "mode": "串行",
                "results": [result],
            })
            agents_used.append("粮情分析")
            final_answer = result["output"]
            all_tool_calls = result.get("tool_calls", [])

        # ========== 出入库场景 ==========
        elif scenario == "inoutbound":
            task = f"用户查询出入库业务：{query}。请查询今日入库/出库数据，汇总业务情况，给出完整的业务简报。"
            result = await self._run_agent(self.agents["出入库"], task)
            processes.append({
                "step": 1,
                "agents": ["出入库"],
                "mode": "串行",
                "results": [result],
            })
            agents_used.append("出入库")
            final_answer = result["output"]
            all_tool_calls = result.get("tool_calls", [])

        # ========== 报表场景 ==========
        elif scenario == "report":
            # 并行查库存 + 查异常
            inv_future = self._run_agent(self.agents["报表分析"], f"{query}。请查询库存汇总和异常仓房分析。")
            trend_future = self._run_agent(self.agents["粮情分析"], "请分析当前粮情整体情况，有哪些异常或需要关注的点。")
            results = await asyncio.gather(inv_future, trend_future)
            processes.append({
                "step": 1,
                "agents": ["报表分析", "粮情分析"],
                "mode": "并行",
                "results": results,
            })
            agents_used.extend(["报表分析", "粮情分析"])

            combined = f"""报表数据：
{results[0]['output']}

粮情数据：
{results[1]['output']}

请综合以上报表数据和粮情数据，生成一份完整的报告。"""
            final = await self._run_agent(self.agents["报表分析"], combined)
            processes.append({
                "step": 2,
                "agents": ["报表分析"],
                "mode": "串行（报告生成）",
                "results": [final],
            })
            final_answer = final["output"]
            all_tool_calls = results[0].get("tool_calls", []) + results[1].get("tool_calls", []) + final.get("tool_calls", [])

        # ========== 通用场景 ==========
        else:
            # 并行调用所有 Agent
            tasks = []
            agent_list = list(self.agents.items())

            for name, agent in agent_list:
                tasks.append(self._run_agent(agent, query))

            results = await asyncio.gather(*tasks)
            processes.append({
                "step": 1,
                "agents": [name for name, _ in agent_list],
                "mode": "并行（全部 Agent）",
                "results": results,
            })
            agents_used = [name for name, _ in agent_list]

            # 聚合结果
            combined = "\n\n".join([
                f"【{r['agent']}】\n{r['output']}" for r in results
            ])
            aggregate_task = f"""
用户问题：{query}

以下是各 Agent 的分析结果：
{combined}

请综合以上信息，给出一个完整、清晰的回答。
"""
            if "智能作业" in self.agents:
                final = await self._run_agent(
                    self.agents["智能作业"], aggregate_task
                )
                processes.append({
                    "step": 2,
                    "agents": ["智能作业"],
                    "mode": "串行（结果聚合）",
                    "results": [final],
                })
                final_answer = final["output"]
                all_tool_calls = sum((r.get("tool_calls", []) for r in results), []) + final.get("tool_calls", [])
            else:
                final_answer = combined
                all_tool_calls = []

        # 记录会话
        self.conversation_history.append({
            "request_id": request_id,
            "query": query,
            "scenario": scenario,
            "agents_used": list(set(agents_used)),
            "tool_calls_count": len(all_tool_calls),
            "timestamp": datetime.now().isoformat(),
        })

        return {
            "answer": final_answer,
            "request_id": request_id,
            "scenario": scenario,
            "agents_used": list(set(agents_used)),
            "processes": processes,
            "tool_calls": all_tool_calls,
        }

    async def process_stream(self, query: str):
        """流式处理 — 每次 LLM 调用前发 thinking 事件，避免卡顿感"""
        rid = str(uuid.uuid4())[:8]
        scenario = self._detect_scenario(query)
        silo_id = self._extract_silo_id(query)
        agents_used, all_tc = [], []
        yield {"type": "plan", "scenario": scenario, "request_id": rid}

        async def run_agent_stream(name, task, label=""):
            """yield thinking → 执行 → yield 结果"""
            agents_used.append(name)
            yield {"type": "thinking", "agent": name, "task": label or task[:60]}
            st = datetime.now()
            try:
                r = await self.agents[name].run(task)
                el = (datetime.now()-st).total_seconds()
                tc = r.get("tool_calls",[]); all_tc.extend(tc)
                yield {"type": "tool_calls", "agent": name, "calls": [{"tool":t["tool"],"input":str(t["input"])[:40]} for t in tc]}
                yield {"type": "agent_done", "agent": name, "elapsed": round(el,1), "tool_count": len(tc)}
            except Exception as e:
                yield {"type": "agent_error", "agent": name, "error": str(e)}

        def _thinking(name, label=""):
            """发送 thinking 事件"""
            return {"type": "thinking", "agent": name, "task": label}

        if scenario == "ventilation":
            sid = silo_id or "S-07"
            yield {"type": "step", "step": 1, "agents": ["粮情分析","智能作业"], "mode": "并行", "desc": "粮情分析查数据 + 智能作业查天气/电价"}
            agents_used.extend(["粮情分析","智能作业"])
            yield _thinking("粮情分析", "读取传感器数据...")
            yield _thinking("智能作业", "查询天气、电价...")
            gf = self._run_agent(self.agents["粮情分析"], f"分析{sid}仓粮情数据")
            wf = self._run_agent(self.agents["智能作业"], "查询天气、电价、设备状态")
            gr, wr = await asyncio.gather(gf, wf)
            all_tc.extend(gr.get("tool_calls",[])+wr.get("tool_calls",[]))
            yield {"type": "tool_calls", "agent": "粮情分析", "calls": [{"tool":t["tool"],"input":str(t["input"])[:40]} for t in gr.get("tool_calls",[])]}
            yield {"type": "tool_calls", "agent": "智能作业", "calls": [{"tool":t["tool"],"input":str(t["input"])[:40]} for t in wr.get("tool_calls",[])]}
            yield {"type": "agent_done", "agent": "粮情分析", "elapsed": round(0,1), "tool_count": len(gr.get("tool_calls",[]))}
            yield {"type": "agent_done", "agent": "智能作业", "elapsed": round(0,1), "tool_count": len(wr.get("tool_calls",[]))}
            yield {"type": "step", "step": 2, "agents": ["智能作业"], "mode": "串行", "desc": "综合判断通风条件"}
            yield _thinking("智能作业", "综合分析中...")
            combined = f"粮情:{gr['output'][:500]}\n天气:{wr['output'][:500]}\n综合判断{sid}是否满足通风条件并给出方案"
            dr = await self._run_agent(self.agents["智能作业"], combined)
            all_tc.extend(dr.get("tool_calls",[]))
            final = dr["output"]

        elif scenario == "inoutbound":
            yield {"type": "step", "step": 1, "agents": ["出入库"], "mode": "串行", "desc": "查询出入库数据"}
            agents_used.append("出入库")
            yield _thinking("出入库", "查询订单和结算数据...")
            r = await self._run_agent(self.agents["出入库"], f"用户查询出入库业务：{query}")
            all_tc.extend(r.get("tool_calls",[]))
            final = r["output"]

        elif scenario == "report":
            yield {"type": "step", "step": 1, "agents": ["报表分析","粮情分析"], "mode": "并行", "desc": "查库存+查异常"}
            agents_used.extend(["报表分析","粮情分析"])
            yield _thinking("报表分析", "查询库存数据...")
            yield _thinking("粮情分析", "分析异常仓房...")
            ir = await self._run_agent(self.agents["报表分析"], f"{query}，查库存和异常")
            tr = await self._run_agent(self.agents["粮情分析"], "分析当前粮情异常")
            all_tc.extend(ir.get("tool_calls",[])+tr.get("tool_calls",[]))
            yield {"type": "step", "step": 2, "agents": ["报表分析"], "mode": "串行", "desc": "生成报告"}
            yield _thinking("报表分析", "正在生成报告...")
            combined = f"报表:{ir['output'][:500]}\n粮情:{tr['output'][:500]}\n综合生成完整报告"
            fr = await self._run_agent(self.agents["报表分析"], combined)
            final = fr["output"]
        else:
            yield {"type": "step", "step": 1, "agents": list(self.agents.keys()), "mode": "并行", "desc": "全部 Agent"}
            for name in list(self.agents.keys()):
                agents_used.append(name)
                yield _thinking(name, "分析中...")
            tasks = {}
            for n, a in self.agents.items():
                tasks[n] = self._run_agent(a, query)
            results = await asyncio.gather(*tasks.values())
            for n, r in zip(tasks.keys(), results):
                all_tc.extend(r.get("tool_calls",[]))
            combined = "\n\n".join([f"【{r['agent']}】\n{r['output'][:300]}" for r in results])
            agg = f"用户问题:{query}\n各Agent结果:\n{combined}\n请综合回答"
            fr = await self._run_agent(self.agents.get("智能作业", list(self.agents.values())[0]), agg)
            final = fr["output"]

        self.conversation_history.append({"request_id": rid, "query": query, "scenario": scenario})
        yield {"type": "conclusion", "text": final}
        yield {"type": "done", "agents_used": list(set(agents_used)), "tool_calls_count": len(all_tc)}
