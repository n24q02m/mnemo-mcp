import zipfile

import pytest

from mnemo_mcp.sync import _extract_rclone_zip


def test_extract_rclone_zip_success(tmp_path):
    """Test successful extraction of a file from a zip archive."""
    # Create a dummy zip file
    zip_path = tmp_path / "test.zip"
    target_path = tmp_path / "extracted_file"
    binary_name = "rclone"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("rclone", b"dummy content")
        zf.writestr("other_file", b"other content")

    # extract
    _extract_rclone_zip(zip_path, target_path, binary_name)

    assert target_path.exists()
    assert target_path.read_bytes() == b"dummy content"

def test_extract_rclone_zip_nested(tmp_path):
    """Test extraction when file is nested in a folder inside the zip."""
    zip_path = tmp_path / "test_nested.zip"
    target_path = tmp_path / "extracted_nested"
    binary_name = "rclone.exe"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("folder/rclone.exe", b"windows content")

    _extract_rclone_zip(zip_path, target_path, binary_name)

    assert target_path.exists()
    assert target_path.read_bytes() == b"windows content"

def test_extract_rclone_zip_not_found(tmp_path):
    """Test FileNotFoundError when binary is missing."""
    zip_path = tmp_path / "test_missing.zip"
    target_path = tmp_path / "should_not_exist"
    binary_name = "rclone"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("other_file", b"content")

    with pytest.raises(FileNotFoundError, match="Binary 'rclone' not found"):
        _extract_rclone_zip(zip_path, target_path, binary_name)

    assert not target_path.exists()

def test_extract_rclone_zip_is_dir(tmp_path):
    """Test that directories matching the name are ignored."""
    zip_path = tmp_path / "test_dir.zip"
    target_path = tmp_path / "should_not_exist"
    binary_name = "rclone"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # ZipInfo for a directory
        info = zipfile.ZipInfo("rclone/")
        zf.writestr(info, b"")

    with pytest.raises(FileNotFoundError):
        _extract_rclone_zip(zip_path, target_path, binary_name)
