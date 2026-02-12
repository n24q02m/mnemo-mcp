# Mnemo MCP Server

Persistent AI memory with hybrid search and embedded sync. Open, free, unlimited.

## Features

- **Hybrid search**: FTS5 full-text + sqlite-vec semantic (when embedding model available)
- **Zero dependency mode**: Works with SQLite FTS5 only — no API keys needed
- **Auto-detect embedding**: Set `API_KEYS` and the server picks the right model
- **Embedded sync**: rclone auto-downloaded and managed as subprocess
- **Multi-machine**: JSONL-based merge sync via rclone (Google Drive, S3, etc.)
- **Proactive memory**: Tool descriptions guide AI to save preferences, decisions, facts

## Install

```bash
# With uv (recommended)
uvx mnemo-mcp

# With pip
pip install mnemo-mcp
```

## Quick Start

### Minimal (FTS5 only, no API keys)

```json
{
  "mcpServers": {
    "mnemo": {
      "command": "uvx",
      "args": ["mnemo-mcp"]
    }
  }
}
```

### With embeddings (semantic search)

```json
{
  "mcpServers": {
    "mnemo": {
      "command": "uvx",
      "args": ["mnemo-mcp"],
      "env": {
        "API_KEYS": "GOOGLE_API_KEY:AIza..."
      }
    }
  }
}
```

### With sync (multi-machine)

```json
{
  "mcpServers": {
    "mnemo": {
      "command": "uvx",
      "args": ["mnemo-mcp"],
      "env": {
        "API_KEYS": "GOOGLE_API_KEY:AIza...",
        "SYNC_ENABLED": "true",
        "SYNC_REMOTE": "gdrive",
        "SYNC_INTERVAL": "300"
      }
    }
  }
}
```

Requires rclone remote configured: `rclone config create gdrive drive`

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `~/.mnemo-mcp/memories.db` | Database location |
| `API_KEYS` | — | API keys (`ENV:key,ENV:key`) |
| `EMBEDDING_MODEL` | auto-detect | LiteLLM model name |
| `EMBEDDING_DIMS` | auto-detect | Embedding dimensions |
| `SYNC_ENABLED` | `false` | Enable rclone sync |
| `SYNC_REMOTE` | — | rclone remote name |
| `SYNC_FOLDER` | `mnemo-mcp` | Remote folder |
| `SYNC_INTERVAL` | `0` | Auto-sync seconds (0=manual) |
| `LOG_LEVEL` | `INFO` | Log level |

### Supported Embedding Providers

| API Key | Auto-detected Model |
|---------|-------------------|
| `GOOGLE_API_KEY` | `gemini/text-embedding-004` |
| `OPENAI_API_KEY` | `text-embedding-3-small` |
| `MISTRAL_API_KEY` | `mistral/mistral-embed` |
| `COHERE_API_KEY` | `cohere/embed-english-v3.0` |
| `OLLAMA_API_BASE` | Set `EMBEDDING_MODEL` manually |

No API keys = FTS5-only mode (text search works perfectly, just no semantic similarity).

## MCP Tools

### `memory` — Core memory operations

| Action | Required | Optional |
|--------|----------|----------|
| `add` | `content` | `category`, `tags` |
| `search` | `query` | `category`, `tags`, `limit` |
| `list` | — | `category`, `limit` |
| `update` | `memory_id` | `content`, `category`, `tags` |
| `delete` | `memory_id` | — |
| `export` | — | — |
| `import` | `data` | `mode` (merge/replace) |
| `stats` | — | — |

### `config` — Server configuration

| Action | Required | Optional |
|--------|----------|----------|
| `status` | — | — |
| `sync` | — | — |
| `set` | `key`, `value` | — |

### `help` — Full documentation

```
help(topic="memory")  # or "config"
```

## Architecture

```
                  MCP Client (Claude, Cursor, etc.)
                         |
                    FastMCP Server
                   /      |       \
             memory    config    help
                |         |        |
            MemoryDB   Settings  docs/
            /     \
        FTS5    sqlite-vec
                    |
              LiteLLM embed
                    |
        Gemini / OpenAI / Ollama / ...

        Sync: rclone (embedded) → Google Drive / S3 / ...
```

## Development

```bash
# Install
uv sync

# Run
uv run mnemo-mcp

# Lint
uv run ruff check src/
uv run ty check src/

# Test
uv run pytest
```

## License

MIT
