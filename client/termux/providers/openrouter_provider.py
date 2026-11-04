import httpx

from .base import AIProvider


class OpenRouterProvider(AIProvider):
    """Provider AI menggunakan OpenRouter."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY belum diset."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.url,
                headers=headers,
                json=payload,
            )

        if response.status_code == 429:
            raise RuntimeError(
                "OpenRouter rate limit tercapai. Silakan coba lagi nanti."
            )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]

    async def generate_with_tools(self, prompt: str, tools: list) -> dict:
        """Mengirim prompt dan schema tools ke OpenRouter."""
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY belum diset."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }
                for tool in tools
            ],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.url,
                headers=headers,
                json=payload,
            )

        if response.status_code == 429:
            raise RuntimeError(
                "OpenRouter rate limit tercapai. Silakan coba lagi nanti."
            )

        if response.status_code == 429:
            raise RuntimeError(
                "OpenRouter rate limit tercapai. Silakan coba lagi nanti."
            )

        response.raise_for_status()
        return response.json()

    async def generate_with_messages(self, messages: list) -> dict:
        """Mengirim rangkaian messages ke OpenRouter."""
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY belum diset."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()
        return response.json()
