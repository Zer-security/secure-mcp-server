import pytest

from client.termux import config
from client.termux.providers.factory import create_provider


def test_config_defaults():
    assert config.AI_PROVIDER == "openrouter"
    assert config.AI_MODEL == "openrouter/free"


def test_factory_requires_api_key(monkeypatch):
    monkeypatch.setattr("client.termux.providers.factory.OPENROUTER_API_KEY", None)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY belum diset"):
        create_provider()


def test_openrouter_429_error(monkeypatch):
    import httpx
    from client.termux.providers.openrouter_provider import OpenRouterProvider

    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(
            429,
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = OpenRouterProvider(
        api_key="test-key",
        model="openrouter/free",
    )

    with pytest.raises(RuntimeError, match="OpenRouter rate limit tercapai"):
        import asyncio
        asyncio.run(provider.generate("test"))
