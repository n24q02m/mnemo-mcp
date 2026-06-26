import re

with open(".mcp-core/packages/core-py/tests/auth/test_credential_form.py", "r") as f:
    c = f.read()
    c = c.replace("include_username_field=True", "")
    with open(".mcp-core/packages/core-py/tests/auth/test_credential_form.py", "w") as out:
        out.write(c)

files_to_fix = [
    ".mcp-core/packages/core-py/tests/auth/test_jwks_endpoint.py",
    ".mcp-core/packages/core-py/tests/oauth/test_jwt_issuer.py",
    ".mcp-core/packages/core-py/tests/auth/test_local_oauth_app.py",
    ".mcp-core/packages/core-py/tests/transport/test_local_server.py",
    ".mcp-core/packages/core-py/tests/storage/test_per_plugin_store.py",
    ".mcp-core/packages/core-py/tests/storage/test_per_plugin_token_key.py",
]

for file in files_to_fix:
    try:
        with open(file, "r") as f:
            c = f.read()
            # test_local_oauth_app.py, test_local_server.py
            c = c.replace("stable_sub_enabled=stable_sub_enabled,", "")
            c = c.replace("stable_sub_enabled=enabled,", "")

            # test_jwks_endpoint.py, test_jwt_issuer.py
            c = re.sub(r",\s*credential_secret=[^,)]+", "", c)

            # test_per_plugin_store.py, test_per_plugin_token_key.py
            c = re.sub(r",\s*backend=mem", "", c)
            c = re.sub(r",\s*sub_key=[\"'][^\"']+[\"']", "", c)

            # test_jwt_issuer.py (mcp typing issue)
            if "test_jwt_issuer.py" in file:
                c = c.replace("build_local_app(\n            mcp,", "build_local_app(\n            mcp, # ty: ignore[arg-type]")

        with open(file, "w") as out:
            out.write(c)
    except FileNotFoundError:
        pass
