"""系统配置"""
import os

# DeepSeek API 配置（OpenAI 兼容接口）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# AgentScope 配置
AGENTSCOPE_PROJECT = "grain-warehouse"

# 粮库配置
SILO_COUNT = 12  # 仓房数量

# LLM 温度
LLM_TEMPERATURE = 0.3
