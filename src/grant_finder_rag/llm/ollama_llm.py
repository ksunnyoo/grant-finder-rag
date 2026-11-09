"""Ollama 로컬 LLM."""
import httpx

from grant_finder_rag.contracts.errors import LLMError
from grant_finder_rag.llm.common import post_json, strip_think


class OllamaLLM:
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3:8b",
        timeout: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = client or httpx.Client(timeout=timeout)

    def generate(self, system: str, prompt: str) -> str:
        data = post_json(
            self.client,
            f"{self.base_url}/api/chat",
            self.name,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "think": False,
                "options": {"temperature": 0.2},
            },
        )
        try:
            return strip_think(data["message"]["content"])
        except (KeyError, TypeError) as error:
            raise LLMError("ollama 응답 형식이 올바르지 않습니다") from error
