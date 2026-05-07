import hashlib

from mnemo_mcp.credential_state import _sub_data_dir
from mnemo_mcp.token_store import _get_token_dir_for_sub


def test_credential_state_sub_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))

    # Malicious sub
    malicious_sub = "../../../outside"
    d = _sub_data_dir(malicious_sub)

    # Verification
    expected_hash = hashlib.sha256(malicious_sub.encode("utf-8")).hexdigest()
    assert d == tmp_path / "subs" / expected_hash
    assert "outside" not in str(d)
    assert ".." not in str(d)
    # Check it is truly under the expected base
    assert str(d).startswith(str(tmp_path / "subs"))


def test_token_store_sub_path_traversal(tmp_path, monkeypatch):
    from mnemo_mcp.config import settings

    monkeypatch.setattr(settings, "get_data_dir", lambda: tmp_path)

    # Malicious sub
    malicious_sub = "../../../outside"
    d = _get_token_dir_for_sub(malicious_sub)

    # Verification
    expected_hash = hashlib.sha256(malicious_sub.encode("utf-8")).hexdigest()
    assert d == tmp_path / "subs" / expected_hash / "tokens"
    assert "outside" not in str(d)
    assert ".." not in str(d)
    assert str(d).startswith(str(tmp_path / "subs"))
