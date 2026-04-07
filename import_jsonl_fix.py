    def import_jsonl(self, data: str | list | dict, mode: str = "merge") -> dict:
        """Import memories from JSONL string.

        Args:
            data: JSONL string (one JSON object per line).
            mode: "merge" (skip existing) or "replace" (clear + import).

        Returns:
            Dict with import stats (imported, skipped, rejected).
        """
        if mode == "replace":
            self._conn.execute("DELETE FROM memories")
            if self._vec_enabled:
                self._conn.execute("DELETE FROM memories_vec")

        imported = 0
        skipped = 0
        rejected = 0

        if isinstance(data, list):
            lines = data
        elif isinstance(data, dict):
            lines = [data]
        elif isinstance(data, str):
            lines = []
            for line in data.strip().split("\n"):
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except Exception:
                        rejected += 1
        else:
            lines = []

        BATCH_SIZE = 900
        now = _now_iso()

        for i in range(0, len(lines), BATCH_SIZE):
            batch_items = lines[i : i + BATCH_SIZE]
            batch_imported, batch_skipped, batch_rejected = self._process_import_batch(
                batch_items, mode, now
            )
            imported += batch_imported
            skipped += batch_skipped
            rejected += batch_rejected

        self._conn.commit()
        if imported > 0:
            logger.info(f"[AUDIT] import count={imported} mode={mode}")
        return {"imported": imported, "skipped": skipped, "rejected": rejected}

    def _process_import_batch(
        self, batch_items: list[dict], mode: str, now: str
    ) -> tuple[int, int, int]:
        """Validate, format, and execute database insertion for a single batch."""
        imported = 0
        skipped = 0
        rejected = 0
        parsed_batch = []

        # Validate batch
        for mem in batch_items:
            try:
                memory_id = mem.get("id", uuid.uuid4().hex)
                content = mem.get("content", "")

                if len(content) > MAX_CONTENT_LENGTH:
                    logger.warning(
                        f"[AUDIT] import rejected id={memory_id} "
                        f"len={len(content)} exceeds {MAX_CONTENT_LENGTH}"
                    )
                    rejected += 1
                    continue

                parsed_batch.append((memory_id, mem, content))
            except Exception:
                rejected += 1
                continue

        if not parsed_batch:
            return imported, skipped, rejected

        to_insert = []
        for memory_id, mem, content in parsed_batch:
            tags = mem.get("tags", [])
            tags_json = json.dumps(tags) if isinstance(tags, list) else tags

            to_insert.append(
                (
                    memory_id,
                    content,
                    mem.get("category", "general"),
                    tags_json,
                    mem.get("source"),
                    mem.get("created_at", now),
                    mem.get("updated_at", now),
                    mem.get("access_count", 0),
                    mem.get("last_accessed", now),
                )
            )

        if to_insert:
            cursor = self._conn.cursor()
            if mode == "replace":
                cursor.executemany(
                    """INSERT OR REPLACE INTO memories
                       (id, content, category, tags, source,
                        created_at, updated_at, access_count, last_accessed)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    to_insert,
                )
                imported += len(to_insert)
            else:
                cursor.executemany(
                    """INSERT OR IGNORE INTO memories
                       (id, content, category, tags, source,
                        created_at, updated_at, access_count, last_accessed)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    to_insert,
                )
                inserted_batch = cursor.rowcount
                imported += inserted_batch
                skipped += len(to_insert) - inserted_batch

        return imported, skipped, rejected
