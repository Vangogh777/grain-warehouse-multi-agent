"""Agent 基类 — 基于 LangChain AgentExecutor（OpenAI 工具调用模式）"""
from typing import Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, LLM_TEMPERATURE


class BaseGrainAgent:
    """所有子 Agent 的基类，封装 LangChain AgentExecutor

    使用 OpenAI 工具调用模式（兼容 DeepSeek API）。
    Agent 内部通过 function calling 调用工具，无需 ReAct 文本格式。
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list[BaseTool],
        llm: Optional[ChatOpenAI] = None,
        max_iterations: int = 10,
    ):
        self.name = name
        self.tools = tools
        self.tool_names = [t.name for t in tools]

        self.llm = llm or ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=LLM_TEMPERATURE,
        )

        # ChatML 格式提示词
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是 {name}。\n\n{system_prompt}"),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(self.llm, tools, prompt)
        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=max_iterations,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )

    async def run(self, input_text: str, context: dict = None) -> dict:
        """执行 Agent 任务，返回结果和中间步骤"""
        result = await self.executor.ainvoke({
            "input": input_text,
            "name": self.name,
            "system_prompt": context.get("system_prompt_extra", "") if context else "",
        })

        # 提取工具调用信息
        tool_calls = []
        for step in result.get("intermediate_steps", []):
            action, observation = step
            tool_calls.append({
                "tool": action.tool,
                "input": str(action.tool_input),
                "output": str(observation)[:300],
            })

        return {
            "agent": self.name,
            "success": True,
            "output": result.get("output", ""),
            "tool_calls": tool_calls,
        }
