from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class Plugin(ABC):
    capability: str
    provider: str = "unknown"

    @abstractmethod
    def execute(self, **kwargs) -> Any: ...


class PluginRegistry:
    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.capability] = plugin

    def get(self, capability: str) -> Plugin:
        if capability not in self._plugins:
            raise KeyError(f"No plugin registered for capability: {capability}")
        return self._plugins[capability]

    def list_capabilities(self) -> list[str]:
        return sorted(self._plugins)
