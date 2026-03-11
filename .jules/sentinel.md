## 2025-03-09 - Protect against malformed JSON in `json_each` DoS
**Vulnerability:** Unvalidated JSON strings inserted into SQLite columns queried with `json_each()` will cause a query-crashing exception (`malformed JSON`), creating a potential Denial-of-Service vulnerability.
**Learning:** `json_each` raises exceptions when passed malformed JSON. This is an issue when filtering is done directly via SQL queries.
**Prevention:** Guard `json_each()` calls with `json_valid()` (e.g., `json_valid(column) AND EXISTS(SELECT 1 FROM json_each(column)...)`).

## 2026-03-10 - Logging Disruption via Invalid Configuration
**Vulnerability:** Unvalidated inputs used in logger configuration can cause the application logger to crash or stop functioning, leading to loss of audit trails or application failure.
**Learning:** External or user-provided configuration values must be strictly validated against an allowlist before being applied to internal state or components like the logging system.
**Prevention:** Validate log levels against a predefined set of valid string values (e.g., TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL) before updating the logger configuration.
