"""Synthetic-only tests for private MP4 integrity receipts."""
import json

from studio.family_private_media import receipt_path, write_receipt, verify_receipt


def test_private_movie_receipt_roundtrip_and_replacement(tmp_path):
    movie = tmp_path / "synthetic.mp4"
    movie.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"0" * 1024)
    movie.chmod(0o600)
    fingerprint = "a" * 64
    receipt = write_receipt(
        movie, owner="child_a", film_id="FILM_synthetic",
        revision="2", fingerprint=fingerprint,
    )
    assert receipt == receipt_path(movie)
    assert receipt.stat().st_mode & 0o077 == 0
    assert verify_receipt(
        movie, owner="child_a", film_id="FILM_synthetic",
        revision="2", fingerprint=fingerprint,
    )
    for owner, revision, digest in (
        ("child_b", "2", fingerprint),
        ("child_a", "1", fingerprint),
        ("child_a", "2", "b" * 64),
    ):
        assert not verify_receipt(
            movie, owner=owner, film_id="FILM_synthetic",
            revision=revision, fingerprint=digest,
        )
    movie.write_bytes(movie.read_bytes() + b"changed")
    assert not verify_receipt(
        movie, owner="child_a", film_id="FILM_synthetic",
        revision="2", fingerprint=fingerprint,
    )


def test_receipt_rejects_forged_fields_and_unsafe_permissions(tmp_path):
    movie = tmp_path / "synthetic.mp4"
    movie.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"0" * 1024)
    movie.chmod(0o600)
    fingerprint = "a" * 64
    receipt = write_receipt(
        movie, owner="child_a", film_id="FILM_synthetic",
        revision="1", fingerprint=fingerprint,
    )
    record = json.loads(receipt.read_text())
    record["public_url"] = "forbidden"
    receipt.write_text(json.dumps(record))
    assert not verify_receipt(
        movie, owner="child_a", film_id="FILM_synthetic",
        revision="1", fingerprint=fingerprint,
    )
    receipt.chmod(0o644)
    assert not verify_receipt(
        movie, owner="child_a", film_id="FILM_synthetic",
        revision="1", fingerprint=fingerprint,
    )
