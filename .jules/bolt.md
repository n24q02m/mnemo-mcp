
## 2024-03-22 - Avoid redundant list allocations in frequent utility functions
**Learning:** Functions like `_is_retryable` in `embedder.py` which are used frequently during API request retry mechanisms were instantiating a list of strings on every single call. This resulted in redundant list allocation and negatively impacted execution time over many iterations.
**Action:** Lift static data structures like pattern lists or configuration dictionaries out of the function body and define them as module-level constant tuples or frozensets. This reuses the same memory reference and provides a noticeable speedup (~15-20% for string matching operations).
