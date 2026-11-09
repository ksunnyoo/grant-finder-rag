"""환경 설정(.env)에서 LLM 공급자 목록을 만든다."""
from collections.abc import Mapping

from grant_finder_rag.contracts.ports import LLMPort
from grant_finder_rag.llm.gemini_llm import GeminiLLM
from grant_finder_rag.llm.groq_llm import GroqLLM
from grant_finder_rag.llm.ollama_llm import OllamaLLM


def parse_order(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def build_providers(order: list[str], env: Mapping[str, str]) -> list[LLMPort]:
    providers: list[LLMPort] = []
    for name in order:
        if name == "ollama":
            providers.append(
                OllamaLLM(
                    base_url=env.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                    model=env.get("OLLAMA_LLM_MODEL", "qwen3:8b"),
                )
            )
        elif name == "gemini":
            if not env.get("GEMINI_API_KEY"):
                raise ValueError("GEMINI_API_KEY가 .env에 없습니다")
            providers.append(
                GeminiLLM(
                    env["GEMINI_API_KEY"], model=env.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
                )
            )
        elif name == "groq":
            if not env.get("GROQ_API_KEY"):
                raise ValueError("GROQ_API_KEY가 .env에 없습니다")
            providers.append(
                GroqLLM(env["GROQ_API_KEY"], model=env.get("GROQ_MODEL", "llama-3.3-70b-versatile"))
            )
        else:
            raise ValueError(f"알 수 없는 LLM 공급자: {name}")
    if not providers:
        raise ValueError("LLM_PROVIDER_ORDER가 비어 있습니다")
    return providers
