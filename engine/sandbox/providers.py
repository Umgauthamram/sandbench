"""Registry of pre-configured OpenAI-compatible model providers."""

PROVIDERS = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
    },
    "gemini": {
        "label": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "huggingface": {
        "label": "Hugging Face",
        "base_url": "https://router.huggingface.co/v1",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "base_url": "",
    },
}


def get_base_url(provider_id: str) -> str | None:
    """Return default base URL for the given provider, or None if unknown."""
    if provider_id in PROVIDERS:
        return PROVIDERS[provider_id]["base_url"]
    return None
