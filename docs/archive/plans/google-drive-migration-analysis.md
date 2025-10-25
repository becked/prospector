# Google Drive Save Source Migration - Analysis

## Current Architecture Overview

The current system has these key components:

1. **Save File Acquisition** (`download_attachments.py`)
   - Fetches save files from Challonge API
   - Uses `attachment_count` and `asset_url` from match records
   - Downloads to local `saves/` directory
   - Names files: `match_{challonge_match_id}_{filename}.zip`

2. **Save File Processing** (`import_attachments.py`)
   - Parses ZIP files containing XML save data
   - Extracts match metadata (map, turns, victory conditions, etc.)
   - Extracts player data (names, stats, resources, events)
   - Stores in DuckDB with `challonge_match_id` as the link

3. **Participant Linking** (`link_players_to_participants.py`)
   - Matches save file player names to Challonge participants
   - Uses normalized name matching + manual overrides
   - Links players across multiple matches via `participant_id`

4. **Metadata Sync** (`sync_challonge_participants.py`)
   - Fetches tournament structure from Challonge API
   - Stores participants (seeding, usernames)
   - Updates matches with participant IDs for player1/player2/winner

## Problem Statement

Challonge has attachment size limits (~100MB per match) and some tournament saves exceed this limit. A Google Drive folder exists with all saves, including those too large for Challonge.

**Key Questions:**
1. How do we match Google Drive files to tournament matches?
2. What happens to the participant linking workflow?
3. Do we still need Challonge API at all?
4. What's the migration path?

## Critical Dependency: challonge_match_id

The current system uses `challonge_match_id` as the **primary link** between:
- Save files (filename contains match ID)
- Database match records
- Participant assignment (player1/player2/winner participant IDs)

**Without challonge_match_id, we cannot:**
- Link save files to specific matches in the bracket
- Determine which participants played which match
- Show accurate tournament bracket progression
- Track player statistics across tournament rounds

## Option 1: Google Drive Only (Filename-Based Matching)

**Approach:** Parse Google Drive filenames to extract match information.

### Implementation

```python
# Filename patterns to support:
# 1. "match_12345_filename.zip" (current Challonge format)
# 2. "PlayerName1_vs_PlayerName2_Round2.zip" (common manual format)
# 3. "R2_PlayerA_PlayerB.zip" (short format)

def parse_gdrive_filename(filename: str) -> dict:
    """Extract match info from Google Drive filename."""
    # Try Challonge format first
    if match := re.match(r'match_(\d+)_.*\.zip', filename):
        return {'challonge_match_id': int(match.group(1))}

    # Try player vs player format
    if match := re.match(r'(.+?)_vs_(.+?)(?:_Round(\d+))?\.zip', filename):
        return {
            'player1_name': match.group(1),
            'player2_name': match.group(2),
            'round': match.group(3)
        }

    # Try short format
    if match := re.match(r'R(\d+)_(.+?)_(.+?)\.zip', filename):
        return {
            'round': match.group(1),
            'player1_name': match.group(2),
            'player2_name': match.group(3)
        }

    return {}
```

### Pros
- No dependency on Challonge API for saves
- Could work with any tournament system (not Challonge-specific)
- Handles large files (Google Drive limit is 5TB)

### Cons
- **Critical flaw:** Cannot reliably determine `challonge_match_id`
  - Player names in filenames may not match participant names
  - Same players can play multiple matches (loser's bracket)
  - Round numbers alone don't uniquely identify matches
- **Breaks participant linking:**
  - Cannot use `player1_participant_id`/`player2_participant_id` from Challonge
  - Would rely entirely on name matching (error-prone)
  - No way to validate matches against bracket structure
- **No bracket context:**
  - Can't show "Round 2, Winners Bracket" vs "Round 2, Losers Bracket"
  - Can't track tournament progression
  - Can't validate save file integrity (is this the right match?)

### Verdict
**❌ Not viable.** Losing `challonge_match_id` breaks too much functionality. The app's value proposition is tournament analytics, not just individual match analysis.

## Option 2: Hybrid Approach - Challonge Metadata + Google Drive Files

**Approach:** Keep using Challonge API for tournament structure, fetch saves from Google Drive.

### Implementation

```python
# Step 1: Sync Challonge tournament structure (participants, matches)
# - Run sync_challonge_participants.py as usual
# - Stores challonge_match_id, participant IDs, bracket structure

# Step 2: Download saves from Google Drive with mapping
# - Maintain a mapping file: challonge_match_id -> gdrive_file_id
# - Download from Google Drive instead of Challonge attachments

# Mapping file structure: data/gdrive_match_mapping.json
{
    "12345": {
        "gdrive_file_id": "1abc...",
        "gdrive_filename": "match_12345_round2.zip",
        "added_date": "2025-01-15",
        "notes": "Too large for Challonge (150MB)"
    }
}

# Modified download_attachments.py
def download_from_gdrive(match_id: int, gdrive_file_id: str) -> Path:
    """Download save file from Google Drive."""
    from googleapiclient.discovery import build

    service = build('drive', 'v3', credentials=get_gdrive_credentials())
    request = service.files().get_media(fileId=gdrive_file_id)

    # Download to saves/ with consistent naming
    save_path = Path(f"saves/match_{match_id}_gdrive.zip")
    with open(save_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    return save_path

# Step 3: Import saves as usual
# - import_attachments.py works unchanged
# - Files are named consistently: match_{challonge_match_id}_*.zip
```

### Workflow

```bash
# Initial setup: Create mapping file manually or via script
uv run python scripts/create_gdrive_mapping.py \
    --gdrive-folder-id "1ss8ToApXPY7o2syLV76i_CJdoS-lnHQk"

# Regular sync workflow (automated):
1. uv run python scripts/sync_challonge_participants.py  # Get tournament structure
2. uv run python scripts/download_attachments.py         # Now checks both Challonge + GDrive
3. uv run python scripts/import_attachments.py --directory saves --force
4. uv run python scripts/link_players_to_participants.py  # Works unchanged
```

### Pros
- ✅ **Preserves challonge_match_id** - No breaking changes
- ✅ **Participant linking works unchanged** - Uses Challonge participant data
- ✅ **Bracket structure intact** - Tournament rounds, seeding, progression
- ✅ **Handles large files** - Google Drive has no practical size limit
- ✅ **Fallback capability** - Can check Challonge first, GDrive second
- ✅ **Incremental migration** - Move files to GDrive as needed

### Cons
- ⚠️ **Manual mapping required** - Need to link challonge_match_id to gdrive_file_id
- ⚠️ **Two sources of truth** - Some saves on Challonge, some on GDrive
- ⚠️ **Google Drive API setup** - OAuth, credentials, rate limits
- ⚠️ **Complexity** - More moving parts than current system

### Migration Path

**Phase 1: Setup Google Drive API**
1. Create Google Cloud project
2. Enable Drive API
3. Create OAuth credentials (or service account)
4. Store credentials securely (not in git)

**Phase 2: Create Mapping Tool**
```python
# scripts/create_gdrive_mapping.py
# 1. List all files in GDrive folder
# 2. Parse filenames to extract match IDs (where possible)
# 3. Query Challonge API to validate match IDs
# 4. Generate mapping JSON with file IDs
# 5. Flag files that couldn't be auto-matched (need manual review)
```

**Phase 3: Modify Download Script**
```python
# scripts/download_attachments.py
# 1. Load gdrive_match_mapping.json
# 2. For each match:
#    a. Try Challonge attachment first (if exists and not oversized)
#    b. Fallback to GDrive if in mapping
#    c. Log which source was used
# 3. Download with consistent naming
```

**Phase 4: Deploy & Sync**
```bash
# Production sync remains simple:
./scripts/sync_tournament_data.sh

# Internally now handles both sources
```

### Verdict
**✅ Recommended.** This preserves all existing functionality while solving the file size problem. The mapping file is a one-time setup cost.

## Option 3: Google Drive Primary + Challonge Mapping Service

**Approach:** Use Google Drive as primary storage, create a lightweight service to maintain match ID mappings.

### Implementation

This is similar to Option 2, but inverts the relationship:
- **Primary source:** Google Drive folder (Tournament Organizer uploads here)
- **Mapping service:** Small web service or cron job that:
  1. Watches Google Drive folder for new files
  2. Parses filenames and extracts metadata
  3. Queries Challonge API to find matching match_id
  4. Updates mapping file automatically

### Pros
- ✅ Tournament Organizer workflow simpler (just upload to GDrive)
- ✅ Less manual mapping work (automated where possible)
- ✅ Still preserves challonge_match_id

### Cons
- ⚠️ **More complex infrastructure** - Requires always-on service or scheduled job
- ⚠️ **Filename parsing still fragile** - Auto-matching will fail on inconsistent names
- ⚠️ **Overkill for current needs** - Tournament is small (dozens of matches, not thousands)

### Verdict
**⚠️ Over-engineered.** Option 2's manual mapping is acceptable for this tournament size. Build this if tournament grows to 100+ matches.

## Option 4: Dual Upload Requirement

**Approach:** Require TOs to upload saves to both Challonge (small files) and Google Drive (all files).

### Implementation

- Keep current system unchanged
- Document requirement: "Upload saves to both locations"
- For oversized files: Skip Challonge, upload to GDrive only, use Option 2's mapping

### Pros
- ✅ **Minimal code changes** - Current system works as-is
- ✅ **Best UX for small files** - Challonge attachment is convenient
- ✅ **Escape hatch for large files** - GDrive mapping for edge cases

### Cons
- ⚠️ **Manual overhead for TOs** - Double upload work
- ⚠️ **Easy to forget** - TOs might only upload to one location
- ⚠️ **Storage waste** - Same files stored twice

### Verdict
**⚠️ Acceptable short-term.** Good for transitioning. Not sustainable long-term.

## Recommended Solution: Option 2 (Hybrid)

**Implement a hybrid system that preserves challonge_match_id while enabling Google Drive storage.**

### Why This Works

1. **Preserves tournament context** - Bracket structure, seeding, rounds
2. **Solves file size problem** - Move large files to GDrive as needed
3. **Backward compatible** - Existing Challonge attachments still work
4. **Incremental migration** - Can migrate files one at a time
5. **Reasonable complexity** - One-time mapping setup, then automated

### Implementation Priority

**High Priority (Required for large files):**
1. ✅ Google Drive API setup and authentication
2. ✅ Mapping file structure and schema
3. ✅ Modified download script (Challonge + GDrive support)
4. ✅ Mapping creation tool (automated + manual override)

**Medium Priority (Quality of life):**
5. ⚠️ Validation script - Verify all matches have saves (either source)
6. ⚠️ GDrive folder watcher - Auto-detect new files
7. ⚠️ Mapping UI - Web interface for managing mappings

**Low Priority (Nice to have):**
8. ⏸️ Automatic file size detection - Move large Challonge files to GDrive
9. ⏸️ Duplicate detection - Warn if same match has multiple saves

### Estimated Effort

**Initial Implementation:** 8-12 hours
- 2 hours: GDrive API setup, credentials, auth flow
- 3 hours: Mapping file schema, creation tool
- 3 hours: Modified download script with dual sources
- 2 hours: Testing, documentation, deployment script updates

**Ongoing Maintenance:** 30 minutes per new batch of files
- Review auto-generated mappings
- Manually map any files that couldn't be auto-matched
- Run sync script

### Risks & Mitigations

**Risk 1:** Google Drive API rate limits (100 requests/100 seconds)
- **Mitigation:** Batch downloads, cache file metadata, use exponential backoff

**Risk 2:** OAuth token expiration requires manual re-auth
- **Mitigation:** Use service account instead (non-expiring credentials)

**Risk 3:** Tournament Organizer uploads file with wrong name
- **Mitigation:** Validation tool shows unmapped matches, suggests fixes

**Risk 4:** Mapping file gets out of sync with Google Drive
- **Mitigation:** Mapping creation tool is idempotent, can re-run safely

## Alternative: Just Use Google Drive Sharing?

**Question:** Can we skip the API and just use GDrive's sharing feature?

**Answer:** Yes, with caveats:

```bash
# Each file has a shareable link like:
# https://drive.google.com/file/d/FILE_ID/view

# We can download via direct link:
curl -L "https://drive.google.com/uc?export=download&id=FILE_ID" -o output.zip

# But we still need the mapping:
{
    "12345": {"gdrive_file_id": "1abc...", "filename": "..."}
}
```

**Pros:**
- ✅ No OAuth complexity
- ✅ Simple `curl` or `urllib` downloads

**Cons:**
- ⚠️ Still need manual mapping (same work as Option 2)
- ⚠️ Can't auto-discover new files
- ⚠️ Folder sharing link shows all files, but can't programmatically list them

**Verdict:** This simplifies auth but doesn't eliminate the core challenge (mapping). Could be good starting point.

## Decision Framework

**Choose Option 2 (Hybrid) if:**
- ✅ Tournament uses Challonge for bracket management
- ✅ You want to preserve bracket context and participant linking
- ✅ You're willing to invest ~10 hours in setup
- ✅ Only a subset of files are oversized

**Choose Option 1 (GDrive Only) if:**
- ❌ You don't care about tournament context
- ❌ You're analyzing individual matches, not tournament progression
- ❌ You have a different bracket system (not Challonge)

**Choose Option 3 (Mapping Service) if:**
- ❌ Tournament has 100+ matches (not current situation)
- ❌ Files are uploaded continuously (not in batches)
- ❌ You want to minimize manual work (at cost of complexity)

**Choose Option 4 (Dual Upload) if:**
- ⏸️ You need a quick fix this week (temporary solution)
- ⏸️ You're evaluating whether to fully migrate
- ⏸️ Most files are under size limit

## Recommended Next Steps

1. **Validate assumptions** - Check Google Drive folder structure
   - Are filenames consistent?
   - Do they contain match IDs?
   - How many files are we talking about?

2. **Prototype mapping** - Write script to parse GDrive folder
   - Use folder sharing link + manual file ID extraction
   - Generate mapping JSON for existing files
   - Validate against Challonge API (do match IDs exist?)

3. **Test download** - Try downloading one file via direct link
   - Verify file integrity
   - Confirm import_attachments.py works unchanged

4. **Implement Option 2 incrementally:**
   - Phase 1: Manual mapping file + modified download script
   - Phase 2: Automated mapping tool
   - Phase 3: Validation and monitoring tools

5. **Document for Tournament Organizer:**
   - How to upload files to Google Drive
   - Naming conventions that enable auto-mapping
   - How to notify us of new files

## Open Questions

1. **Google Drive folder structure:**
   - Is it flat or nested by round?
   - Are there non-save files in the folder?

2. **File naming conventions:**
   - Do current filenames contain match IDs?
   - Who controls the naming (TO or players)?

3. **Frequency of updates:**
   - Are files uploaded in batches (once per round)?
   - Or continuously (as matches complete)?

4. **Access control:**
   - Do we need write access or read-only?
   - Service account or OAuth user credentials?

5. **Challonge attachments going forward:**
   - Should TOs stop uploading to Challonge entirely?
   - Or keep uploading small files there?

## Appendix: Google Drive API Reference

### Required Scopes
```python
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
```

### Authentication (Service Account)
```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

credentials = service_account.Credentials.from_service_account_file(
    'credentials.json',
    scopes=SCOPES
)
service = build('drive', 'v3', credentials=credentials)
```

### List Files in Folder
```python
results = service.files().list(
    q=f"'{FOLDER_ID}' in parents",
    fields="files(id, name, size, createdTime)"
).execute()

files = results.get('files', [])
```

### Download File
```python
from googleapiclient.http import MediaIoBaseDownload
import io

request = service.files().get_media(fileId=file_id)
fh = io.BytesIO()
downloader = MediaIoBaseDownload(fh, request)

done = False
while not done:
    status, done = downloader.next_chunk()
    print(f"Download {int(status.progress() * 100)}%")

with open('output.zip', 'wb') as f:
    f.write(fh.getvalue())
```

### Rate Limits
- 1000 requests/100 seconds per user
- 10 requests/second per user (burst)

Use exponential backoff for retries.
