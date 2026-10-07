from __future__ import annotations

import copy
import json
from pathlib import Path

from studio.bridge.server import BridgeApplication, build_server


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "godot" / "config" / "runtime" / "bridge_character_example.json"


class SmokeCharacterGateway:
    def __init__(self) -> None:
        self.character = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def list_characters(self) -> list[dict]:
        return [copy.deepcopy(self.character)]

    def get_character(self, character_id: str) -> dict | None:
        if character_id != self.character["character_id"]:
            return None
        return copy.deepcopy(self.character)

    def update_character(
        self,
        character_id: str,
        payload: dict,
    ) -> dict | None:
        if character_id != self.character["character_id"]:
            return None
        self.character["display_name"] = payload["display_name"]
        self.character["description"] = payload.get("description", "")
        self.character["profile"] = copy.deepcopy(payload["profile"])
        self.character["revision"] = "WRITE_SMOKE_R2"
        return copy.deepcopy(self.character)


if __name__ == "__main__":
    gateway = SmokeCharacterGateway()
    application = BridgeApplication(
        character_reader_factory=lambda: gateway
    )
    server = build_server(
        host="127.0.0.1",
        port=8765,
        application=application,
    )
    print("bridge_godot_write_smoke_server: READY", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
