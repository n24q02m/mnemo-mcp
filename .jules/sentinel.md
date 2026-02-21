## 2026-02-21 - Missing Integrity Check on Binary Download
**Vulnerability:** The application downloaded the `rclone` binary from GitHub Releases without verifying its integrity (SHA256 checksum).
**Learning:** Even when downloading from trusted sources like GitHub Releases, a lack of integrity check leaves users vulnerable to MITM attacks or compromised releases.
**Prevention:** Always fetch the `SHA256SUMS` (or equivalent) file from the release, verify its signature if possible (or at least trust the HTTPS channel for it as a baseline), and compute the hash of the downloaded artifact before execution.
