from studio.providers.base import StructuredTextProvider


class OpenAIProvider(StructuredTextProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def generate_structured(self, *, system: str, user: str, schema):
        raise NotImplementedError("OpenAI adapter is intentionally stubbed in v0.3 Foundation.")
