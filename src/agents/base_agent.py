"""Agent 基类 — 基于 LangChain AgentExecutor（OpenAI 工具调用模式）"""
import time
import asyncio
from typing import Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from src.config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    LLM_TEMPERATURE, LLM_TIMEOUT, LLM_MAX_RETRIES, CUSTOM_GET_TOKEN_IDS,
    REASONING_MODELS, MODEL_CONFIGS, TOOL_MODEL_MAP,
)


class BaseGrainAgent:
    """所有子 Agent 的基类，封装 LangChain AgentExecutor"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list[BaseTool],
        llm: Optional[ChatOpenAI] = None,
        max_iterations: int = 10,
        request_id: str = "",
        model: str = "",
    ):
        self.name = name
        self.tools = tools
        self.tool_names = [t.name for t in tools]
        self.request_id = request_id
        self._current_model = model or DEEPSEEK_MODEL
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations

        self.llm = llm or ChatOpenAI(
            model=self._current_model,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT,
            max_retries=LLM_MAX_RETRIES,
            custom_get_token_ids=CUSTOM_GET_TOKEN_IDS,
        )

        self._rebuild_executor()

    def _get_model_api_config(self, model: str) -> dict:
        """获取模型对应的 API Key 和 Base URL（支持按模型定制）"""
        cfg = MODEL_CONFIGS.get(model, {})
        return {
            "api_key": cfg.get("api_key", DEEPSEEK_API_KEY),
            "base_url": cfg.get("base_url", DEEPSEEK_BASE_URL),
        }

    def _rebuild_executor(self):
        """重建 LLM 和 AgentExecutor（推理模型走纯文本路径）"""
        api_cfg = self._get_model_api_config(self._current_model)
        self.llm = ChatOpenAI(
            model=self._current_model,
            api_key=api_cfg["api_key"],
            base_url=api_cfg["base_url"],
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT,
            max_retries=LLM_MAX_RETRIES,
            custom_get_token_ids=CUSTOM_GET_TOKEN_IDS,
        )
        self._is_reasoning = self._current_model in REASONING_MODELS

        if self._is_reasoning:
            # 推理模型：executor 用不上，工具调用在 run() 里手动处理
            self.executor = None
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是 {name}。\n\n{system_prompt}"),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            self.executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=False,
                max_iterations=self._max_iterations,
                handle_parsing_errors=True,
                return_intermediate_steps=True,
            )

    def set_model(self, model: str):
        """切换模型（运行时生效）"""
        if model and model != self._current_model:
            self._current_model = model
            self._rebuild_executor()

    async def run(self, input_text: str, context: dict = None, model: str = "") -> dict:
        """执行 Agent 任务，带自动重试"""
        from src.tools.observability import record_llm_call, record_tool_call

        if model:
            self.set_model(model)

        last_error = None
        for attempt in range(1 + LLM_MAX_RETRIES):
            try:
                start = time.time()

                if self._is_reasoning:
                    # 混合模式：快模型调工具 → 推理模型做分析
                    system_prompt_extra = context.get("system_prompt_extra", "") if context else ""
                    tool_model = TOOL_MODEL_MAP.get(self._current_model, "")
                    tool_calls = []

                    if tool_model:
                        # 创建快模型 (DeepSeek V3) 执行工具调用
                        tool_api_cfg = self._get_model_api_config(tool_model)
                        tool_llm = ChatOpenAI(
                            model=tool_model,
                            api_key=tool_api_cfg["api_key"] or DEEPSEEK_API_KEY,
                            base_url=tool_api_cfg["base_url"] or DEEPSEEK_BASE_URL,
                            temperature=LLM_TEMPERATURE, timeout=LLM_TIMEOUT,
                            max_retries=LLM_MAX_RETRIES,
                            custom_get_token_ids=CUSTOM_GET_TOKEN_IDS,
                        )
                        tool_prompt = ChatPromptTemplate.from_messages([
                            ("system", f"你是 {self.name}。\n\n{self._system_prompt}\n{system_prompt_extra}\n请调用工具获取数据，不要分析。"),
                            MessagesPlaceholder(variable_name="chat_history", optional=True),
                            ("human", "{input}"),
                            MessagesPlaceholder(variable_name="agent_scratchpad"),
                        ])
                        tool_agent = create_openai_tools_agent(tool_llm, self.tools, tool_prompt)
                        tool_executor = AgentExecutor(
                            agent=tool_agent, tools=self.tools, verbose=False,
                            max_iterations=self._max_iterations,
                            handle_parsing_errors=True, return_intermediate_steps=True,
                        )
                        tool_result = await tool_executor.ainvoke({
                            "input": f"请调用相关工具查询数据，无需分析。问题：{input_text}",
                            "name": self.name,
                        })
                        for step in tool_result.get("intermediate_steps", []):
                            action, observation = step
                            tool_calls.append({
                                "tool": action.tool, "input": str(action.tool_input),
                                "output": str(observation)[:300],
                                "duration_ms": 0, "depends_on": [],
                            })
                            record_tool_call(request_id=self.request_id, agent_name=self.name,
                                tool_name=action.tool, tool_input=str(action.tool_input),
                                tool_output=str(observation)[:200], duration_ms=0, success=True)

                        tool_data = tool_result.get("output", "")
                    else:
                        tool_data = ""

                    # 把数据送给推理模型做分析
                    analysis_prompt = (
                        f"{self._system_prompt}\n{system_prompt_extra}\n\n"
                        f"以下是查询到的数据：\n{tool_data[:2000]}\n\n"
                        f"请基于以上数据，分析并回答用户问题：\n{input_text}"
                    )
                    msg = await self.llm.ainvoke(analysis_prompt)
                    elapsed_ms = int((time.time() - start) * 1000)
                    result = {"output": msg.content}
                else:
                    result = await self.executor.ainvoke({
                        "input": input_text,
                        "name": self.name,
                        "system_prompt": context.get("system_prompt_extra", "") if context else "",
                    })
                    elapsed_ms = int((time.time() - start) * 1000)

                    # 提取工具调用
                    tool_calls = []
                    for i, step in enumerate(result.get("intermediate_steps", [])):
                        action, observation = step
                        # 记录工具调用时间点（近似：每个工具用时约 elapsed_ms / len(steps)）
                        tc = {
                            "tool": action.tool,
                            "input": str(action.tool_input),
                            "output": str(observation)[:300],
                            "duration_ms": elapsed_ms // max(len(result.get("intermediate_steps", [])), 1),
                            "depends_on": [tool_calls[-1]["tool"]] if tool_calls else [],
                        }
                        tool_calls.append(tc)
                        record_tool_call(
                            request_id=self.request_id,
                            agent_name=self.name,
                            tool_name=action.tool,
                            tool_input=str(action.tool_input),
                            tool_output=str(observation)[:200],
                            depends_on=",".join(tc["depends_on"]),
                            duration_ms=tc["duration_ms"],
                            success=True,
                        )

                input_chars = len(input_text) + len(str(result.get("intermediate_steps", [])))
                output_chars = len(result.get("output", ""))
                estimated_input_tokens = int(input_chars / 3.5)
                estimated_output_tokens = max(1, int(output_chars / 3.5))

                record_llm_call(
                    request_id=self.request_id,
                    agent_name=self.name,
                    input_tokens=estimated_input_tokens,
                    output_tokens=estimated_output_tokens,
                    duration_ms=elapsed_ms,
                    success=True,
                )

                return {
                    "agent": self.name,
                    "success": True,
                    "output": result.get("output", ""),
                    "tool_calls": tool_calls,
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens,
                    "duration_ms": elapsed_ms,
                }

            except Exception as e:
                last_error = e
                if attempt < LLM_MAX_RETRIES:
                    wait = (attempt + 1) * 2
                    await asyncio.sleep(wait)
                    continue

        # 所有重试都失败
        return {
            "agent": self.name,
            "success": False,
            "output": f"Agent 执行出错（已重试 {LLM_MAX_RETRIES} 次）: {str(last_error)}",
            "tool_calls": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "duration_ms": 0,
        }
