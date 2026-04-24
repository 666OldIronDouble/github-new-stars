import time
from abc import ABC, abstractmethod

import httpx

from config import (
    AI_BACKEND,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_MODEL,
)
from github_fetcher import RepoInfo

MAX_README_LEN = 3000
MAX_RETRIES = 3
RETRY_DELAY = 5

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


# ── 抽象后端 ──────────────────────────────────────────────


class SummarizerBackend(ABC):
    """AI 摘要后端的统一接口。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """后端显示名称。"""

    @abstractmethod
    def is_available(self) -> bool:
        """检测后端是否可用（静默，不抛异常）。"""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """调用 AI 生成摘要文本。失败时返回以"（"开头的错误提示。"""


# ── Ollama 后端 ──────────────────────────────────────────


class OllamaBackend(SummarizerBackend):
    @property
    def name(self) -> str:
        return f"Ollama/{OLLAMA_MODEL}"

    def is_available(self) -> bool:
        try:
            transport = httpx.HTTPTransport()
            mounts = {"http://": transport, "https://": transport}
            with httpx.Client(transport=transport, mounts=mounts, timeout=5) as client:
                resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str) -> str:
        transport = httpx.HTTPTransport()
        mounts = {"http://": transport, "https://": transport}

        for attempt in range(MAX_RETRIES):
            if attempt > 0 and not self.is_available():
                print(f"    Ollama 不可用，等待 {RETRY_DELAY}s 后重试...")
                time.sleep(RETRY_DELAY)
                if not self.is_available():
                    if attempt == MAX_RETRIES - 1:
                        return "（Ollama 服务不可用，摘要生成跳过）"
                    continue

            try:
                with httpx.Client(transport=transport, mounts=mounts, timeout=300) as client:
                    resp = client.post(
                        f"{OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": OLLAMA_MODEL,
                            "prompt": prompt,
                            "stream": False,
                            "think": False,
                            "options": {"num_predict": 512, "temperature": 0.7},
                        },
                    )
                    resp.raise_for_status()
                    return resp.json().get("response", "").strip()
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

        return "（Ollama 重试耗尽，摘要生成跳过）"


# ── Gemini 后端 ──────────────────────────────────────────


class GeminiBackend(SummarizerBackend):
    @property
    def name(self) -> str:
        return f"Gemini/{GEMINI_MODEL}"

    def is_available(self) -> bool:
        if not GEMINI_API_KEY:
            return False
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}",
                    params={"key": GEMINI_API_KEY},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 512,
            },
        }

        for attempt in range(MAX_RETRIES):
            try:
                with httpx.Client(timeout=120) as client:
                    resp = client.post(
                        url,
                        params={"key": GEMINI_API_KEY},
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                    return "（Gemini 未返回有效内容）"
            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                if attempt < MAX_RETRIES - 1:
                    print(f"    超时，第 {attempt + 2}/{MAX_RETRIES} 次重试...")
                    continue
                return "（Gemini 摘要生成超时）"
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    if attempt < MAX_RETRIES - 1:
                        wait = RETRY_DELAY * (attempt + 1)
                        print(f"    Gemini 速率限制，等待 {wait}s...")
                        time.sleep(wait)
                        continue
                    return "（Gemini API 速率限制）"
                return f"（Gemini API 错误: {e.response.status_code}）"
            except Exception as e:
                return f"（Gemini 摘要生成失败: {e}）"

        return "（Gemini 重试耗尽，摘要生成跳过）"


# ── OpenAI 兼容后端（硅基流动 / DeepSeek） ──────────────


class OpenAICompatBackend(SummarizerBackend):
    """支持所有 OpenAI 兼容 API（硅基流动、DeepSeek 等）。"""

    def __init__(self, api_key: str, base_url: str, model: str, display_name: str):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._display_name = display_name

    @property
    def name(self) -> str:
        return self._display_name

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.7,
        }

        for attempt in range(MAX_RETRIES):
            try:
                with httpx.Client(timeout=120) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return (
                            choices[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                        )
                    return f"（{self._display_name} 未返回有效内容）"
            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                if attempt < MAX_RETRIES - 1:
                    print(f"    超时，第 {attempt + 2}/{MAX_RETRIES} 次重试...")
                    continue
                return f"（{self._display_name} 摘要生成超时）"
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    if attempt < MAX_RETRIES - 1:
                        wait = RETRY_DELAY * (attempt + 1)
                        print(f"    速率限制，等待 {wait}s...")
                        time.sleep(wait)
                        continue
                    return f"（{self._display_name} API 速率限制）"
                return f"（{self._display_name} API 错误: {e.response.status_code}）"
            except Exception as e:
                return f"（{self._display_name} 摘要生成失败: {e}）"

        return f"（{self._display_name} 重试耗尽，摘要生成跳过）"


# ── 降级模式 ─────────────────────────────────────────────


class DegradedBackend(SummarizerBackend):
    """无可用 AI 后端时的降级模式：仅基于项目描述生成简要摘要。"""

    @property
    def name(self) -> str:
        return "降级模式（无 AI）"

    def is_available(self) -> bool:
        return True  # 降级模式始终可用

    def generate(self, prompt: str) -> str:
        # 从 prompt 中提取项目描述信息
        lines = prompt.strip().split("\n")
        desc = ""
        lang = ""
        for line in lines:
            if line.startswith("描述："):
                desc = line[3:].strip()
            elif line.startswith("语言："):
                lang = line[3:].strip()
        parts = []
        if desc:
            parts.append(f"项目简介：{desc}")
        if lang and lang != "N/A":
            parts.append(f"主要语言：{lang}")
        return " | ".join(parts) if parts else "（降级模式：请配置 AI 后端以生成详细摘要）"


# ── 后端工厂 ─────────────────────────────────────────────


def _build_candidates() -> list[SummarizerBackend]:
    """构建所有候选后端列表。"""
    candidates: list[SummarizerBackend] = [OllamaBackend()]
    if GEMINI_API_KEY:
        candidates.append(GeminiBackend())
    if SILICONFLOW_API_KEY:
        candidates.append(
            OpenAICompatBackend(
                api_key=SILICONFLOW_API_KEY,
                base_url=SILICONFLOW_BASE_URL,
                model=SILICONFLOW_MODEL,
                display_name=f"SiliconFlow/{SILICONFLOW_MODEL}",
            )
        )
    if DEEPSEEK_API_KEY:
        candidates.append(
            OpenAICompatBackend(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                model=DEEPSEEK_MODEL,
                display_name=f"DeepSeek/{DEEPSEEK_MODEL}",
            )
        )
    return candidates


_BACKEND_MAP = {
    "ollama": lambda: OllamaBackend(),
    "gemini": lambda: GeminiBackend(),
    "siliconflow": lambda: OpenAICompatBackend(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL,
        model=SILICONFLOW_MODEL,
        display_name=f"SiliconFlow/{SILICONFLOW_MODEL}",
    ),
    "deepseek": lambda: OpenAICompatBackend(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        display_name=f"DeepSeek/{DEEPSEEK_MODEL}",
    ),
}


def create_backend() -> SummarizerBackend:
    """根据 AI_BACKEND 配置创建后端实例。

    - 'auto': 自动检测可用后端，均不可用则降级
    - 具体名称: 使用指定后端，不可用则降级
    - 'none': 直接降级模式
    """
    if AI_BACKEND == "none":
        return DegradedBackend()

    if AI_BACKEND == "auto":
        candidates = _build_candidates()
        for backend in candidates:
            if backend.is_available():
                return backend
        print("  未检测到可用的 AI 后端，进入降级模式。")
        print("  提示：配置 Ollama/Gemini/SiliconFlow/DeepSeek 可生成详细摘要。")
        return DegradedBackend()

    # 指定后端
    factory = _BACKEND_MAP.get(AI_BACKEND)
    if factory:
        backend = factory()
        if backend.is_available():
            return backend
        print(f"  指定的后端 {AI_BACKEND} 不可用，进入降级模式。")
        return DegradedBackend()

    print(f"  未知后端: {AI_BACKEND}，进入降级模式。")
    return DegradedBackend()


# ── 对外接口 ─────────────────────────────────────────────


def generate_summary(repo: RepoInfo, readme: str, backend: SummarizerBackend) -> str:
    """使用指定后端生成项目摘要。"""
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
    return backend.generate(prompt)
