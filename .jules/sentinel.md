## 2025-03-09 - Protect against malformed JSON in `json_each` DoS
**Vulnerability:** Unvalidated JSON strings inserted into SQLite columns queried with `json_each()` will cause a query-crashing exception (`malformed JSON`), creating a potential Denial-of-Service vulnerability.
**Learning:** `json_each` raises exceptions when passed malformed JSON. This is an issue when filtering is done directly via SQL queries.
**Prevention:** Guard `json_each()` calls with `json_valid()` (e.g., `json_valid(column) AND EXISTS(SELECT 1 FROM json_each(column)...)`).

## 2026-03-11 - Fix Logging Disruption via Invalid Configuration
**Vulnerability:** In `mnemo_mcp/server.py`'s `main` function, the `log_level` value from settings was being used to configure the `loguru` logger directly via `logger.add(..., level=settings.log_level)`. An invalid log level string (e.g. "INVALID_LEVEL") provided by environment variables or configuration files would cause `logger.add()` to raise a `ValueError: Level '...' does not exist`, disrupting logging entirely or crashing the process.
**Learning:** Always validate externally sourced configuration values against a known whitelist before passing them to internal library functions, especially for critical infrastructure like logging where a crash can lead to silent failures or denial of service.
**Prevention:** Ensured the log level is mapped to uppercase and checked against the set `{"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}`. If it's invalid, it now safely defaults to `"INFO"`. Added a regression test mocking invalid settings to ensure `logger.add` handles it correctly.
