import sys
from pathlib import Path

path = Path("src/mnemo_mcp/sync.py")
content = path.read_text()

old_block = """        # Extract rclone binary from zip
        with zipfile.ZipFile(tmp_path, "r") as zf:
            # Find rclone binary in archive
            binary_name = f"rclone{ext}"
            for info in zf.infolist():
                if info.filename.endswith(binary_name) and not info.is_dir():
                    # Extract to temp, then move
                    with zf.open(info) as src:
                        target_path.write_bytes(src.read())
                    break
            else:
                logger.error("rclone binary not found in archive")
                return None"""

new_block = """        # Extract rclone binary from zip (in thread pool)
        binary_name = f"rclone{ext}"
        try:
            await asyncio.to_thread(_extract_rclone_zip, tmp_path, target_path, binary_name)
        except Exception as e:
            logger.error(f"Failed to extract rclone binary: {e}")
            return None"""

if old_block in content:
    new_content = content.replace(old_block, new_block)
    path.write_text(new_content)
    print("Successfully updated src/mnemo_mcp/sync.py")
else:
    print("Could not find code block to replace")
    sys.exit(1)
