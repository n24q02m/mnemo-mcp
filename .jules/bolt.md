## 2025-03-25 - [Optimize knowledge graph traversal with CTE]
**Learning:** Replaced a python logic loop in `find_related_memory_ids` querying individual graph nodes from memory_entities and union relationships sequentially, which took max_depth * round trips. SQLite CTE allows handling recursive hierarchy completely in DB without crossing to python.
**Action:** Always favor CTE queries for variable deep iterative graph or tree fetches if performance starts dropping with increased branching.
