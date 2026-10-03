from abc import ABC, abstractmethod
from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StructuredTextProvider(ABC):
    @abstractmethod
    def generate_structured(self, *, system: str, user: str, schema: Type[T]) -> T:
        """Generate a validated Pydantic object. Concrete OpenAI/Gemini providers come next."""
        raise NotImplementedError


class ImageGenerationProvider(ABC):
    """Provider-neutral binary image generation boundary."""

    @abstractmethod
    def generate(
        self,
        *,
        prompt: str,
        size: str = "1024x1536",
        quality: str = "medium",
    ) -> bytes:
        raise NotImplementedError



class ImageAnalysisProvider(ABC):
    """Provider-neutral image -> validated structured data boundary."""

    @abstractmethod
    def analyze_structured(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        schema: Type[T],
    ) -> T:
        raise NotImplementedError
