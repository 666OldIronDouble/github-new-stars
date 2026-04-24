import os
from dotenv import load_dotenv

# 在 load_dotenv 之前修正 socks:// 为 socks5://，兼容 httpx 代理格式
for _key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    _val = os.environ.get(_key)
    if _val and _val.startswith("socks://"):
        os.environ[_key] = _val.replace("socks://", "socks5://", 1)

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TOP_N = int(os.getenv("TOP_N", "10"))
