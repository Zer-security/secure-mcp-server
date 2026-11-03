from config import AI_PROVIDER, AI_MODEL, OPENROUTER_API_KEY
from providers.openrouter_provider import OpenRouterProvider


def create_provider():
    """Membuat instance AI provider sesuai konfigurasi."""

    if AI_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY belum diset."
            )

        return OpenRouterProvider(
            api_key=OPENROUTER_API_KEY,
            model=AI_MODEL,
        )

    raise ValueError(
        f"Provider tidak didukung: {AI_PROVIDER}"
    )
