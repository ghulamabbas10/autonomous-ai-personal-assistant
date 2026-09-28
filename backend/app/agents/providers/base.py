from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

MessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True)
class GenerationRequest:
    messages: Sequence[ChatMessage]
    temperature: float = 0.2
    max_output_tokens: int = 1_024


@dataclass(frozen=True)
class GenerationResult:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult: ...

    @abstractmethod
    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        if False:
            yield ""

    @abstractmethod
    async def generate_structured(
        self, request: GenerationRequest, schema: dict[str, Any]
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def close(self) -> None:
        return None


class ProviderError(RuntimeError):
    """A safe, provider-independent inference failure."""
