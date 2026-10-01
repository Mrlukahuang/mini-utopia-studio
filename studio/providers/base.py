from abc import ABC, abstractmethod
from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StructuredTextProvider(ABC):
    @abstractmethod
    def generate_structured(self, *, system: str, user: str, schema: Type[T]) -> T:
        """Generate a validated Pydantic object. Concrete OpenAI/Gemini providers come next."""
        raise NotImplementedError
