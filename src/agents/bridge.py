"""AgentScope ↔ LangChain 桥接"""
from agentscope.agent import AgentBase
from agentscope.message import Msg
from src.agents.base_agent import BaseGrainAgent


class LangChainBridgeAgent(AgentBase):
    """将 LangChain AgentExecutor 包装为 AgentScope Agent

    实现 AgentScope 的 AgentBase 接口，内部调用 LangChain Agent。
    """

    def __init__(self, name: str, langchain_agent: BaseGrainAgent, **kwargs):
        super().__init__(name=name, **kwargs)
        self._langchain_agent = langchain_agent

    def reply(self, x: dict = None) -> dict:
        """AgentScope 消息接口 (同步)"""
        import asyncio
        return asyncio.run(self._async_reply(x))

    async def _async_reply(self, x: dict = None) -> dict:
        if x is None:
            content = ""
        elif isinstance(x, dict):
            content = x.get("content", str(x))
        else:
            content = str(x)

        context = x.get("context", {}) if isinstance(x, dict) else {}

        result = await self._langchain_agent.run(content, context)
        return Msg(
            name=self.name,
            content=result["output"],
            role="assistant",
            metadata={
                "tool_calls": result.get("tool_calls", []),
                "agent": self.name,
            }
        ).to_dict()
