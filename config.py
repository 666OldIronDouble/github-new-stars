import os
from dotenv import load_dotenv

# 在 load_dotenv 之前修正 socks:// 为 socks5://，兼容 httpx 代理格式
for _key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    _val = os.environ.get(_key)
    if _val and _val.startswith("socks://"):
        os.environ[_key] = _val.replace("socks://", "socks5://", 1)

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
TOP_N = int(os.getenv("TOP_N", "10"))

# AI 后端选择: auto | ollama | gemini | siliconflow | deepseek | none
AI_BACKEND = os.getenv("AI_BACKEND", "auto")

# Ollama 配置
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Google Gemini 配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# 硅基流动配置 (OpenAI 兼容 API)
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv(
    "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
)
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen3-8B")

# DeepSeek 配置 (OpenAI 兼容 API)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
