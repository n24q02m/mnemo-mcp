# Memory Tool - Full Documentation

## Overview

The memory tools manage persistent AI memories with hybrid search (text + semantic).
Memories survive across sessions, projects, and machines (with sync enabled).

## Tools

## `add_memory` - Save a new memory

Save facts, preferences, decisions, code patterns, project context.

**Parameters:**
- `content` (required): The memory content to save
- `category` (optional): Organize by category (default: "general")
- `tags` (optional): List of tags for filtering

**Categories (recommended):**
- `preference` - User preferences, settings, workflow choices
- `decision` - Architecture decisions, trade-offs, rationale
- `fact` - Facts about the user, project, or environment
- `pattern` - Code patterns, idioms, conventions the user prefers
- `context` - Project context, goals, constraints
- `general` - Everything else

**Example:**
```json
{"content": "User prefers Polars over Pandas for DataFrames", "category": "preference", "tags": ["python", "dataframes"]}
```

## `search_memory`

Hybrid search combining full-text and semantic similarity.

**Parameters:**
- `query` (required): Search query
- `category` (optional): Filter by category
- `tags` (optional): Filter by tags (any match)
- `limit` (optional): Max results (default: 5)

**Search behavior:**
- FTS5 full-text search (always active, works offline)
- Semantic vector search (when embedding model is configured)
- Results scored by: text relevance + semantic similarity + recency + access frequency
- Access count is incremented for returned results

**Example:**
```json
{"query": "dataframe library preference"}
```

## `list_memories`

List memories with optional filtering, ordered by most recently updated.

**Parameters:**
- `category` (optional): Filter by category
- `limit` (optional): Max results (default: 5)

**Example:**
```json
{"category": "decision", "limit": 10}
```

## `update_memory`

Update content, category, or tags of a memory.

**Parameters:**
- `memory_id` (required): ID of the memory to update
- `content` (optional): New content
- `category` (optional): New category
- `tags` (optional): New tags

**Example:**
```json
{"memory_id": "abc123", "content": "Updated preference: Polars > Pandas > DuckDB"}
```

## `delete_memory`

**Parameters:**
- `memory_id` (required): ID of the memory to delete

**Example:**
```json
{"memory_id": "abc123"}
```

## `export_memories`

Returns all memories as a JSONL string for backup or migration.

**Parameters:** None

## `import_memories`

Import memories from JSONL string, list of objects, or single object.

**Parameters:**
- `data` (required): JSONL string, list of objects, or single object
- `mode` (optional): "merge" (skip existing, default) or "replace" (clear + import)

## `memory_stats`

Returns total count, categories breakdown, last update time, and sync status.

**Parameters:** None

## `restore_memory`

Restore a previously archived memory back to active status.

**Parameters:**
- `memory_id` (required): ID of the archived memory to restore

**Example:**
```json
{"memory_id": "abc123"}
```

## `list_archived_memories`

Browse memories that have been auto-archived (old + low importance).

**Parameters:**
- `limit` (optional): Max results (default: 5)

**Example:**
```json
{"limit": 10}
```

## `consolidate_memories`

Uses LLM to summarize multiple memories in a category into a single consolidated text.
Requires LLM access (proxy or SDK mode). Returns a summary for review — does not
automatically modify memories.

**Parameters:**
- `category` (required): Category to consolidate

**Example:**
```json
{"category": "decision"}
```

## Intelligence Features

### Knowledge Graph
When LLM is available (proxy or SDK mode), adding or updating a memory automatically:
- Extracts entities (person, project, tool, concept, org, location, event)
- Identifies relations (uses, works_on, related_to, depends_on, created_by, part_of)
- Links entities to memories for graph-boosted search results

### Importance Scoring
Each memory is scored 0.0-1.0 by an LLM based on its value for future recall.
Defaults to 0.5 when LLM is unavailable. Used by auto-archive to identify low-value memories.

### Duplicate Detection
Before adding a memory, the system checks for semantic duplicates:
- Above `DEDUP_THRESHOLD` (0.9): warns about near-duplicate
- Above `DEDUP_WARN_THRESHOLD` (0.7): warns about similar existing memory

### Auto-Archive
Memories older than `ARCHIVE_AFTER_DAYS` (90) with importance below
`ARCHIVE_IMPORTANCE_THRESHOLD` (0.3) are automatically archived. Use `restore` to recover them.

### Reranking
Search results are reranked using a cross-encoder model for improved precision.
Supports Jina AI and Cohere cloud rerankers, with local Qwen3 as fallback.

## Proactive Memory Guidelines

The AI SHOULD proactively save memories when it detects:
- User states a preference or choice
- A technical decision is made with rationale
- User corrects the AI (save the correction)
- Project-specific conventions are established
- Recurring patterns or workflows emerge
- Important facts about the environment are discovered

The AI SHOULD search memories:
- At the start of new conversations (recall context)
- When making recommendations (check past preferences)
- Before suggesting alternatives (check past decisions)
- When the user references something discussed before
