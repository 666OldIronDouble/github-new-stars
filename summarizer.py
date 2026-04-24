import time

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from github_fetcher import RepoInfo

MAX_README_LEN = 3000
MAX_RETRIES = 3
RETRY_DELAY = 5  # 重试等待秒数

# Ollama 是本地服务，不走代理；使用 mounts 显式绕过系统代理
_OLLAMA_TRANSPORT = httpx.HTTPTransport()
_OLLAMA_MOUNTS = {
    "http://": _OLLAMA_TRANSPORT,
    "https://": _OLLAMA_TRANSPORT,
}

PROMPT_TEMPLATE = """请用中文对以下 GitHub 项目生成摘要，包含：
1. 项目用途（一句话）
2. 核心功能（2-3个要点）
3. 技术栈/依赖
4. 适合哪类开发者使用

项目：{name}
Star数：{stars}
语言：{language}
描述：{description}

README内容：
{readme}"""


def _ollama_client(**kwargs) -> httpx.Client:
    """创建绕过代理的 Ollama HTTP 客户端。"""
    return httpx.Client(transport=_OLLAMA_TRANSPORT, mounts=_OLLAMA_MOUNTS, **kwargs)


def check_ollama_available() -> None:
    """检查 Ollama 服务是否可用，不可用则抛出异常。"""
    try:
        with _ollama_client(timeout=10) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Ollama 服务响应异常 (HTTP {resp.status_code})，请确认 Ollama 是否正常运行。"
                )
    except httpx.ConnectError:
        raise RuntimeError(
            "无法连接到 Ollama 服务，请确认 Ollama 已启动 "
            f"(地址: {OLLAMA_BASE_URL})。"
        )


def _ollama_is_available() -> bool:
    """静默检查 Ollama 是否可用。"""
    try:
        with _ollama_client(timeout=5) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def generate_summary(repo: RepoInfo, readme: str) -> str:
    """调用 Ollama 生成项目摘要，失败时重试最多 MAX_RETRIES 次。"""
    if not readme:
        return "（该项目无 README 文件，无法生成摘要）"

    truncated_readme = readme[:MAX_README_LEN]
    prompt = PROMPT_TEMPLATE.format(
        name=repo.name,
        stars=repo.stars,
        language=repo.language,
        description=repo.description,
        readme=truncated_readme,
    )

    for attempt in range(MAX_RETRIES):
        # 每次重试前检测 Ollama 可用性
        if attempt > 0 and not _ollama_is_available():
            print(f"    Ollama 不可用，等待 {RETRY_DELAY}s 后重试...")
            time.sleep(RETRY_DELAY)
            if not _ollama_is_available():
                if attempt == MAX_RETRIES - 1:
                    return "（Ollama 服务不可用，摘要生成跳过）"
                continue

        try:
            with _ollama_client(timeout=300) as client:
                resp = client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "think": False,  # 禁用思考模式，避免 thinking 占满输出
                        "options": {
                            "num_predict": 512,
                            "temperature": 0.7,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "").strip()
        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            if attempt < MAX_RETRIES - 1:
                print(f"    超时，第 {attempt + 2}/{MAX_RETRIES} 次重试...")
                continue
            return "（摘要生成超时）"
        except (httpx.ConnectError, httpx.RemoteProtocolError):
            if attempt < MAX_RETRIES - 1:
                print(f"    连接中断，第 {attempt + 2}/{MAX_RETRIES} 次重试...")
                time.sleep(RETRY_DELAY)
                continue
            return "（Ollama 连接中断，摘要生成失败）"
        except Exception as e:
            return f"（摘要生成失败: {e}）"
