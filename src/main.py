"""粮库多智能体系统 — CLI Demo 主入口（4 Agent 完整版）"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.mock_data import refresh_sensor_data
from src.agents.grain_condition import create_grain_condition_agent
from src.agents.operation import create_operation_agent
from src.agents.inoutbound import create_inoutbound_agent
from src.agents.report import create_report_agent
from src.agents.quality import create_quality_agent
from src.orchestrator.graph_orchestrator import LangGraphOrchestrator


def init_system() -> LangGraphOrchestrator:
    """初始化全部 5 个 Agent 并注册到编排器"""
    refresh_sensor_data()
    grain = create_grain_condition_agent()
    op = create_operation_agent()
    io = create_inoutbound_agent()
    rpt = create_report_agent()
    qual = create_quality_agent()
    
    print(f"  ✅ 粮情分析 Agent (工具: {grain.tool_names})")
    print(f"  ✅ 智能作业 Agent (工具: {op.tool_names})")
    print(f"  ✅ 出入库 Agent (工具: {io.tool_names})")
    print(f"  ✅ 报表分析 Agent (工具: {rpt.tool_names})")
    print(f"  ✅ 质量检测 Agent (工具: {qual.tool_names})")
    
    orch = LangGraphOrchestrator()
    orch.register_agent(grain)
    orch.register_agent(op)
    orch.register_agent(io)
    orch.register_agent(rpt)
    orch.register_agent(qual)
    return orch


async def demo_ventilation():
    """通风条件判断演示"""
    print("\n" + "=" * 60)
    print("  🌾 粮库多智能体系统 · 通风条件判断")
    print("=" * 60)
    print("\n📋 场景: S-07 仓是否满足通风条件？")
    print("🧠 涉及: 粮情分析 + 智能作业（并行→串行协同）")
    
    print("\n🔄 初始化系统...")
    orch = init_system()
    
    print("\n🚀 执行并行推理...")
    result = await orch.process("S-07仓当前是否满足通风条件？请分析并给出作业方案")
    
    print("\n📊 执行过程:")
    for step in result["processes"]:
        agents = ", ".join(step["agents"])
        print(f"  Step {step['step']} | {step['mode']} | {agents}")
        for r in step["results"]:
            tc = len(r.get("tool_calls", []))
            print(f"    {'✅' if r['success'] else '❌'} {r['agent']} ({r.get('elapsed_seconds',0):.1f}s, {tc}次工具调用)")
    
    print("\n" + "=" * 60)
    print("✅ 结论:")
    print(result["answer"][:1500])
    print(f"\n🤖 Agent: {result['agents_used']} | 🔧 工具调用: {len(result['tool_calls'])}次")


async def interactive_mode():
    """交互模式 — 支持所有 Agent"""
    print("\n🔄 初始化 5 个 Agent（接入 DeepSeek API）...")
    orch = init_system()
    print("\n✅ 系统就绪！支持以下场景：")
    print("   🌡 粮情分析 — S-07温度多少？最近粮情有什么变化？")
    print("   ⚙ 智能作业 — S-07满足通风条件吗？S-03需要熏蒸吗？")
    print("   🚛 出入库 — 今天出入库情况如何？查询今日入库记录")
    print("   📋 报表分析 — 生成今日库存日报、哪些仓房有异常？")
    print("   📋 质量检测 — 小麦的质量等级分布？S-03最近三批稻谷质量如何？")
    print("\n💬 输入问题开始 (q 退出)\n")

    while True:
        try:
            query = input("> ").strip()
            if query.lower() in ("q", "quit", "exit"):
                break
            if not query:
                continue

            print("⏳ 多 Agent 协同分析中...")
            result = await orch.process(query)

            print(f"\n{'─' * 50}")
            for step in result["processes"]:
                agents = ", ".join(step["agents"])
                print(f"  Step {step['step']} | {step['mode']} | {agents}")
            print(f"\n{result['answer'][:2000]}")
            if len(result['answer']) > 2000:
                print("...（内容较长已截断）")
            print(f"{'─' * 50}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


async def main():
    print("\n🌾 粮库仓储多智能体系统 (5 Agent)")
    print("=" * 45)
    print("1. 演示: 通风条件判断（最小闭环）")
    print("2. 交互模式（自由提问）")
    print("q. 退出")

    choice = input("\n请选择 [1/2/q]: ").strip()
    if choice == "1":
        await demo_ventilation()
    elif choice == "2":
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
