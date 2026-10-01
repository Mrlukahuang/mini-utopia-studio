from studio.storage.local import LocalObjectStorage


def test_local_storage_roundtrip(tmp_path):
    storage = LocalObjectStorage(tmp_path)
    key = storage.put_bytes("assets/test/hello.txt", b"hello")
    assert storage.exists(key)
    assert storage.resolve(key).read_bytes() == b"hello"
