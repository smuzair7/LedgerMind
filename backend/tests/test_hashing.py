import tempfile
from pathlib import Path

from app.ingestion.hashing import chunk_hash, sha256_bytes, sha256_file


def test_sha256_bytes_known() -> None:
    assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_sha256_file_matches_bytes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x"
        p.write_bytes(b"hello world")
        assert sha256_file(p) == sha256_bytes(b"hello world")


def test_chunk_hash_deterministic() -> None:
    a = chunk_hash(doc_id="d1", page=1, text="abc")
    b = chunk_hash(doc_id="d1", page=1, text="abc")
    assert a == b
    assert a != chunk_hash(doc_id="d1", page=2, text="abc")
    assert a != chunk_hash(doc_id="d2", page=1, text="abc")
    assert a != chunk_hash(doc_id="d1", page=1, text="abc", table_id="t1")
