from studio.plugins.base import PluginRegistry
from studio.plugins.mock.creative import MockCharacterParsePlugin, MockTurnaroundPlugin


def test_plugin_registry_is_capability_based():
    registry = PluginRegistry()
    registry.register(MockCharacterParsePlugin())
    registry.register(MockTurnaroundPlugin())
    assert registry.get("character.parse").provider == "mock"
    assert "character.turnaround" in registry.list_capabilities()
