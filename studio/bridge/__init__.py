"""Mini Utopia local Bridge.

Godot Creator talks to Python Core through this package. The Bridge is a
transport boundary, not a second persistence layer.
"""

from studio.bridge.server import (
    BRIDGE_PROTOCOL_VERSION,
    BridgeApplication,
    build_server,
)

__all__ = [
    "BRIDGE_PROTOCOL_VERSION",
    "BridgeApplication",
    "build_server",
]
