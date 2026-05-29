# -*- coding: utf-8 -*-
"""Debug script - Test DeepSeek tool calling"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from typing import Type


class TestInput(BaseModel):
    query: str = Field(description="query content")


class TestTool(BaseTool):
    name: str = "get_test_data"
    description: str = "Get test data"
    args_schema: Type[BaseModel] = TestInput

    def _run(self, query: str) -> str:
        return f"Test data: {query}"


async def test_basic_chat():
    """Test basic chat"""
    print("\n=== Test 1: Basic Chat ===")
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0.3,
    )
    try:
        result = await llm.ainvoke("Hello, please reply 'test success'")
        print(f"[OK] Basic chat success: {result.content[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Basic chat failed: {type(e).__name__}: {e}")
        return False


async def test_tool_call():
    """Test tool calling (using bind_tools directly)"""
    print("\n=== Test 2: Direct Tool Call ===")
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0.3,
    )

    # Bind tools
    tools = [TestTool()]
    llm_with_tools = llm.bind_tools(tools)

    try:
        result = await llm_with_tools.ainvoke("Please get test data with content 'hello'")
        print(f"Response type: {type(result)}")
        print(f"Content: {result.content[:200] if result.content else 'No content'}")
        print(f"Tool calls: {result.tool_calls if hasattr(result, 'tool_calls') else 'None'}")
        return True
    except Exception as e:
        print(f"[FAIL] Tool call failed: {type(e).__name__}: {e}")
        return False


async def test_agent():
    """Test Agent execution"""
    print("\n=== Test 3: Agent Execution ===")
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0.3,
    )

    tools = [TestTool()]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a test assistant that can use tools to get data."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    try:
        agent = create_openai_tools_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        result = await executor.ainvoke({"input": "Please get test data with content 'hello'"})
        print(f"[OK] Agent execution success: {result.get('output', '')[:200]}")
        return True
    except Exception as e:
        print(f"[FAIL] Agent execution failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    # Load .env
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    print("=" * 50)
    print("DeepSeek Tool Calling Debug")
    print("=" * 50)

    print(f"\nAPI Key: {os.getenv('DEEPSEEK_API_KEY', 'NOT SET')[:20]}...")
    print(f"Base URL: {os.getenv('DEEPSEEK_BASE_URL', 'NOT SET')}")
    print(f"Model: {os.getenv('DEEPSEEK_MODEL', 'NOT SET')}")

    results = []
    results.append(("Basic Chat", await test_basic_chat()))
    results.append(("Tool Call", await test_tool_call()))
    results.append(("Agent Execution", await test_agent()))

    print("\n" + "=" * 50)
    print("Test Results Summary:")
    for name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {name}")


if __name__ == "__main__":
    asyncio.run(main())
