from abc import ABC, abstractmethod
from pathlib import Path


class ObjectStorage(ABC):
    @abstractmethod
    def put_bytes(self, relative_path: str, payload: bytes) -> str: ...
    @abstractmethod
    def exists(self, relative_path: str) -> bool: ...
    @abstractmethod
    def resolve(self, relative_path: str) -> Path: ...
