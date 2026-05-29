"""Debate 辩论编排器 — 多 Agent 独立分析 + 加权投票"""
import asyncio
import json
import re
from datetime import datetime
from typing import Optional

from src.agents.base_agent import BaseGrainAgent
from src.tools.observability import new_request_id, record_conversation


class DebateOrchestrator:
    """多 Agent 辩论投票编排器"""

    def __init__(self):
        self.agents: dict[str, BaseGrainAgent] = {}

    def register_agent(self, agent: BaseGrainAgent):
        self.agents[agent.name] = agent

    async def debate(self, query: str, role: str = "keeper",
                     session_id: str = "default", model: str = "") -> dict:
        """并行调所有 Agent → 投票聚合"""
        rid = new_request_id()
        start = datetime.now()

        if not self.agents:
            return {"answer": "没有注册任何 Agent", "votes": {}, "winner": ""}

        # 1. 并行调所有 Agent
        tasks = []
        agent_names = []
        for name, agent in self.agents.items():
            agent.request_id = rid
            debate_prompt = (
                f"{query}\n\n"
                f"请从你的专业角度分析，输出 JSON 格式：\n"
                f'{{"conclusion":"你的结论","confidence":0.85,"reason":"判断理由","suggestion":"具体建议"}}\n'
                f"confidence 范围 0~1，越高越确定。"
            )
            tasks.append(agent.run(debate_prompt, model=model))
            agent_names.append(name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2. 解析各 Agent 结论
        votes = {}
        details = []
        for i, name in enumerate(agent_names):
            r = results[i]
            if isinstance(r, Exception):
                details.append({"agent": name, "success": False, "error": str(r)})
                continue

            output = r.get("output", "")
            parsed = self._parse_conclusion(output)
            confidence = parsed.get("confidence", 0.5)
            conclusion = parsed.get("conclusion", "无法判断")

            # 加权投票
            votes[conclusion] = votes.get(conclusion, 0) + confidence

            details.append({
                "agent": name,
                "success": True,
                "conclusion": conclusion,
                "confidence": confidence,
                "reason": parsed.get("reason", ""),
                "suggestion": parsed.get("suggestion", ""),
                "raw": output[:200],
            })

        # 3. 聚合
        if not votes:
            return {"answer": "所有 Agent 均未能给出结论", "votes": {}, "winner": "", "details": details}

        winner = max(votes, key=votes.get)
        total = sum(votes.values())
        vote_breakdown = {k: {"score": round(v, 2), "pct": round(v / total * 100, 1) if total > 0 else 0}
                         for k, v in sorted(votes.items(), key=lambda x: -x[1])}

        # 4. 生成最终回答
        lines = [f"## 🤝 多 Agent 辩论结果\n"]
        lines.append(f"### 问题：{query}\n")
        lines.append(f"**🏆 最终结论：{winner}**（得分 {vote_breakdown[winner]['pct']}%）\n")

        # 分歧说明
        if len(votes) > 1:
            dissent = [k for k in votes if k != winner]
            lines.append(f"⚠️ 存在分歧：{'、'.join(dissent)}\n")

        lines.append("\n### 各 Agent 分析\n")
        for d in details:
            icon = "✅" if d.get("success") else "❌"
            c = d.get("conclusion", "N/A")
            conf = d.get("confidence", 0)
            bar = "█" * int(conf * 20) + "░" * (20 - int(conf * 20))
            lines.append(f"{icon} **{d['agent']}**：{c}")
            lines.append(f"   置信度 {bar} {conf:.0%}")
            if d.get("reason"):
                lines.append(f"   理由：{d['reason']}")
            lines.append("")

        answer = "\n".join(lines)
        elapsed = int((datetime.now() - start).total_seconds() * 1000)
        record_conversation(rid, query, "debate", agent_names, len(details), 0, elapsed)

        return {
            "answer": answer,
            "winner": winner,
            "votes": vote_breakdown,
            "details": details,
            "request_id": rid,
        }

    def _parse_conclusion(self, text: str) -> dict:
        """从 Agent 输出中提取结构化结论"""
        # 尝试提取 JSON
        json_match = re.search(r'\{[^{}]*"conclusion"[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 用 LLM 的输出本身判断
        text_lower = text.lower()
        confidence = 0.6  # 默认

        # 提取置信度关键词
        if "确定" in text or "一定" in text:
            confidence = 0.8
        elif "可能" in text or "或许" in text:
            confidence = 0.4
        elif "不确定" in text:
            confidence = 0.2

        return {
            "conclusion": text[:100],
            "confidence": confidence,
            "reason": text[:150],
            "suggestion": "",
        }
