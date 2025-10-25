# Google Drive Migration - Findings & Recommendations

> **Status**: Completed and archived (2025-10-25)
>
> Feature complete and documented in CLAUDE.md (Google Drive Integration section).

## Executive Summary

After analyzing the Google Drive folder and current system architecture, **I recommend Option 2 (Hybrid Approach)** with a simplified implementation using direct download links instead of the full Google Drive API.

**Key insight:** The Google Drive folder already uses a filename format that includes match numbers (e.g., `01-anarkos-becked.zip`, `15-fiddler-ninja.zip`), which can likely be mapped directly to Challonge match IDs.

## Google Drive Folder Analysis

### Current State
- **Folder:** `completed-game-save-files`
- **Location:** https://drive.google.com/drive/folders/1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk
- **Access:** Publicly shared (view/download)
- **File Count:** 18 files visible (numbered 01-27, some gaps)
- **File Sizes:** All under 350KB (well under Challonge's limit!)

### Filename Pattern
All files follow the pattern: `{NN}-{player1}-{player2}.zip`

Examples:
- `01-anarkos-becked.zip`
- `15-fiddler-ninja.zip`
- `27-alcaras-Michael-of-Minsk.zip`

**Critical observation:** The number prefix (e.g., `01`, `15`, `27`) appears to correspond to match order or bracket position, **not Challonge match IDs**.

### File Size Paradox

**Important finding:** All files in the Google Drive folder are **under 350KB**, which is well under Challonge's ~100MB attachment limit.

**This raises questions:**
1. Why are files on Google Drive if they're not oversized?
2. Are these files also on Challonge? Or is GDrive the primary source?
3. Is the size limit issue anticipated (future matches) or already occurring?

## Updated Recommendation: Hybrid Lite

Given that the GDrive files appear to be the primary source (not overflow for oversized files), I recommend a **simplified hybrid approach**:

### Approach: Challonge Metadata + Google Drive Direct Links

Instead of implementing the full Google Drive API, use direct download links with a mapping file.

### Implementation

```json
// data/gdrive_match_mapping.json
{
  "_schema_version": "1.0",
  "_notes": "Maps Challonge match IDs to Google Drive files",
  "_gdrive_folder_id": "1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk",

  "matches": {
    "123456789": {
      "gdrive_file_id": "1abc...",
      "gdrive_filename": "01-anarkos-becked.zip",
      "match_number": 1,
      "players": ["anarkos", "becked"],
      "source": "gdrive",
      "added_date": "2024-09-21"
    },
    "123456790": {
      "gdrive_file_id": "1def...",
      "gdrive_filename": "15-fiddler-ninja.zip",
      "match_number": 15,
      "players": ["fiddler", "ninja"],
      "source": "gdrive",
      "added_date": "2024-10-10"
    }
  }
}
```

### Download Implementation

```python
# In download_attachments.py

def download_from_gdrive_direct(file_id: str, output_path: Path) -> bool:
    """Download file from Google Drive using direct link.

    No API auth required for publicly shared files.
    """
    url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        logger.error(f"Failed to download from GDrive: {e}")
        return False


def download_match_save(match_id: int, match_data: dict) -> Optional[Path]:
    """Download save file from best available source.

    Priority:
    1. Google Drive (if in mapping)
    2. Challonge attachment (fallback)
    """
    # Check GDrive mapping first
    if mapping := get_gdrive_mapping(match_id):
        file_id = mapping['gdrive_file_id']
        filename = f"match_{match_id}_{mapping['gdrive_filename']}"
        save_path = SAVES_DIR / filename

        if download_from_gdrive_direct(file_id, save_path):
            logger.info(f"Downloaded match {match_id} from Google Drive")
            return save_path

    # Fallback to Challonge
    if attachment_url := match_data.get('attachment_url'):
        filename = f"match_{match_id}_challonge.zip"
        save_path = SAVES_DIR / filename

        if download_attachment(attachment_url, save_path):
            logger.info(f"Downloaded match {match_id} from Challonge")
            return save_path

    logger.warning(f"No save file found for match {match_id}")
    return None
```

## Creating the Mapping File

### Option A: Manual Mapping (Initial Setup)

Since there are only ~18 files currently, manual mapping is feasible:

```bash
# 1. Get Challonge match IDs
uv run python scripts/list_challonge_matches.py > matches.txt

# 2. Get Google Drive file IDs (from sharing links)
# Visit: https://drive.google.com/drive/folders/1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk
# For each file, right-click > "Get link" > Extract file ID from URL

# 3. Manually create mapping.json matching:
#    - Match number prefix (01, 15, 27) with player names
#    - To Challonge match records (also have player names)
```

### Option B: Semi-Automated Mapping

```python
# scripts/create_gdrive_mapping.py

def match_by_players(gdrive_filename: str, challonge_matches: list) -> Optional[int]:
    """Match GDrive file to Challonge match using player names.

    Example:
    - GDrive: "15-fiddler-ninja.zip"
    - Challonge: Match 123456789 with players "Fiddler" and "Ninjaa"
    - Normalized match: "fiddler" vs "ninja" (partial match OK)
    """
    # Parse GDrive filename
    match = re.match(r'(\d+)-(.+?)-(.+?)\.zip', gdrive_filename)
    if not match:
        return None

    match_num, player1, player2 = match.groups()

    # Normalize names
    player1_norm = normalize_name(player1)
    player2_norm = normalize_name(player2)

    # Search Challonge matches
    for challonge_match in challonge_matches:
        c_player1_norm = normalize_name(challonge_match['player1_name'])
        c_player2_norm = normalize_name(challonge_match['player2_name'])

        # Check if names match (order-independent, partial match OK)
        if (player1_norm in c_player1_norm or c_player1_norm in player1_norm) and \
           (player2_norm in c_player2_norm or c_player2_norm in player2_norm):
            return challonge_match['id']

        if (player1_norm in c_player2_norm or c_player2_norm in player1_norm) and \
           (player2_norm in c_player1_norm or c_player1_norm in player2_norm):
            return challonge_match['id']

    return None
```

### Option C: Use Challonge Round Data

If the number prefix corresponds to match order in the bracket:

```python
def match_by_round_order(match_num: int, challonge_matches: list) -> Optional[int]:
    """Match GDrive file to Challonge match using round order.

    Assumptions:
    - Files numbered sequentially by bracket progression
    - Challonge matches have round and suggested_play_order
    """
    # Sort Challonge matches by round, then suggested play order
    sorted_matches = sorted(
        challonge_matches,
        key=lambda m: (m.get('round', 0), m.get('suggested_play_order', 0))
    )

    # Match number 1 = first match, etc.
    if 1 <= match_num <= len(sorted_matches):
        return sorted_matches[match_num - 1]['id']

    return None
```

## Questions to Resolve

Before implementing, we need answers to:

### 1. **Are files on both Challonge AND Google Drive?**
   - Check: Do Challonge matches have attachments?
   - If yes: Are they the same files or different?
   - If no: GDrive is the only source

### 2. **What is the match ID mapping?**
   - Does `01-anarkos-becked.zip` correspond to Challonge match ID X?
   - Can we validate the mapping using player names?
   - Do we have access to bracket order/round data?

### 3. **Why Google Drive?**
   - Is this replacing Challonge attachments entirely?
   - Or supplementing (some files too large, others on Challonge)?
   - Is this a permanent change or temporary?

### 4. **Who manages Google Drive?**
   - Tournament Organizer uploads files?
   - Players upload directly?
   - How are file IDs shared with us?

## Next Steps

### Immediate (30 minutes)
1. ✅ Query Challonge API for match list with player names
2. ✅ Compare with Google Drive filenames
3. ✅ Determine if we can auto-match by player names
4. ✅ Check if Challonge matches have attachments

### Short-term (2-4 hours)
1. Create mapping file schema
2. Write semi-automated mapping script
3. Manually review and validate mappings
4. Test download for 1-2 files

### Medium-term (4-8 hours)
1. Modify `download_attachments.py` to support dual sources
2. Update documentation for Tournament Organizer
3. Deploy to production
4. Monitor first full sync

## Validation Script

```python
# scripts/validate_gdrive_mapping.py

def validate_mapping(mapping_file: Path, challonge_api: ChallongeApi):
    """Validate that all mappings are correct."""

    with open(mapping_file) as f:
        mappings = json.load(f)

    errors = []
    warnings = []

    # Check 1: All Challonge matches have files
    challonge_matches = challonge_api.matches.get_all(tournament_id)
    for match in challonge_matches:
        match_id = match['id']

        if match_id not in mappings['matches']:
            # Check if Challonge has attachment
            if match.get('attachment_count', 0) > 0:
                warnings.append(f"Match {match_id} has Challonge attachment but no GDrive mapping")
            else:
                errors.append(f"Match {match_id} has no save file (Challonge or GDrive)")

    # Check 2: All GDrive mappings are valid
    for match_id, mapping in mappings['matches'].items():
        # Validate file_id format
        if not mapping['gdrive_file_id']:
            errors.append(f"Match {match_id} missing gdrive_file_id")

        # Validate players match Challonge
        challonge_match = next(
            (m for m in challonge_matches if m['id'] == int(match_id)),
            None
        )

        if not challonge_match:
            errors.append(f"Match {match_id} in mapping but not in Challonge")

    # Report
    print(f"✅ Valid mappings: {len(mappings['matches'])}")
    print(f"⚠️  Warnings: {len(warnings)}")
    print(f"❌ Errors: {len(errors)}")

    for warning in warnings:
        print(f"  ⚠️  {warning}")

    for error in errors:
        print(f"  ❌ {error}")

    return len(errors) == 0
```

## Migration Path

### Phase 0: Investigation (Today)
```bash
# Check current state
uv run python scripts/list_challonge_matches.py --verbose

# Compare with GDrive folder
# Document findings
```

### Phase 1: Prototype Mapping (1-2 hours)
```bash
# Create mapping for 2-3 matches manually
# Test download and import
uv run python scripts/test_gdrive_download.py --match-id 123456789
uv run python scripts/import_attachments.py --directory saves
```

### Phase 2: Full Mapping (2-3 hours)
```bash
# Run automated mapping tool
uv run python scripts/create_gdrive_mapping.py --output data/gdrive_match_mapping.json

# Manually review and fix edge cases
# Validate mappings
uv run python scripts/validate_gdrive_mapping.py
```

### Phase 3: Integration (2-4 hours)
```bash
# Modify download_attachments.py
# Test full workflow locally
uv run python scripts/download_attachments.py --verbose
uv run python scripts/import_attachments.py --directory saves --force
uv run python scripts/link_players_to_participants.py

# Deploy to production
./scripts/sync_tournament_data.sh
```

### Phase 4: Documentation (1 hour)
- Update CLAUDE.md with new workflow
- Document mapping file format
- Create guide for Tournament Organizer

## Complexity Comparison

| Approach | Setup Time | Ongoing Effort | Complexity | Reliability |
|----------|-----------|----------------|------------|-------------|
| **Direct Links (Recommended)** | 4-6 hours | 15 min/batch | Low | High |
| **Google Drive API** | 8-12 hours | 5 min/batch | Medium | High |
| **Filename Only** | 2-3 hours | 0 min | Very Low | Low (breaks tourney context) |
| **Dual Upload** | 0 hours | 2x upload time | Very Low | Low (human error) |

## Risk Assessment

### Low Risk ✅
- Files are small (no corrupted downloads)
- Filenames are consistent
- Public sharing enabled (no auth issues)

### Medium Risk ⚠️
- Manual mapping required (18 files = manageable)
- Player name variations may cause mismatches
- Need to validate all mappings

### High Risk ❌
- **If Challonge match IDs don't align with file numbers:** Manual mapping becomes tedious
- **If Tournament Organizer adds files without notification:** Our mapping gets stale

## Mitigation Strategies

1. **Stale mapping detection:**
   ```python
   def check_for_new_files(gdrive_folder_url: str) -> list[str]:
       """Parse GDrive folder HTML to detect new files."""
       # Could scrape folder page or use RSS feed
       # Alert if new files appear that aren't in mapping
   ```

2. **Mapping validation as pre-commit hook:**
   ```bash
   # .git/hooks/pre-commit
   uv run python scripts/validate_gdrive_mapping.py || exit 1
   ```

3. **Tournament Organizer notification system:**
   - Email alert when new matches complete
   - Includes file naming instructions
   - Confirms file uploaded to GDrive

## Conclusion

**Recommended Action:** Implement Option 2 (Hybrid) with direct download links.

**Estimated Total Effort:** 8-10 hours
- 2 hours: Investigation & mapping prototype
- 3 hours: Full mapping creation & validation
- 3 hours: Integration & testing
- 2 hours: Documentation & deployment

**Ongoing Maintenance:** ~15 minutes per new batch of files (assuming 5-10 new matches at once)

**Next Immediate Step:** Run investigation scripts to determine if we can auto-match GDrive files to Challonge match IDs using player names.
