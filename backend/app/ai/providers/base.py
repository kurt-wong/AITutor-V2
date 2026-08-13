from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        ...
