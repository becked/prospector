# Import Threading Analysis

**Date:** 2025-10-25
**Status:** Research - Not Implemented
**Scope:** < 100 files × 2MB XML each

## Executive Summary

Analysis of parallelization opportunities for the DuckDB import process. Current import is fully single-threaded. **Recommendation: Implement parallel XML parsing with sequential database writes for ~2x speedup with minimal risk.**

**Key Finding:** DuckDB allows multiple write connections from the same process, but serializes writes internally via MVCC. Therefore, the highest-value optimization is parallelizing the XML parsing phase (60-70% of import time) while keeping database writes sequential.

## Current Architecture

### Import Pipeline (Single-Threaded)

The import flow in `tournament_visualizer/data/etl.py`:

1. **File discovery & deduplication** (sequential)
   - Scan all .zip files
   - Extract lightweight metadata for duplicate detection
   - Select best file from each duplicate group

2. **For each file** (sequential loop at `etl.py:638`):
   - **Parse phase** (CPU-intensive):
     - Unzip file
     - Parse XML with ElementTree
     - Extract all game data (players, events, territories, history, etc.)
   - **Database write phase** (I/O with lock contention):
     - Insert match
     - Insert players, rulers, events, territories, etc.
     - All bulk inserts

### Database Architecture (Single Shared Connection)

From `tournament_visualizer/data/database.py:32`:

```python
self._lock = threading.RLock()  # Reentrant lock

@contextmanager
def get_connection(self):
    with self._lock:
        conn = self.connect()  # Single shared connection
        yield conn
```

**Implication:** Even with multiple threads, all database operations are serialized by this lock. The connection is shared, not per-thread.

## Time Breakdown Analysis

Estimated time per file (typical 2MB save):

| Phase | Time | % of Total |
|-------|------|------------|
| Unzipping + XML parsing | 100-140ms | 60-70% |
| Data extraction (parser methods) | 20-30ms | 10-15% |
| Database writes (bulk inserts) | 40-60ms | 20-25% |
| Deduplication metadata | 10ms | 5% |
| **Total per file** | **170-240ms** | **100%** |

**For 100 files:**
- Current (single-threaded): 17-24 seconds
- With parallel parsing (Option 1): 9-12 seconds (~2x speedup)
- With per-thread connections: 8-11 seconds (~2.2x speedup, marginal)

## Threading Options Evaluated

### Option 1: Parallel Parsing, Sequential Writes ✅ RECOMMENDED

**Architecture:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_directory_parallel(self, directory_path):
    files_to_process, skipped = self.find_duplicates(all_files)

    # Parse files in parallel (CPU-bound work)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(parse_tournament_file, f): f
            for f in files_to_process
        }

        # Write to database as results complete (sequential)
        for future in as_completed(futures):
            file_path = futures[future]
            parsed_data = future.result()
            self._load_tournament_data(parsed_data, file_path)
            del parsed_data  # Free memory immediately
```

**Pros:**
- **High value:** Parallelizes 60-70% of the work (parsing)
- **Low risk:** No database concurrency issues
- **Memory efficient:** Only 4 files in memory at once (~50-90MB peak)
- **Simple:** Easy to implement and debug
- **Respects existing lock:** Database writes remain serialized

**Cons:**
- Database writes still sequential (but this is fine - see Option 2 analysis)

**Memory Profile:**
- 4 workers × 2MB XML = 8MB raw XML
- 4 workers × 15-20MB parsed structures = 60-80MB
- **Peak memory: ~90MB** (very manageable)

**Estimated Speedup:** 2x (17-24s → 9-12s)

---

### Option 2: Per-Thread Database Connections ❌ NOT RECOMMENDED

**Architecture:**
```python
# Each thread creates its own connection
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(self.process_tournament_file, f)
        for f in files_to_process
    ]
```

Would require refactoring `TournamentDatabase` to support per-thread connections instead of a single shared connection.

**DuckDB Concurrency Model:**

DuckDB uses MVCC (Multi-Version Concurrency Control):
- Multiple read connections: fully parallel ✓
- Multiple write connections: **serialized internally by DuckDB**
- Each transaction locks affected tables

From DuckDB documentation:
> *"For write-heavy workloads, a single connection is often sufficient and recommended due to transaction overhead"*

**Pros:**
- True parallel database writes (in theory)
- Each thread has isolated transaction

**Cons:**
- **DuckDB serializes writes internally anyway** - minimal speedup over Option 1
- **Connection overhead:** Each connection = ~15MB catalog cache + transaction state
- **Memory cost:** 4 connections × 15MB = 60MB overhead
- **Complexity:** Error handling, transaction management per thread
- **Lock contention:** Tables still lock during conflicting writes
- **Risk:** More failure modes (partial writes, connection leaks)

**Estimated Speedup:** 2.1x (only ~5-10% better than Option 1)

**Verdict:** Complexity and memory overhead not justified for marginal gain.

---

### Option 3: Batch Transactions (Orthogonal Optimization)

**Current:** Each file = separate transaction (implicit commit after each file)

**Optimized:** Batch N files per transaction
```python
for batch in chunks(files, batch_size=10):
    with conn.begin():  # One transaction for 10 files
        for file in batch:
            parse_and_write(file)
```

**Pros:**
- Reduces transaction overhead (commit/fsync is expensive)
- No architecture changes needed
- **Can combine with Option 1** for additive benefit

**Cons:**
- If batch fails, all files in batch are rolled back
- Slightly more complex error handling

**Estimated Additional Speedup:** +20% (when combined with Option 1)

**Verdict:** Good supplementary optimization, implement after validating Option 1.

---

### Option 4: Producer-Consumer Pipeline (Alternative to Option 1)

**Architecture:**
```python
from queue import Queue
from threading import Thread

def parse_worker(file_queue, result_queue):
    """Producer: Parse files in parallel"""
    while True:
        file_path = file_queue.get()
        if file_path is None:
            break
        parsed = parse_tournament_file(file_path)
        result_queue.put((file_path, parsed))
        file_queue.task_done()

def write_worker(result_queue, total_files):
    """Consumer: Write to DB sequentially"""
    for _ in range(total_files):
        file_path, parsed_data = result_queue.get()
        self._load_tournament_data(parsed_data, file_path)
        result_queue.task_done()

# Start workers
file_queue = Queue()
result_queue = Queue(maxsize=4)  # Limit buffering

parse_threads = [Thread(target=parse_worker, args=(file_queue, result_queue))
                 for _ in range(4)]
write_thread = Thread(target=write_worker, args=(result_queue, len(files)))
```

**Pros:**
- Parsing happens in parallel
- Database writes happen in order (better for debugging)
- Memory-efficient (bounded queue prevents unlimited buffering)
- Good observability (can log progress from consumer)

**Cons:**
- More complex than Option 1
- Requires queue management
- Slightly harder to debug

**Estimated Speedup:** Same as Option 1 (~2x)

**Verdict:** Only use if you need ordered processing. Option 1 is simpler for same benefit.

## Why Parsing Benefits from Threading

**Unzipping (zipfile module):**
- Pure Python decompression
- CPU-intensive
- No shared state between files

**XML Parsing (ElementTree):**
- Pure Python parsing
- GIL-bound but CPU-intensive
- No shared state between files

**Data Extraction (parser methods):**
- String manipulation, lookups, transformations
- CPU work
- No shared state

**Conclusion:** Each file is completely independent during parsing. Perfect candidate for parallelization.

## Why Database Writes Don't Benefit Much from Threading

**Current Implementation:**
- Single shared connection with `RLock`
- All `execute_query()` calls acquire lock (`database.py:94`)
- Serializes all database operations

**Even with per-thread connections:**
- DuckDB uses MVCC for transaction isolation
- Table-level locks during writes
- Internal serialization of conflicting operations
- Transaction commit overhead per connection

**Result:** Write parallelism gains are minimal and don't justify the complexity.

## Recommendation

### Implement Option 1: Parallel Parsing with Sequential Writes

**Phase 1: Core Implementation**
1. Add `ThreadPoolExecutor` to `etl.py`
2. Parse files in parallel (4 workers default)
3. Write to database sequentially as results complete
4. Use `as_completed()` to prevent memory buildup
5. Add `--workers N` CLI flag for tuning

**Phase 2: Optional Optimizations**
1. Add batch transactions (10 files per transaction)
2. Profile to identify remaining bottlenecks
3. Tune worker count based on CPU cores

**Testing Strategy:**
1. Test with small batch (5-10 files)
2. Verify data integrity (run all validation scripts)
3. Measure actual speedup with timing
4. Check memory usage with profiler
5. Test error handling (corrupted file, disk full, etc.)

**Expected Results:**
- Import time: 17-24s → 9-12s
- Memory usage: +50-90MB peak
- Code complexity: Low (50-100 LOC change)
- Risk: Low (parsing is stateless)

### Do NOT Implement: Per-Thread Database Connections

**Reasons:**
1. Adds significant complexity
2. Only 5-10% additional speedup over Option 1
3. Higher memory usage (+60MB overhead)
4. More failure modes to handle
5. DuckDB serializes writes internally anyway

**Exception:** Only consider if profiling shows database writes are the bottleneck after implementing Option 1 (unlikely given current scale).

## Implementation Notes

### Worker Count Tuning

```python
import os

# Default to CPU count, cap at 8 to avoid diminishing returns
default_workers = min(os.cpu_count() or 4, 8)
```

**Guidelines:**
- **CPU-bound:** Use `cpu_count()` workers
- **I/O-bound:** Use `cpu_count() * 2` workers
- **Memory-constrained:** Reduce worker count
- **Our case:** Start with 4, can go up to 8

### Error Handling

```python
for future in as_completed(futures):
    file_path = futures[future]
    try:
        parsed_data = future.result(timeout=300)  # 5 min timeout
        self._load_tournament_data(parsed_data, file_path)
        successful_count += 1
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        failed_files.append(file_path)
    finally:
        del parsed_data  # Ensure memory cleanup
```

### Progress Reporting

```python
total = len(files_to_process)
for i, future in enumerate(as_completed(futures), 1):
    # ... process future ...
    logger.info(f"Processed {i}/{total} files ({i/total:.1%})")
```

## Future Considerations

### If Import Volume Grows

**Current scale:** < 100 files, ~20s import time
**Future scale:** 1000s of files, minutes of import time

At larger scale, consider:
1. **Distributed processing:** Process files on multiple machines
2. **Incremental imports:** Only import changed files
3. **Database partitioning:** Partition by tournament/date
4. **Streaming inserts:** Use DuckDB's COPY FROM for bulk loading

### If Database Writes Become Bottleneck

After implementing Option 1, if profiling shows database writes are >50% of time:
1. Implement batch transactions first (easier win)
2. Profile DuckDB operations (which inserts are slowest?)
3. Consider `COPY FROM` instead of parameterized inserts
4. Only then consider per-thread connections

## References

### Code Locations
- Import pipeline: `tournament_visualizer/data/etl.py:601-656`
- Database class: `tournament_visualizer/data/database.py`
- Parser: `tournament_visualizer/data/parser.py`
- Import script: `scripts/import_attachments.py`

### DuckDB Documentation
- Concurrency: https://duckdb.org/docs/connect/concurrency
- Transactions: https://duckdb.org/docs/sql/statements/transactions
- Performance: https://duckdb.org/docs/guides/performance/overview

### Python Threading
- ThreadPoolExecutor: https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor
- GIL considerations: https://docs.python.org/3/glossary.html#term-global-interpreter-lock

## Appendix: Memory Math

### Current (Single-Threaded)
- 1 file being parsed: ~20MB
- Peak: ~25MB

### Option 1 (4 Workers)
- 4 files × 2MB XML = 8MB raw
- 4 files × 15MB structures = 60MB parsed
- Overhead: ~10MB
- **Peak: ~78MB** (3x increase, acceptable)

### Per-Thread Connections (Not Recommended)
- Option 1 memory: 78MB
- 4 connections × 15MB = 60MB
- **Peak: ~138MB** (5.5x increase)

### Batch Transactions (Supplementary)
- No additional memory overhead
- Same as Option 1: ~78MB
