"""Regression tests for owner-only file writes."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest


def test_write_owner_only_creates_restricted_file(tmp_path: Path):
    from mnemo_mcp.secure_file import write_owner_only

    path = tmp_path / "secret.bin"
    write_owner_only(path, b"new-content")

    assert path.read_bytes() == b"new-content"
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == stat.S_IRUSR | stat.S_IWUSR


def test_fchmod_failure_does_not_truncate_existing_file(tmp_path: Path):
    from mnemo_mcp.secure_file import write_owner_only

    path = tmp_path / "secret.bin"
    path.write_bytes(b"previous-content")

    if os.name == "nt":
        pytest.skip("POSIX-only fchmod failure path")

    with patch("mnemo_mcp.secure_file.os.fchmod", side_effect=OSError("not supported")):
        with pytest.raises(OSError, match="not supported"):
            write_owner_only(path, b"replacement")

    assert path.read_bytes() == b"previous-content"


def test_replace_failure_preserves_existing_file(tmp_path: Path):
    from mnemo_mcp.secure_file import write_owner_only

    path = tmp_path / "secret.bin"
    path.write_bytes(b"previous-content")

    with (
        patch(
            "mnemo_mcp.secure_file.os.replace", side_effect=OSError("replace failed")
        ),
        pytest.raises(OSError, match="replace failed"),
    ):
        write_owner_only(path, b"replacement")

    assert path.read_bytes() == b"previous-content"
    assert not list(tmp_path.glob(".secret.bin.*"))


def test_reparse_target_is_not_modified(tmp_path: Path):
    from mnemo_mcp.secure_file import write_owner_only

    target = tmp_path / "target.bin"
    target.write_bytes(b"previous-content")
    link = tmp_path / "secret.bin"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(OSError):
        write_owner_only(link, b"replacement")

    assert target.read_bytes() == b"previous-content"


def test_windows_branch_applies_acl_without_posix_fchmod(tmp_path: Path):
    from mnemo_mcp.secure_file import write_owner_only

    path = tmp_path / "secret.bin"
    with (
        patch("mnemo_mcp.secure_file._IS_WINDOWS", True),
        patch("mnemo_mcp.secure_file._set_windows_owner_only") as mock_acl,
        patch("mnemo_mcp.secure_file.os.fchmod") as mock_fchmod,
    ):
        write_owner_only(path, b"windows-content")

    mock_fchmod.assert_not_called()
    assert mock_acl.call_count == 2
    assert path.read_bytes() == b"windows-content"


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL test")
def test_windows_file_acl_contains_only_current_user(tmp_path: Path):
    import win32api
    import win32security

    from mnemo_mcp.secure_file import write_owner_only

    path = tmp_path / "secret.bin"
    write_owner_only(path, b"windows-content")

    token = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(), win32security.TOKEN_QUERY
    )
    try:
        current_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[
            0
        ]
    finally:
        win32api.CloseHandle(token)

    security_descriptor = win32security.GetNamedSecurityInfo(
        str(path), win32security.SE_FILE_OBJECT, win32security.DACL_SECURITY_INFORMATION
    )
    dacl = security_descriptor.GetSecurityDescriptorDacl()
    assert dacl.GetAceCount() == 1
    assert win32security.ConvertSidToStringSid(dacl.GetAce(0)[2]) == (
        win32security.ConvertSidToStringSid(current_sid)
    )
