## 2025-05-15 - Hardening SQLite Table Creation and Updates
**Learning:** Dynamically constructing SQL statements with f-strings, even for internal parameters like table dimensions or column names, is a potential injection vector if those parameters ever become user-controlled.
**Action:** Implemented strict bounds validation for vector dimensions and allowlist validation for dynamic update columns.
