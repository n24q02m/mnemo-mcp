"""Secure local-file persistence primitives."""

from __future__ import annotations

import errno
import os
import stat
import tempfile
from pathlib import Path

_IS_WINDOWS = os.name == "nt"
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_OWNER_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR
_OWNER_DIRECTORY_MODE = stat.S_IRWXU


def _is_reparse_point(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return False

    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT
    )


def _reject_reparse_path(path: Path) -> None:
    """Reject symlink/reparse components before touching a private path."""
    for candidate in (path, *path.parents):
        if _is_reparse_point(candidate):
            raise OSError(
                errno.ELOOP,
                f"Refusing to use a symlink or reparse point: {candidate}",
            )


def _set_windows_owner_only(  # pragma: no cover - chỉ chạy trên Windows, CI kiểm chứng
    path: Path, *, directory: bool
) -> None:
    """Replace inherited Windows ACLs with a DACL for the current user."""
    try:
        import win32api
        import win32con
        import win32security
    except ImportError as exc:  # pragma: no cover - only reachable on Windows
        raise RuntimeError(
            "Windows owner-only file persistence requires pywin32"
        ) from exc

    token = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(), win32security.TOKEN_QUERY
    )
    try:
        user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    finally:
        win32api.CloseHandle(token)

    inheritance = 0
    if directory:
        inheritance = (
            win32security.OBJECT_INHERIT_ACE | win32security.CONTAINER_INHERIT_ACE
        )

    dacl = win32security.ACL()
    dacl.AddAccessAllowedAceEx(
        win32security.ACL_REVISION,
        inheritance,
        win32con.GENERIC_ALL,
        user_sid,
    )

    security_info = (
        win32security.DACL_SECURITY_INFORMATION
        | win32security.PROTECTED_DACL_SECURITY_INFORMATION
    )
    try:
        win32security.SetNamedSecurityInfo(
            str(path),
            win32security.SE_FILE_OBJECT,
            security_info,
            None,
            None,
            dacl,
            None,
        )
    except Exception as exc:
        raise OSError(f"Unable to apply owner-only ACL to {path}") from exc


def ensure_owner_only_directory(path: str | os.PathLike[str]) -> Path:
    """Create a private directory and fail if its permissions cannot be set."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    _reject_reparse_path(directory)

    if _IS_WINDOWS:  # pragma: no cover - nhánh Windows được CI kiểm chứng
        _set_windows_owner_only(directory, directory=True)
    else:
        directory.chmod(_OWNER_DIRECTORY_MODE)
    return directory


def write_owner_only(path: str | os.PathLike[str], content: bytes) -> None:
    """Atomically write bytes to a private owner-only file.

    The temporary file is secured before any content is written. The target is
    replaced only after the complete payload is flushed, so write or permission
    failures leave an existing credential/configuration file intact.
    """
    file_path = Path(path)
    ensure_owner_only_directory(file_path.parent)
    _reject_reparse_path(file_path)

    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{file_path.name}.", dir=file_path.parent
    )
    temp_path = Path(temp_name)
    try:
        if _IS_WINDOWS:  # pragma: no cover - nhánh Windows được CI kiểm chứng
            _set_windows_owner_only(temp_path, directory=False)
        else:
            os.fchmod(temp_fd, _OWNER_FILE_MODE)

        with os.fdopen(temp_fd, "wb") as stream:
            temp_fd = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        # os.replace() replaces a symlink itself rather than following it, but
        # reject a pre-existing reparse target so callers never accept one.
        _reject_reparse_path(file_path)
        os.replace(temp_path, file_path)
    finally:
        if temp_fd >= 0:
            os.close(temp_fd)
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
