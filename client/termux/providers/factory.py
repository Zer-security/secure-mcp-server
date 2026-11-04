from ..config import AI_PROVIDER, AI_MODEL, OPENROUTER_API_KEY
from .openrouter_provider import OpenRouterProvider
# tambahkan import provider lain di sini jika ada


def create_provider():
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY belum diset")
        
    if AI_PROVIDER == "openrouter":
        return OpenRouterProvider(
            api_key=OPENROUTER_API_KEY,
            model=AI_MODEL,
        )
    else:
        raise ValueError(f"Provider {AI_PROVIDER} tidak didukung")
