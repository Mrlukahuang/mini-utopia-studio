from pathlib import Path
from studio.storage.base import ObjectStorage


class LocalObjectStorage(ObjectStorage):
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        target = (self.root / relative_path).resolve()
        if self.root.resolve() not in target.parents and target != self.root.resolve():
            raise ValueError("Path escapes storage root")
        return target

    def put_bytes(self, relative_path: str, payload: bytes) -> str:
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return relative_path

    def exists(self, relative_path: str) -> bool:
        return self.resolve(relative_path).exists()

    def get_bytes(self, relative_path: str) -> bytes:
        return self.resolve(relative_path).read_bytes()
