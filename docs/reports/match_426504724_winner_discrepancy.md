# Match 426504724 Winner Discrepancy Analysis

**Report Date:** October 14, 2025
**Match ID (Internal):** 4
**Challonge Match ID:** 426504724
**Save File:** `match_426504724_moose-mongreleyes.zip`
**Issue:** Winner recorded in save file does not match Challonge tournament result

---

## Executive Summary

Our parser correctly identified **MongrelEyes** as the winner of match_id 4 based on the save file data. However, the official Challonge tournament page shows **ThePurpleBullMoose (PBM)** won this match 1-0.

**Conclusion:** The save file uploaded to Challonge contains incorrect game data. This is a data quality issue, not a parser bug.

---

## Background

### Tournament Context

- **Match:** ThePurpleBullMoose vs MongrelEyes
- **Official Result (Challonge):** ThePurpleBullMoose won 1-0
- **Date:** September 14, 2025

### Files Available

Two save files were attached to this Challonge match:

1. **`match_426504724_moose-mongreleyes.zip`** (141,816 bytes)
   - Has TeamVictoriesCompleted data
   - NOT an autosave
   - **Selected by deduplication logic** (correct choice based on our criteria)

2. **`match_426504724_OW-Save-Auto-Game270134180-7-Player2.zip`** (126,372 bytes)
   - NO TeamVictoriesCompleted data
   - IS an autosave
   - Skipped by deduplication

Our deduplication logic correctly selected file #1 because:
- It has victory data (higher priority)
- It's not an autosave (manual saves are more reliable)
- It's larger (likely more complete)

---

## XML Analysis

This section provides detailed XML evidence showing how we determined MongrelEyes won.

### 1. Save File Metadata

```xml
<Root
  SaveDate="14 September 2025"
  GameName="Game270134180"
  GameId="52860559-e713-4c4b-8527-d84f41550202"
  Version="Version: 1.0.79513"
  MapSize="MAPSIZE_SMALLEST"
  GameMode="NETWORK"
  TurnStyle="TURNSTYLE_TIGHT"
  TurnTimer="TURNTIMER_SLOW"
  ...>
```

**Key Points:**
- This is a network multiplayer game
- Completed on turn 47
- Game ID: 52860559-e713-4c4b-8527-d84f41550202

### 2. Player Definitions

The XML contains two `<Player>` elements at the root level, indexed by ID starting at 0:

```xml
<Player
  ID="0"
  Name="PBM"
  Email=""
  OnlineID="76561198047346110"
  Language="LANGUAGE_ENGLISH"
  Nation="NATION_GREECE"
  Dynasty="DYNASTY_PHILIP"
  AIControlledToTurn="2147483647"
  ...>
```

```xml
<Player
  ID="1"
  Name="MongrelEyes"
  Email=""
  OnlineID="76561198203038932"
  Language="LANGUAGE_ENGLISH"
  Nation="NATION_AKSUM"
  Dynasty="DYNASTY_KALEB"
  AIControlledToTurn="0"
  ...>
```

**Key Points:**
- **Player ID 0**: PBM playing as Greece
- **Player ID 1**: MongrelEyes playing as Aksum
- Steam IDs confirm these are the correct players

### 3. Team Assignments

The `<Team>` section maps players to teams using `<PlayerTeam>` elements:

```xml
<Team>
  <PlayerTeam>0</PlayerTeam>
  <PlayerTeam>1</PlayerTeam>
</Team>
```

**How to read this:**
- The first `<PlayerTeam>` element corresponds to Player ID 0
- The second `<PlayerTeam>` element corresponds to Player ID 1
- The **text content** indicates which team the player is on

**Therefore:**
- **Player 0 (PBM)** → **Team 0**
- **Player 1 (MongrelEyes)** → **Team 1**

**Implementation in parser** (`tournament_visualizer/data/parser.py:663-673`):

```python
# Find which player is on the winning team
# PlayerTeam elements are indexed by player ID
player_teams = self.root.findall(".//Team/PlayerTeam")
for player_idx, team_elem in enumerate(player_teams):
    team_id = self._safe_int(team_elem.text)
    if team_id == winning_team_id:
        # Return 1-based player ID
        return player_idx + 1
```

This code iterates through `PlayerTeam` elements:
- `player_idx=0` → Reads `<PlayerTeam>0</PlayerTeam>` → team_id = 0
- `player_idx=1` → Reads `<PlayerTeam>1</PlayerTeam>` → team_id = 1

If winning_team_id is 1, then player_idx=1 matches, returning `1 + 1 = 2` (1-based player ID).

### 4. Victory Data

#### TeamVictories (Pending Victories)

```xml
<TeamVictories>
  <Team Victory="VICTORY_CONQUEST">1</Team>
</TeamVictories>
```

#### TeamVictoriesCompleted (Confirmed Victories)

```xml
<TeamVictoriesCompleted>
  <Team Victory="VICTORY_CONQUEST">1</Team>
</TeamVictoriesCompleted>
```

**Key Points:**
- **Winning Team:** Team 1
- **Victory Type:** VICTORY_CONQUEST
- **What this means:** Team 1 achieved and completed a Conquest Victory

**Combining with team assignments:**
- Team 1 won
- Player 1 (MongrelEyes) is on Team 1
- **Therefore: MongrelEyes won**

### 5. In-Game Victory Logs

The save file contains multiple log messages confirming the victory:

```xml
<LogData>
  <Text>&lt;color=#e3c08c&gt;&lt;link="HELP_LINK,HELP_SELECT_PLAYER,1"&gt;&lt;color=#C97889&gt;&lt;sprite="Sprites/Crests" name="CREST_NATION_AKSUM" tint&gt;&lt;/color&gt; &lt;color=#C97889&gt;Aksum (MongrelEyes)&lt;/color&gt;&lt;/link&gt;&lt;/color&gt; has met the conditions for &lt;color=#e3c08c&gt;&lt;link="HELP_LINK,HELP_VICTORY_TYPE,VICTORY_CONQUEST"&gt;a Conquest Victory&lt;/link&gt;&lt;/color&gt;!</Text>
  <Type>MISC</Type>
</LogData>
```

**Decoded for readability:**
```
"Aksum (MongrelEyes) has met the conditions for a Conquest Victory!"
```

This message appears multiple times in:
- Player turn summaries (both players see this message)
- Event logs
- Achievement records

### 6. Event Story Victory

The game records which player triggered the victory event:

```xml
<EVENTSTORY_VICTORY_CONQUEST>47</EVENTSTORY_VICTORY_CONQUEST>
<P.1.EVENTSTORY_VICTORY_CONQUEST>47</P.1.EVENTSTORY_VICTORY_CONQUEST>
```

**Key Points:**
- The `P.1.` prefix indicates this is Player 1's event story
- Player 1 (MongrelEyes) triggered the Conquest Victory event on turn 47

### 7. Active Player at Save Time

```xml
<?ActivePlayer 0?>
```

```xml
<PlayerTurn>1</PlayerTurn>
```

**Key Points:**
- The save was created from Player 0's (PBM's) perspective
- It was Player 1's (MongrelEyes') turn
- This explains the filename `moose-mongreleyes.zip` - it's PBM's save showing MongrelEyes won

---

## Database State

### Match Record

```
match_id:           4
file_name:          match_426504724_moose-mongreleyes.zip
save_date:          2025-09-14 00:00:00
total_turns:        47
challonge_match_id: NULL
```

**Note:** The `challonge_match_id` is NULL because we extract it from the filename, not from Challonge API data.

### Player Records

```
player_id: 7
player_name: PBM
civilization: Greece
team_id: NULL
final_score: 0

player_id: 8
player_name: MongrelEyes
civilization: Aksum
team_id: NULL
final_score: 0
```

**Note:** `team_id` is NULL because we don't currently store the team assignment from the XML in the database. Both players have `final_score: 0` because Old World doesn't use a traditional score system - victory is binary (win/lose).

### Match Winner Record

```
winner_player_id:            8
winner_name:                 MongrelEyes
winner_determination_method: parser_determined
determined_at:               2025-10-14 10:50:31
```

**Key Points:**
- Our parser determined player_id 8 (MongrelEyes) won
- This was determined from the `TeamVictoriesCompleted` XML data
- Timestamp shows when we last imported this data

---

## The Discrepancy

### What Challonge Says

From the Challonge match page (https://challonge.com/tournaments/[tournament]/matches/426504724):

```
ThePurpleBullMoose    1
MongrelEyes           0

Winner: ThePurpleBullMoose
```

### What the Save File Says

```
Team 1 won via VICTORY_CONQUEST
Player 1 (MongrelEyes) is on Team 1
Winner: MongrelEyes
```

### Contradiction

**Official tournament result:** ThePurpleBullMoose (PBM) won
**Save file data:** MongrelEyes won

---

## Possible Explanations

### 1. Wrong Save File Uploaded

The most likely explanation is that the wrong save file was uploaded to Challonge. Possibilities:

- **Practice game save**: This might be from a practice match between these players
- **Different tournament match**: Could be from a different stage of the tournament
- **Re-match save**: They might have played multiple games

### 2. Save From Wrong Player

Old World allows any player to save the game. PBM might have:
- Saved the game before the final outcome
- Uploaded an older save by mistake
- Saved a game where MongrelEyes won but the match was conceded/replayed

However, this seems unlikely because:
- The save has `TeamVictoriesCompleted` (game is finished)
- The victory event was triggered on turn 47
- Multiple log entries confirm MongrelEyes' victory

### 3. Concession or Manual Override

Possible tournament scenarios:

- MongrelEyes won the game but conceded the match for meta-game reasons
- Technical issues required a rematch
- Tournament organizer manually adjusted the result
- Players agreed to a different outcome

### 4. Game Bug

Unlikely, but possible:
- Old World recorded the wrong winner in the save file
- XML corruption during save/upload

---

## Parser Logic Validation

Let's verify our parser is working correctly by tracing through the code:

### Step 1: Extract TeamVictoriesCompleted

From `tournament_visualizer/data/parser.py:654-660`:

```python
team_victories = self.root.find(".//TeamVictoriesCompleted")
if team_victories is not None:
    # Get the first team that achieved victory
    team_elem = team_victories.find(".//Team")
    if team_elem is not None and team_elem.text:
        winning_team_id = self._safe_int(team_elem.text)
```

**For our file:**
- `team_victories` finds `<TeamVictoriesCompleted>`
- `team_elem` finds `<Team Victory="VICTORY_CONQUEST">1</Team>`
- `team_elem.text` is `"1"`
- `winning_team_id = 1`

### Step 2: Find Player on Winning Team

From `tournament_visualizer/data/parser.py:663-673`:

```python
# Find which player is on the winning team
# PlayerTeam elements are indexed by player ID
player_teams = self.root.findall(".//Team/PlayerTeam")
for player_idx, team_elem in enumerate(player_teams):
    team_id = self._safe_int(team_elem.text)
    if team_id == winning_team_id:
        # Return 1-based player ID
        return player_idx + 1
```

**For our file:**
- `player_teams` finds `[<PlayerTeam>0</PlayerTeam>, <PlayerTeam>1</PlayerTeam>]`
- Iteration 0: player_idx=0, team_id=0, 0 != 1, continue
- Iteration 1: player_idx=1, team_id=1, 1 == 1, **match!**
- Return `1 + 1 = 2` (1-based player ID)

### Step 3: Map to Database

From `tournament_visualizer/data/etl.py:127-132`:

```python
# Check if this is the winner
if original_winner_id and original_player_id == original_winner_id:
    winner_db_id = player_id
```

**For our file:**
- `original_winner_id = 2` (from parser)
- When processing Player 1 (MongrelEyes): `original_player_id = 2`
- `2 == 2`, so `winner_db_id = 8` (database player_id for MongrelEyes)

### Conclusion

**The parser logic is correct.** It accurately reads:
1. Team 1 won (from `TeamVictoriesCompleted`)
2. Player 1 is on Team 1 (from `PlayerTeam` mappings)
3. Player 1 is MongrelEyes (from `Player` attributes)
4. Therefore MongrelEyes won

---

## Recommendations

### Immediate Actions

1. **Verify with tournament organizer**
   - Confirm who actually won this match
   - Check if there were any special circumstances (concession, rematch, etc.)

2. **Request correct save file**
   - If PBM won, ask them to upload their save file
   - The correct save should show Team 0 winning

3. **Document the issue**
   - Note this discrepancy in tournament records
   - Check other matches for similar issues

### Data Quality Improvements

1. **Implement Challonge cross-reference**
   - During import, fetch match results from Challonge API
   - Compare parser-determined winner with Challonge winner
   - Flag mismatches for manual review

2. **Add validation warnings**
   - Warn when save file winner doesn't match filename pattern
   - Alert on matches without victory data
   - Report matches with multiple conflicting saves

3. **Manual override capability**
   - Add script to manually set winner for specific matches
   - Log all manual overrides with reason
   - Preserve original parser determination for audit trail

### Code Example: Manual Override Script

```python
# scripts/override_match_winner.py
import sys
from tournament_visualizer.data.database import get_database

def override_winner(match_id: int, player_name: str, reason: str) -> None:
    """Manually override the winner for a match."""
    db = get_database()

    # Find player_id by name
    player_id = db.fetch_one(
        "SELECT player_id FROM players WHERE match_id = ? AND player_name = ?",
        (match_id, player_name)
    )[0]

    # Update match_winners table
    db.execute_query("""
        UPDATE match_winners
        SET winner_player_id = ?,
            winner_determination_method = 'manual_override',
            override_reason = ?
        WHERE match_id = ?
    """, (player_id, reason, match_id))

    print(f"✅ Updated match {match_id} winner to {player_name}")
    print(f"   Reason: {reason}")

# Usage:
# override_winner(4, "PBM", "Challonge shows PBM won; save file data incorrect")
```

---

## Appendix: Full XML Extraction Commands

For future reference, here are the commands used to extract this data:

```bash
# Extract save file
unzip -p saves/match_426504724_moose-mongreleyes.zip > match.xml

# Find Player elements
grep -A 10 '<Player$' match.xml | head -50

# Find Team assignments
grep -A 5 '<Team>' match.xml | head -10

# Find victory data
grep -A 3 'TeamVictoriesCompleted' match.xml

# Find victory logs
grep 'Conquest Victory' match.xml

# Parse with Python
python3 << 'EOF'
import xml.etree.ElementTree as ET
tree = ET.parse('match.xml')
root = tree.getroot()
# ... analysis code ...
EOF
```

---

## Conclusion

Our parser correctly determined that **MongrelEyes won** based on the save file data. However, this conflicts with the official Challonge result showing **ThePurpleBullMoose won**.

**This is not a parser bug - it's a data quality issue.** The save file uploaded to Challonge contains incorrect or mismatched game data.

To resolve this, we need to either:
1. Obtain the correct save file showing PBM's victory
2. Manually override the winner in our database based on Challonge's official result
3. Remove this match from our dataset until the discrepancy is resolved

**Recommended action:** Contact tournament organizer and players to determine the source of truth, then either replace the save file or implement a manual override with documentation.
