import sys

def update_test_token_store():
    path = "tests/test_token_store.py"
    with open(path, "r") as f:
        content = f.read()

    extra_test = """
    def test_load_token_exists_oserror(self, token_dir):
        from mnemo_mcp.token_store import load_token
        from pathlib import Path

        with patch.object(Path, "exists", side_effect=OSError("exists error")):
            with patch("mnemo_mcp.token_store.settings") as m:
                m.get_data_dir.return_value = token_dir.parent
                assert load_token("drive") is None
"""
    # Insert before TestSaveToken
    if "test_load_token_exists_oserror" not in content:
        content = content.replace("class TestSaveToken:", extra_test + "\n\nclass TestSaveToken:")
        with open(path, "w") as f:
            f.write(content)

def update_test_token_store_per_sub():
    path = "tests/test_token_store_per_sub.py"
    with open(path, "r") as f:
        content = f.read()

    extra_load_test = """
    def test_load_token_for_sub_exists_oserror(self, data_dir):
        from mnemo_mcp.token_store import load_token_for_sub
        from pathlib import Path

        with patch.object(Path, "exists", side_effect=OSError("exists error")):
            assert load_token_for_sub("user", "drive") is None
"""
    extra_save_test = """
    def test_save_token_for_sub_fallback_chmod_oserror(self, data_dir):
        if os.name == "nt":
            pytest.skip("POSIX-only branch")
        from mnemo_mcp.token_store import save_token_for_sub
        from pathlib import Path

        with patch("mnemo_mcp.token_store.os.open", side_effect=OSError("open fail")):
            with patch.object(Path, "chmod", side_effect=OSError("chmod fail")):
                # Should not raise
                save_token_for_sub("user", "drive", {"access_token": "ok"})
"""

    if "test_load_token_for_sub_exists_oserror" not in content:
        content = content.replace("class TestAsyncTokenForSub:", extra_load_test + "\n\nclass TestAsyncTokenForSub:")

    if "test_save_token_for_sub_fallback_chmod_oserror" not in content:
        # Find TestSaveTokenForSubFallback class and add it there
        if "class TestSaveTokenForSubFallback:" in content:
            content = content.replace("assert path.exists()", "assert path.exists()\n" + extra_save_test)
        else:
             content = content.replace("class TestLoadTokenForSub:", extra_save_test + "\n\nclass TestLoadTokenForSub:")

    with open(path, "w") as f:
        f.write(content)

update_test_token_store()
update_test_token_store_per_sub()
