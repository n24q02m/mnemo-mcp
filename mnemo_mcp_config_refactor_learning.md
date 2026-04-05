# Learning: Refactoring Complex Tool Functions in mnemo_mcp

## Context
In `src/mnemo_mcp/server.py`, several MCP tools (e.g., `memory`, `config`) are implemented as large functions with a `match action:` block. This pattern, while functional, can lead to high cognitive load and maintainability issues as the number of actions grows.

## Pattern: Tiered Dispatcher
The repository follows a tiered dispatcher pattern for complex tools:
1. **Tool Entry Point**: The `@mcp.tool` function handles documentation, context retrieval (`_get_ctx`), and parameter normalization (e.g., clamping `limit`).
2. **Dispatcher**: A `match action:` block routes the request to action-specific async handlers.
3. **Action Handlers**: Private async functions (e.g., `_handle_config_status`, `_handle_config_set`) implement the core logic for each action.

## Implementation Details
- **Lazy Imports**: Heavy dependencies or those only needed for specific actions should be imported inside the action handler (e.g., `from mnemo_mcp.sync import sync_full`).
- **Standardized Response**: All tool actions return a JSON string via the `_json()` helper.
- **Error Handling**: Handlers should return structured JSON errors instead of raising exceptions when possible, to provide graceful feedback to the MCP client.

## Example Refactoring
The `config` tool was refactored by extracting its `status`, `sync`, `set`, `warmup`, and `setup_sync` logic into `_handle_config_*` functions, significantly reducing the size of the main `config` function and aligning it with the pattern used for the `memory` tool.
