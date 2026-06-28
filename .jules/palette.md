## 2025-05-18 - Added context-aware `suggestion` to JSON error responses
**Learning:** In a backend/CLI-focused MCP server, traditional frontend UX paradigms translate to Developer/Agent Experience (DX). When the server returns raw errors without guidance, consumers (like LLMs or developers debugging tools) struggle to recover. Standardizing on a top-level `suggestion` key in JSON error responses makes the API significantly more actionable and "intuitive".
**Action:** When adding or refactoring error paths in server tool handlers (like `_handle_add`, `_handle_capture`, etc.), always ensure `_json({"error": ...})` includes a corresponding `"suggestion": "..."` field with concrete next steps.

## 2025-02-24 - Handle NoneType and Provide Fallback Suggestions
**Learning:** When using fuzzy matching (like `difflib.get_close_matches`) for error responses in MCP tools, `NoneType` inputs (e.g. missing action or topic) cause unhandled `TypeError` exceptions. Additionally, when no close match is found, simply omitting a suggestion leaves the user/LLM without clear guidance on what to do next.
**Action:** Always guard against `NoneType` inputs before calling fuzzy matching, and always provide a fallback suggestion dynamically constructed from the available valid options to ensure the API always guides the consumer to a valid state.
