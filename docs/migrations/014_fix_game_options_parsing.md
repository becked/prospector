# Migration 014: Fix Game Options and DLC Parsing

**Date:** 2025-01-25
**Status:** Pending Re-import

## Summary
Fixes parser to correctly capture game options and DLC content from XML. Previously these were stored as NULL because the parser only captured elements with text content, but these elements are self-closing tags where presence indicates "enabled".

## Problem

XML format:
```xml
<GameOptions>
  <GAMEOPTION_COMPETITIVE_MODE />  <!-- No text content, just presence = enabled -->
</GameOptions>
```

Old parser:
```python
if opt.text:  # Always false for self-closing tags
    game_options[opt.tag] = opt.text
```

## Parser Fix

In `parser.py` `extract_match_metadata()`:

```python
# Game options are self-closing tags - presence means enabled
for opt in option_elements:
    game_options[opt.tag] = opt.text if opt.text else True
```

Same fix applied to DLC content extraction.

## Files Modified

| File | Changes |
|------|---------|
| `tournament_visualizer/data/parser.py` | Fixed game options extraction to capture self-closing tags |
| `tournament_visualizer/data/parser.py` | Fixed xpath from `.//DLC/*` to `.//GameContent/*` |
| `tournament_visualizer/data/queries.py` | Added Competitive Mode bonus (+40/turn) to science tracking |

## Science Tracking Impact

With this fix, Competitive Mode games now correctly track:
- **+40 science/turn** per player (game setting bonus)

This was previously a major source of "untracked" science.

## Data Re-import Required

Yes - full re-import needed to populate game_options in match_metadata.

```bash
# Re-import all saves
uv run python scripts/import_attachments.py --directory saves --force --verbose
```

## Verification

After re-import:
```bash
uv run duckdb data/tournament_data.duckdb -readonly -c "
SELECT
    match_id,
    json_extract_string(game_options, '$.GAMEOPTION_COMPETITIVE_MODE') as competitive
FROM match_metadata
WHERE game_options IS NOT NULL
LIMIT 5
"
```

Expected: All tournament matches should have `competitive = 'true'`.

## Related Features

This migration enables:
1. **Competitive Mode Science Bonus**: +40/turn per player now tracked
2. **Game Settings Analysis**: Can now analyze which game options are used
3. **DLC Usage Tracking**: Can see which DLCs are enabled per match
