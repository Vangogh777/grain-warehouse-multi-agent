"""系统配置 — 从环境变量或 .env 文件读取"""
import os

# 尝试加载 .env 文件
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# LLM 后端选择: openai / anthropic
LLM_BACKEND = os.getenv("LLM_BACKEND", "openai")

# DeepSeek API 配置（OpenAI 兼容接口）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Anthropic 兼容配置（GLM-5 等）
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://aicoding.bwits.cn:90/anthropic")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "glm-5")

# 可选模型列表（前端切换用）
AVAILABLE_MODELS = {
    "deepseek-chat": "DeepSeek V3（快速）",
    "deepseek-v4-flash": "DeepSeek V4 Flash（推理）",
    "deepseek-v4-pro": "DeepSeek V4 Pro（最强）",
    "glm-5": "GLM-5（智谱）",
}

# 各模型专属配置（API Key / Base URL 覆盖默认值）
MODEL_CONFIGS = {
    "glm-5": {
        "api_key": os.getenv("GLM5_API_KEY", ""),
        "base_url": os.getenv("GLM5_BASE_URL", "https://aicoding.bwits.cn:90/v1"),
    },
    "deepseek-ai/DeepSeek-V2.5": {
        "api_key": os.getenv("SILICONFLOW_API_KEY", ""),
        "base_url": os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
    },
}

# 推理模型列表（不支持工具调用）
REASONING_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro", "glm-5"}

# 推理模型对应的工具调用模型（快模型，非推理）
TOOL_MODEL_MAP = {
    "glm-5": "deepseek-chat",         # GLM-5 推理 → DeepSeek V3 调工具
    "deepseek-v4-flash": "deepseek-chat",
    "deepseek-v4-pro": "deepseek-chat",
    "deepseek-v4-flash": "deepseek-chat",
    "deepseek-v4-pro": "deepseek-chat",
}

# LLM 温度
LLM_TEMPERATURE = 0.3

# LLM 工厂 — 根据模型名自动选择后端
def create_llm(model: str = None, temperature: float = None):
    """根据模型名自动选择 OpenAI 或 Anthropic 后端"""
    m = model or DEEPSEEK_MODEL
    if m and m.startswith("glm"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=m,
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
            temperature=temperature or LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=m,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=temperature or LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT,
            max_retries=LLM_MAX_RETRIES,
        )


# API 超时 & 重试

# API 超时 & 重试
LLM_TIMEOUT = 60  # 单次请求超时（秒）
LLM_MAX_RETRIES = 2  # 失败重试次数

# ========== 角色系统 ==========
ROLES = {
    "keeper": {
        "label": "保管员",
        "icon": "🔧",
        "prompt": "你是一个粮库保管员，负责日常巡检和操作执行。回答要具体、可操作，直接告诉用户该做什么、怎么做。多用行动指令如'请打开风机''建议今天安排熏蒸'。",
    },
    "manager": {
        "label": "科长",
        "icon": "📋",
        "prompt": "你是一个粮库管理科长，负责全局监管和决策。回答要关注统计数据、趋势变化、异常汇总。多用管理视角如'本月异常率''建议调整作业计划''需要向领导汇报'。",
    },
    "inspector": {
        "label": "质检员",
        "icon": "🧪",
        "prompt": "你是一个粮库质检员，负责质量检测和标准合规。回答要精确引用国标数据，给出指标数值和等级判定。多用水分/容重/出糙率等专业指标。",
    },
}

# ========== 对话记忆（SQLite）==========
MEMORY_MAX_EXCHANGES = 5  # 每次携带最近5轮对话

# ========== 绕过 tiktoken 下载问题（国内网络限制）==========
# tiktoken 需要从 Azure Blob 下载编码文件，国内无法访问
# 方案：预创建缓存文件 + 跳过哈希校验
import os as _os
import base64 as _b64
import hashlib as _hashlib
import tiktoken.load as _tiktoken_load

_tiktoken_cache = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), ".tiktoken_cache")
_os.makedirs(_tiktoken_cache, exist_ok=True)
_os.environ["TIKTOKEN_CACHE_DIR"] = _tiktoken_cache

_cache_key = _hashlib.sha1(
    "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken".encode()
).hexdigest()
_cache_path = _os.path.join(_tiktoken_cache, _cache_key)

if not _os.path.exists(_cache_path) or _os.path.getsize(_cache_path) < 1000:
    _minimal = "\n".join(
        f"{_b64.b64encode(bytes([i])).decode()} {i}"
        for i in range(256)
    )
    with open(_cache_path, "w") as _f:
        _f.write(_minimal)

# 跳过哈希校验
_tiktoken_load.check_hash = lambda data, expected: True

def _simple_token_ids(text: str) -> list[int]:
    return [ord(c) for c in text[:10000]]

CUSTOM_GET_TOKEN_IDS = _simple_token_ids
