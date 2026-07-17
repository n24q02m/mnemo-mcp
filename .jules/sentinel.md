## 2026-07-13 - Secure file write permissions
**Vulnerability:** Files written with sensitive data (like passports and token files) used `path.write_text()` without explicit permission restrictions, relying entirely on the umask. This exposes sensitive data to other local users.
**Learning:** Default file creation is not secure enough for secrets on shared systems.
**Prevention:** Use `os.open` with `os.O_CREAT | os.O_WRONLY | os.O_TRUNC` and explicit `0600` permissions via `os.fchmod`.
