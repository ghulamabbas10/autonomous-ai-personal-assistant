import hashlib
from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.agents.providers.base import GenerationRequest, GenerationResult, LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"

    def __init__(self, model: str = "mock-v1") -> None:
        self.model = model

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        user_message = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        content = self._reply(user_message)
        return GenerationResult(
            content=content,
            model=self.model,
            input_tokens=self._tokens(" ".join(message.content for message in request.messages)),
            output_tokens=self._tokens(content),
            metadata={"deterministic": True},
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        result = await self.generate(request)
        chunk_size = 24
        for offset in range(0, len(result.content), chunk_size):
            yield result.content[offset : offset + chunk_size]

    async def generate_structured(
        self, request: GenerationRequest, schema: dict[str, Any]
    ) -> dict[str, Any]:
        result = await self.generate(request)
        return {
            "response": result.content,
            "provider": self.name,
            "schema_title": schema.get("title"),
        }

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embedding(text) for text in texts]

    @staticmethod
    def _reply(message: str) -> str:
        normalized = message.strip()
        if not normalized:
            return "What would you like to work on?"
        return (
            f"I received your request: “{normalized}”\n\n"
            "The free mock provider is active, so this response is deterministic and no external "
            "AI service was called. Connect Ollama to get full local-model answers. Planning and "
            "autonomous execution will be added in Phase 6."
        )

    @staticmethod
    def _tokens(text: str) -> int:
        return max(1, (len(text) + 3) // 4)

    @staticmethod
    def _embedding(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [round((byte / 127.5) - 1, 6) for byte in digest]
