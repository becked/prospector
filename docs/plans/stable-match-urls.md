# Plan: Stable Match URLs Using Challonge Match Numbers

## Problem

Match pages currently use internal database IDs in their URLs:

```
/matches?match_id=3
```

These IDs are auto-incremented by the database and **change on reimport**, breaking bookmarks, shared links, and any external references.

## Solution

Replace database IDs with Challonge's `suggested_play_order` — the match number visible on the tournament bracket (1, 2, 3, ... 21, 22, ... 41, 42, ... 51, etc.).

**New URL format:**

```
/matches?match=21
```

These numbers are stable, human-readable, and map directly to what users see on Challonge.

## Background: Challonge Match Identifiers

The Challonge API provides three identifiers per match:

| Field | Example | Description |
|-------|---------|-------------|
| `id` | `426504724` | Internal API ID (9-digit, opaque). Already stored as `challonge_match_id`. |
| `round` | `2` or `-1` | Tournament round (signed). Already stored as `tournament_round`. |
| `suggested_play_order` | `21` | **Match number shown on bracket.** Not currently stored. |

We already fetch all three from the API during import (in `fetch_tournament_rounds()` at `etl.py:24`) but only capture `id` and `round`. The `suggested_play_order` field is in the same API response — we just discard it.

---

## Implementation

### Phase 1: Store `suggested_play_order`

**1a. Add column to `matches` table**

File: `tournament_visualizer/data/database.py` (~line 218)

```sql
ALTER TABLE matches ADD COLUMN suggested_play_order INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_play_order
ON matches(suggested_play_order);
```

Add after `tournament_round INTEGER` in `_create_matches_table()`. Use a UNIQUE index since these numbers should be unique per tournament.

**1b. Expand `fetch_tournament_rounds()` to also return play order**

File: `tournament_visualizer/data/etl.py` (~line 24)

The function currently returns `Dict[int, int]` mapping `challonge_match_id -> round`. It needs to return both round and play order. Options:

- **Option A (minimal):** Return `Dict[int, dict]` mapping `challonge_match_id -> {"round": int, "play_order": int}`. Rename function to `fetch_tournament_metadata()`.
- **Option B (separate cache):** Add a second cache dict. Simpler but more parameters to thread through.

Option A is cleaner. The API response already has both fields:

```python
# Current (line 55):
round_cache = {match["id"]: match["round"] for match in matches}

# New:
match_cache = {
    match["id"]: {
        "round": match["round"],
        "play_order": match["suggested_play_order"],
    }
    for match in matches
}
```

**1c. Store play order during import**

File: `tournament_visualizer/data/etl.py` (~line 144-154)

In `process_tournament_file()`, where `tournament_round` is extracted from the cache, also extract and store `suggested_play_order`:

```python
if challonge_match_id:
    match_metadata["challonge_match_id"] = challonge_match_id
    cached = self.match_cache.get(challonge_match_id, {})
    if cached.get("round") is not None:
        match_metadata["tournament_round"] = cached["round"]
    if cached.get("play_order") is not None:
        match_metadata["suggested_play_order"] = cached["play_order"]
```

**1d. Update `bulk_insert_match()` / `insert_match()`**

File: `tournament_visualizer/data/database.py` (~line 1437)

Add `suggested_play_order` to the INSERT column list.

**1e. Reimport**

```bash
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

**1f. Verify**

```sql
SELECT match_id, challonge_match_id, suggested_play_order, tournament_round
FROM matches
ORDER BY suggested_play_order;
```

All rows should have a non-NULL `suggested_play_order`.

**1g. Export updated schema docs**

```bash
uv run python scripts/export_schema.py
```

---

### Phase 2: Update URL Scheme

**2a. Add query method to resolve play order -> match_id**

File: `tournament_visualizer/data/queries.py`

```python
def get_match_id_by_play_order(self, play_order: int) -> Optional[int]:
    """Get the database match_id for a given suggested_play_order."""
    ...
```

Also add a method (or update `get_match_summary()`) to include `suggested_play_order` in the match summary results, since the dropdown and link generation need it.

**2b. Update match dropdown to use play order as value**

File: `tournament_visualizer/pages/matches.py` (~line 417)

Currently:
```python
options.append({"label": label, "value": row["match_id"]})
```

Change to use `suggested_play_order` as the value. All downstream callbacks that receive this value then resolve it to `match_id` for queries.

**Alternative approach:** Keep `match_id` as the internal value for the dropdown (avoids touching every callback), but translate between `match_id` and `suggested_play_order` only at the URL boundary. This is simpler — fewer changes, less risk.

**Recommended: URL-boundary translation only.** The `sync_match_selection` callback is the single point where URL <-> dropdown sync happens. Change it to:
- Read `?match=N` from URL, resolve to `match_id` via lookup, set dropdown value
- When dropdown changes, resolve `match_id` to `suggested_play_order`, set URL

This keeps all existing callbacks untouched — they continue using `match_id` internally.

**2c. Update `sync_match_selection` callback**

File: `tournament_visualizer/pages/matches.py` (~line 292-367)

The callback currently parses `?match_id=N` from the URL and uses it directly as the dropdown value. Change to:

1. Parse `?match=N` (the play order) from URL
2. Look up corresponding `match_id` from a preloaded mapping
3. Set dropdown to `match_id`
4. When dropdown fires, reverse-map `match_id` -> play order for URL

The mapping can be loaded once (it's small — ~50 entries) and cached.

**2d. Update link generation in overview page**

File: `tournament_visualizer/pages/overview.py` (~line 1785)

Currently:
```python
"match_link": f"[{game_name}](/matches?match_id={match_id})",
```

Change to:
```python
"match_link": f"[{game_name}](/matches?match={play_order})",
```

This requires `suggested_play_order` to be available in the query results used here (from `get_match_summary()` or `get_matches_by_round()`).

**2e. Search for any other places generating match URLs**

Currently only one location generates match links (`overview.py:1785`), but verify with:
```bash
grep -r "match_id=" tournament_visualizer/pages/
grep -r "/matches?" tournament_visualizer/
```

---

### Phase 3: Backward-Compatible Redirect

Support old `?match_id=` URLs so existing bookmarks don't break.

**3a. Handle old URL format in `sync_match_selection`**

In the same callback, check for both URL parameter names:

```python
from urllib.parse import parse_qs

params = parse_qs(url_search.lstrip("?"))

# New format: ?match=21 (suggested_play_order)
play_order = params.get("match", [None])[0]

# Legacy format: ?match_id=3 (database match_id)
legacy_match_id = params.get("match_id", [None])[0]

if play_order:
    match_id = play_order_to_match_id[int(play_order)]
elif legacy_match_id:
    match_id = int(legacy_match_id)
    # Redirect to new URL format
    play_order = match_id_to_play_order.get(match_id)
    if play_order:
        return match_id, f"?match={play_order}", ""
```

This transparently handles old links and rewrites the URL to the new format.

**Note:** Since database `match_id` values change on reimport, old `?match_id=` links will only work until the next reimport. This is acceptable — the redirect is a courtesy for the transition period, not a permanent guarantee.

---

## Files Changed (Summary)

| File | Change |
|------|--------|
| `tournament_visualizer/data/database.py` | Add `suggested_play_order` column to schema and insert methods |
| `tournament_visualizer/data/etl.py` | Expand `fetch_tournament_rounds()` to capture play order; store it during import |
| `tournament_visualizer/data/queries.py` | Add `suggested_play_order` to `get_match_summary()`; add lookup method |
| `tournament_visualizer/pages/matches.py` | Translate between play order (URL) and match_id (internal) in sync callback |
| `tournament_visualizer/pages/overview.py` | Generate links with `?match=` instead of `?match_id=` |
| `docs/schema.sql` | Updated via export script |
| `docs/database-schema.md` | Updated via export script |

## Migration Doc

Create `docs/migrations/012_add_suggested_play_order.md` following the pattern in `010_add_tournament_round.md`.

## Testing

- Verify all matches have `suggested_play_order` after reimport
- Verify `?match=21` loads the correct match
- Verify old `?match_id=3` redirects to `?match=N`
- Verify overview table links use new format
- Verify dropdown selection updates URL to `?match=N`
- Verify direct URL navigation (paste URL into browser) works

## Edge Cases

- **NULL `suggested_play_order`:** If a match has no Challonge data (local test file), fall back to `match_id` in URLs. Handle in the URL translation layer.
- **Duplicate play orders:** Shouldn't happen within a tournament, but the UNIQUE index will catch it at insert time.
- **Multiple tournaments:** If this app ever supports multiple tournaments, `suggested_play_order` alone won't be unique. The UNIQUE index would need to become a composite on `(tournament_id, suggested_play_order)`. Not needed now (YAGNI) but worth noting.
