from backend.providers.base import ProviderAdapter
from backend.providers.gemini import GeminiAdapter
from backend.providers.openrouter import OpenRouterAdapter

# To add a vendor, implement ProviderAdapter and register it here.
PROVIDERS: dict[str, type[ProviderAdapter]] = {
    "openrouter": OpenRouterAdapter,
    "gemini": GeminiAdapter,
}
