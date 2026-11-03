from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Interface dasar untuk AI provider."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Menghasilkan respons dari AI provider."""
        raise NotImplementedError
