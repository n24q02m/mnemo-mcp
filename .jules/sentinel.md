## 2024-05-18 - Hardcoded Google Drive Client Secret
**Vulnerability:** A hardcoded Google Drive Client Secret (`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`) was found in `src/mnemo_mcp/config.py` as a default value for the Pydantic `Settings` class.
**Learning:** Hardcoding secrets as default values in configuration classes exposes them in the repository history and makes them available to anyone with read access to the code.
**Prevention:** Always default sensitive fields in configuration classes (like Pydantic `BaseSettings`) to empty strings (`""`) or `None`, and rely on environment variables or secure configuration files to populate them at runtime.
