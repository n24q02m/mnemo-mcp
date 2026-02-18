## 2024-04-12 - [Rclone Config Input Validation]
**Vulnerability:** User-controlled configuration parameters (`sync_remote`, `sync_folder`) were passed directly to `rclone` subprocess commands, creating potential for command injection and path traversal.
**Learning:** External tool integrations like `rclone` often rely on strict input formats that are not enforced by standard type systems (str).
**Prevention:** Use strict regex validation for all configuration inputs that are passed to subprocesses, and enforce relative paths to prevent traversal.
