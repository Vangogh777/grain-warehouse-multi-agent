# -*- coding: utf-8 -*-
"""Debug script - Test actual Grain Agent tool calling"""
import asyncio
import os
import sys
import json

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from src.tools.mock_data import refresh_sensor_data
from src.agents.grain_condition import create_grain_condition_agent
from src.agents.operation import create_operation_agent


async def test_grain_agent():
    """Test grain condition agent"""
    print("\n=== Test: Grain Condition Agent ===")
    refresh_sensor_data()

    agent = create_grain_condition_agent()
    print(f"Agent: {agent.name}")
    print(f"Tools: {agent.tool_names}")

    try:
        result = await agent.run("S-07仓当前粮情如何？")
        output = result.get('output', '')
        # Remove emojis for display
        output_clean = output.encode('ascii', 'replace').decode('ascii')
        print(f"[OK] Success (first 300 chars): {output_clean[:300]}")
        print(f"Tool calls count: {len(result.get('tool_calls', []))}")
        print(f"Success: {result.get('success')}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_operation_agent():
    """Test operation agent"""
    print("\n=== Test: Operation Agent ===")
    refresh_sensor_data()

    agent = create_operation_agent()
    print(f"Agent: {agent.name}")
    print(f"Tools: {agent.tool_names}")

    try:
        result = await agent.run("请查询当前天气和电价")
        output = result.get('output', '')
        output_clean = output.encode('ascii', 'replace').decode('ascii')
        print(f"[OK] Success (first 300 chars): {output_clean[:300]}")
        print(f"Tool calls count: {len(result.get('tool_calls', []))}")
        print(f"Success: {result.get('success')}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_orchestrator():
    """Test full orchestrator"""
    print("\n=== Test: Full Orchestrator ===")
    refresh_sensor_data()

    from src.orchestrator.graph_orchestrator import LangGraphOrchestrator
    from src.agents.inoutbound import create_inoutbound_agent
    from src.agents.report import create_report_agent
    from src.agents.quality import create_quality_agent

    orch = LangGraphOrchestrator()
    orch.register_agent(create_grain_condition_agent())
    orch.register_agent(create_operation_agent())
    orch.register_agent(create_inoutbound_agent())
    orch.register_agent(create_report_agent())
    orch.register_agent(create_quality_agent())

    try:
        result = await orch.process("S-07满足通风条件吗？")
        answer = result.get('answer', '')
        answer_clean = answer.encode('ascii', 'replace').decode('ascii')
        print(f"[OK] Success")
        print(f"Answer (first 500 chars): {answer_clean[:500]}")
        print(f"Agents used: {result.get('agents_used', [])}")
        print(f"Tool calls count: {len(result.get('tool_calls', []))}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 50)
    print("Grain Agent Tool Calling Debug")
    print("=" * 50)

    results = []
    results.append(("Grain Agent", await test_grain_agent()))
    results.append(("Operation Agent", await test_operation_agent()))
    results.append(("Full Orchestrator", await test_full_orchestrator()))

    print("\n" + "=" * 50)
    print("Test Results Summary:")
    for name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {name}")


if __name__ == "__main__":
    asyncio.run(main())
