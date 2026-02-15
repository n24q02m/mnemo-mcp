## 2024-05-23 - Argument Injection in Rclone Configuration
**Vulnerability:** The `config` tool allowed setting `sync_remote` and `sync_folder` to arbitrary strings, enabling argument injection in the constructed `rclone` command (e.g. via `--config` flags) and potential path traversal via `..` in `sync_folder`.
**Learning:** Concatenating user input into command arguments (even when using `subprocess.run` with a list) can still be dangerous if the input starts with `-` (interpreted as flags) or contains traversal sequences.
**Prevention:** Always validate and sanitize user input that flows into external commands. Use allowlists (e.g. alphanumeric only) where possible.
