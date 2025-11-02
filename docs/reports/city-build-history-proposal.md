# City Build History Tracking Proposal for Old World

**Date:** October 30, 2025 (Updated)
**Author:** Claude Code Analysis
**Status:** Proposal for Review - Updated with military unit tracking clarification

## Executive Summary

This document proposes adding comprehensive build history tracking to Old World's save file system. The feature would record every building, unit, specialist, and project completed by each city, along with contextual metadata like turn number, costs, and build conditions.

**Key Findings:**
- **Recommended Approach:** Per-city comprehensive build history storage
- **Critical Discoveries - Major tracking gaps in current system:**
  - Military units: NOT tracked at city level (only settlers, workers, disciples)
  - Specialists: Only total count tracked, no per-type breakdown or history
- **This proposal fixes both gaps:** ALL units (military + civilian) and specialist types will be tracked with full detail
- **File Size Impact:** +150-200 KB compressed for marathon games (~5-8% increase)
- **Implementation Complexity:** Low - follows existing serialization patterns
- **Value:** High - enables analytics, debugging, and future features

---

## Current State Analysis

### Existing Build Tracking in Save Files

Based on review of `City.cs` (lines 1129-1478), the current save system tracks:

#### 1. BuildQueue (lines 1456-1466)
- Current and queued builds only
- Uses `CityQueueData` structure
- No historical data

#### 2. CompletedBuild (lines 1468-1476)
- **Only the last completed build**
- Single `CityQueueData` object
- **No turn number recorded**
- Overwritten on each new completion

#### 3. Build Counters (lines 1273-1298)
- `UnitProductionCounts`: Total count per unit type
- `ProjectCount`: Total count per project type
- `SpecialistProducedCount`: Single total count (line 1199-1201)
- Simple aggregates, no historical detail
- **CRITICAL LIMITATIONS:**
  - `UnitProductionCounts` only tracks units with `miProductionCity != 0` (see line 8448-8450)
    - Only tracks: Settlers, Workers, and religious Disciples
    - **Does NOT track military units** (warriors, archers, cavalry, etc.)
  - `SpecialistProducedCount` is a **single total** (not per-type)
    - No breakdown by specialist type (farmer, miner, priest, etc.)
    - No historical record of when/where specialists were built

### CityQueueData Structure (CityQueueData.cs)

Current structure includes:
```csharp
public class CityQueueData
{
    public BuildType meBuild;      // UNIT_BUILD, PROJECT_BUILD, SPECIALIST_BUILD
    public int miType;              // Specific type ID
    public int miData;              // Additional data (e.g., spawn location)
    public int miProgress;          // Current progress
    public bool mbRepeat;           // Repeat flag
    public bool mbHurried;          // Was rushed/hurried
    public bool mbAutobuild;        // Auto-queued
    public DictionaryList<YieldType, int> mdYieldCosts;  // Cost breakdown
}
```

**Critical Gap:** No turn tracking, no historical persistence beyond last build.

### Important Discovery: Major Tracking Gaps

#### Gap 1: Military Units Not Tracked

**Code Analysis:** `City.cs:8448-8450`
```csharp
if (infos().unit(eUnit).miProductionCity != 0)
{
    incrementUnitProductionCount(eUnit);
}
```

The existing `UnitProductionCounts` system only records units where `miProductionCity != 0`. Based on analysis of `unit.xml`, only these 6 unit types have this field:

**Tracked Units:**
- `UNIT_SETTLER`
- `UNIT_WORKER`
- `UNIT_ZOROASTRIANISM_DISCIPLE`
- `UNIT_JUDAISM_DISCIPLE`
- `UNIT_CHRISTIANITY_DISCIPLE`
- `UNIT_MANICHAEISM_DISCIPLE`

**NOT Tracked (all military units):**
- Warriors, Spearmen, Axemen
- Archers, Slingers, Crossbowmen
- Cavalry, Chariots, Elephants
- Siege units, Ships
- All other combat units

#### Gap 2: Specialist Details Not Tracked

**Code Analysis:** `City.cs:8432, 1199-1201`
```csharp
incrementSpecialistProducedCount();  // Single counter only
```

The save file only stores `SpecialistProducedCount` - a single integer total.

**What IS tracked:**
- Total number of specialists produced (e.g., "12 specialists")
- Current specialist placement on tiles (in Tile data)

**What is NOT tracked:**
- Which types of specialists were built (farmers vs miners vs priests, etc.)
- When specialists were built (turn numbers)
- Historical specialist production (can only see current state)

**Implication:** The current save file has **no city-level record of military unit production** and **no per-type specialist production history**. These are significant limitations that the build history feature will correct.

### Alternative: Player Turn Summaries

Player.cs (lines 2421-2429) has `TurnSummary` system using `TurnLogData`:
- Generic text-based logging
- Per-player, not per-city
- Designed for UI display, not structured queries
- Less suitable for detailed build history

---

## Requirements

Based on discussion:

1. **Scope:** Track ALL build types (units, buildings, specialists, projects)
2. **History Limit:** Unlimited - no artificial cap
3. **File Size:** Acceptable within reason (~5-10% save file increase)
4. **Querying:** No complex query requirements (simple per-city access sufficient)

---

## Proposed Solution: Comprehensive Build History

### Architecture: Per-City Storage

Store build history as a list within each City entity, following the existing pattern used by `BuildQueue`.

**Rationale:**
- Direct association with city (intuitive data model)
- Reuses existing serialization patterns
- Simple to access (no joins or lookups needed)
- Survives city capture (attributes builds to city location)

### Data Structure

Create new `CityBuildHistoryData` class extending `CityQueueData`:

```csharp
public class CityBuildHistoryData : ICloneable, SimplifyIO.ListMember
{
    // Core build data
    public BuildType meBuild;           // UNIT_BUILD, PROJECT_BUILD, etc.
    public int miType;                  // Specific type ID (UnitType, ProjectType, etc.)
    public int miTurn;                  // Turn completed

    // Build context
    public bool mbHurried;              // Was it rushed?
    public bool mbAutobuild;            // Auto-queued by AI/governor?
    public DictionaryList<YieldType, int> mdYieldCosts;  // Actual costs paid

    // City state at build time
    public int miPopulation;            // City population when built
    public PlayerType mePlayer;         // Owner at completion (tracks captures)
}
```

**Fields Excluded from CityQueueData:**
- `miData` - Only used for unit spawn location (not relevant after completion)
- `miProgress` - Always 100% when completed
- `mbRepeat` - Queue behavior, not relevant to history

**Fields Added:**
- `miTurn` - Critical for temporal analysis
- `miPopulation` - Context for build efficiency
- `mePlayer` - Tracks ownership changes

### XML Serialization Format

```xml
<City ID="5" TileID="1234" Player="0" Founded="1">
  <!-- ... existing city data ... -->

  <BuildHistory>
    <Entry>
      <Build>UNIT_BUILD</Build>
      <Type>UNIT_WARRIOR</Type>
      <Turn>12</Turn>
      <Hurried>true</Hurried>
      <Population>5</Population>
      <Player>0</Player>
      <YieldCosts>
        <YIELD_TRAINING>40</YIELD_TRAINING>
        <YIELD_MONEY>10</YIELD_MONEY>
      </YieldCosts>
    </Entry>
    <Entry>
      <Build>PROJECT_BUILD</Build>
      <Type>PROJECT_MONUMENT</Type>
      <Turn>18</Turn>
      <Population>6</Population>
      <Player>0</Player>
      <YieldCosts>
        <YIELD_CIVICS>50</YIELD_CIVICS>
      </YieldCosts>
    </Entry>
    <!-- ... more entries ... -->
  </BuildHistory>

  <!-- ... existing CompletedBuild, etc. ... -->
</City>
```

### Integration Points

#### 1. City.cs Data Structure

Add to `City.Data` class (around line 192):
```csharp
public List<CityBuildHistoryData> maBuildHistory;
```

Initialize in constructor (around line 320):
```csharp
maBuildHistory = new List<CityBuildHistoryData>();
```

#### 2. Serialization (City.cs writeGameXML)

Add after `CompletedBuild` section (after line 1476):
```csharp
if (getBuildHistory().Count > 0)
{
    pWriter.WriteStartElement("BuildHistory");

    foreach (CityBuildHistoryData entry in getBuildHistory())
    {
        entry.writeXML(pWriter, infos());
    }

    pWriter.WriteEndElement();
}
```

#### 3. Deserialization (City.cs readGameXML)

Add in XML reading loop (around line 1850):
```csharp
else if (pChildNode.Name == "BuildHistory")
{
    foreach (XmlNode pEntryNode in pChildNode.ChildNodes)
    {
        CityBuildHistoryData entry = new CityBuildHistoryData();
        entry.readXML(pEntryNode, infos());
        addBuildHistory(entry);
    }
}
```

#### 4. Build Completion Hook (City.cs)

Modify build completion logic (around line 8440-8458) in the `UNIT_BUILD` section:
```csharp
else if (pCurrentBuild.meBuild == infos().Globals.UNIT_BUILD)
{
    UnitType eUnit = (UnitType)(pCurrentBuild.miType);

    changeCitizensQueue(-(infos().unit(eUnit).miPopulationCost));

    Unit pUnit = createBuildUnit(eUnit, game().tile(pCurrentBuild.miData));

    // ADD BUILD HISTORY ENTRY FOR ALL UNITS (not just those with miProductionCity)
    CityBuildHistoryData historyEntry = new CityBuildHistoryData(
        pCurrentBuild.meBuild,
        pCurrentBuild.miType,
        game().getTurn(),
        pCurrentBuild.mbHurried,
        pCurrentBuild.mbAutobuild,
        pCurrentBuild.mdYieldCosts,
        getPopulation(),
        getPlayer()
    );
    addBuildHistory(historyEntry);

    // Existing production count tracking (only for civilian units)
    if (infos().unit(eUnit).miProductionCity != 0)
    {
        incrementUnitProductionCount(eUnit);
    }

    player().incrementUnitsProduced(eUnit);
    // ... rest of existing code
}
```

**CRITICAL:** The build history entry must be added **BEFORE** the `miProductionCity` check, ensuring ALL units (military and civilian) are recorded in the history, while preserving the existing behavior of `UnitProductionCounts` which only tracks civilian units.

Similar hooks needed for:
- Project completion (around line 8412-8419)
- Specialist completion (around line 8420-8438)

---

## File Size Impact Analysis

### Per-Entry Size

**Comprehensive format:** ~250-350 bytes per entry (XML)
- Build type: ~40 bytes
- Type ID: ~40 bytes
- Turn: ~20 bytes
- Flags: ~30 bytes each
- Population: ~25 bytes
- Player: ~20 bytes
- Yield costs: ~50-150 bytes (varies by number of yields)

**With typical 2 yield costs:** ~300 bytes average

### Build Rate Estimates

Based on Old World game mechanics:
- **Early game (turns 1-50):** ~1 build per 6-8 turns per city
- **Mid game (turns 51-150):** ~1 build per 4-5 turns per city
- **Late game (turns 151+):** ~1 build per 2-3 turns per city
- **Average:** ~1 build per 4-5 turns per city

### Scenario Calculations

| Scenario | Turns | Cities | Builds/City | Raw Size | Compressed* |
|----------|-------|--------|-------------|----------|-------------|
| **Typical Game** | 200 | 12 | 45 | 162 KB | ~30 KB |
| **Large Map** | 350 | 20 | 75 | 450 KB | ~70 KB |
| **Marathon Game** | 600 | 25 | 135 | 1.0 MB | ~150 KB |

*Estimated 5:1 to 7:1 compression ratio for repetitive XML data

### Percentage Impact on Save Files

Current Old World save files:
- **Uncompressed:** 1-5 MB (varies by game stage)
- **Compressed:** 200 KB - 1 MB

Impact percentages:

| Scenario | Uncompressed Impact | Compressed Impact |
|----------|---------------------|-------------------|
| Typical 200-turn | +8-16% | +2-4% |
| Large 350-turn | +15-20% | +4-6% |
| Marathon 600-turn | +20-30% | +5-8% |

### Assessment

**Verdict:** Acceptable file size impact
- Typical games: negligible (+30 KB compressed)
- Long games: minor (+70 KB compressed)
- Marathon games: noticeable but reasonable (+150 KB compressed)
- Compression makes the feature nearly free in practice
- Players concerned about size can use existing compression option

---

## Benefits and Use Cases

### 1. Analytics and Statistics
- Track total units/buildings produced per city
- Analyze build efficiency over time
- Compare city productivity
- Economic analysis (total resources spent)

### 2. Victory Conditions and Achievements
- Verify "built X units" conditions
- Track milestone builds
- Achievement validation ("Never rushed a build")

### 3. Debugging and Balance
- Identify problematic build chains
- Analyze cost effectiveness
- Track balance changes across game versions
- Reproduce bug scenarios

### 4. AI Analysis
- Study player vs AI build patterns
- Optimize AI build strategies
- Validate AI governor performance

### 5. Multiplayer Attribution
- Track which player built what (after city captures)
- Conflict resolution
- Post-game analysis

### 6. Future Features
- City production graphs/charts
- "Greatest builds" hall of fame
- Replay annotations
- Modding support for custom analytics

### 7. Scenario Design
- Verify scenario build requirements
- Track mission objectives
- Validate scripted events

---

## Implementation Checklist

### Phase 1: Data Structure (New Files)
- [ ] Create `CityBuildHistoryData.cs` class
- [ ] Implement `writeXML()` method
- [ ] Implement `readXML()` method
- [ ] Implement `Clone()` for dirty tracking
- [ ] Implement `Data()` for binary serialization

### Phase 2: City Integration (City.cs)
- [ ] Add `maBuildHistory` field to `City.Data`
- [ ] Add `getBuildHistory()` accessor
- [ ] Add `addBuildHistory()` method
- [ ] Add serialization in `writeGameXML()`
- [ ] Add deserialization in `readGameXML()`

### Phase 3: Build Completion Hooks
- [ ] Hook unit completion (around line 8445) **BEFORE the `miProductionCity` check**
  - **CRITICAL:** Must record ALL units, not just civilian units
  - Place `addBuildHistory()` call before `if (infos().unit(eUnit).miProductionCity != 0)`
  - This ensures military units are captured in history
- [ ] Hook project completion (around line 8483)
- [ ] Hook specialist completion (around line 8420)
- [ ] Ensure all build types covered
- [ ] Verify military units appear in test histories

### Phase 4: Testing
- [ ] Test save/load consistency
- [ ] Test with existing saves (backward compatibility)
- [ ] Test file size with various scenarios
- [ ] Test compression effectiveness
- [ ] Test across game captures/ownership changes

### Phase 5: Optional Enhancements
- [ ] Add dirty tracking for network sync (if needed)
- [ ] Add UI to view build history
- [ ] Add statistics screen
- [ ] Add export functionality

---

## Alternative Approaches Considered

### Alternative 1: Minimal Format
Store only essential data (BuildType, Type ID, Turn):
- **Pros:** Smaller files (~80 bytes per entry, ~25 KB compressed for typical game)
- **Cons:** Missing valuable context (costs, hurry status, population)
- **Verdict:** Rejected - file size savings minimal, context valuable

### Alternative 2: Player-Level Storage
Store all build history under Player instead of City:
- **Pros:** Centralized, easier for player-wide queries
- **Cons:** Less intuitive, harder to track city-specific production, complicates city captures
- **Verdict:** Rejected - per-city is more natural

### Alternative 3: Hybrid Approach
Keep detailed history for recent builds (last 20), minimal for older builds:
- **Pros:** Balances detail with size
- **Cons:** Arbitrary cutoff, complexity, inconsistent data
- **Verdict:** Rejected - unnecessary optimization given acceptable file sizes

### Alternative 4: Optional Feature
Add game setting to enable/disable history tracking:
- **Pros:** Players can opt out if concerned about file size
- **Cons:** Fragmented data, testing complexity, user confusion
- **Verdict:** Rejected - file size acceptable without this complexity

---

## Backward Compatibility

### Loading Old Saves
- Old saves without `<BuildHistory>` will load normally
- Cities will have empty build history list
- No migration needed

### Saving to Old Format
- If needed, can omit `<BuildHistory>` section conditionally
- Existing `CompletedBuild` remains unchanged
- Build counters remain unchanged

### Version Detection
Consider adding version marker if needed:
```xml
<City BuildHistoryVersion="1">
```

---

## Performance Considerations

### Memory Usage
- **Per entry:** ~100 bytes in memory (C# object overhead)
- **Typical game:** 12 cities × 45 builds × 100 bytes = 54 KB
- **Marathon game:** 25 cities × 135 builds × 100 bytes = 337 KB
- **Assessment:** Negligible compared to game's total memory footprint

### CPU Impact
- **Save time:** Negligible - linear write, already serializing similar data
- **Load time:** Negligible - linear read, parallel to existing city loading
- **Runtime:** Zero - history is append-only during builds

### Network Sync (Multiplayer)
- Build history is **not** dirty-tracked (doesn't need real-time sync)
- Only written to save files
- No network overhead

---

## Recommendations

### Primary Recommendation: Comprehensive Format ✅

Implement the comprehensive `CityBuildHistoryData` structure with:
- Full build details (type, costs, flags)
- Turn number
- Population at build time
- Player ownership

**Rationale:**
1. File size impact is acceptable (5-8% compressed for long games)
2. Rich data enables valuable future features
3. Can't retroactively add this data - capture it now
4. Follows Old World's design philosophy (rich simulation over minimal saves)
5. Consistent with existing serialization patterns
6. Modern storage makes this a non-issue

### Implementation Priority: Medium-High

Not critical for core gameplay, but:
- Easy to implement (follows existing patterns)
- High value for debugging and analytics
- Foundation for future features
- Better to add early (can't recover historical data later)

### Phased Rollout

1. **Phase 1:** Implement data capture and serialization (invisible to players)
2. **Phase 2:** Add basic UI to view city build history
3. **Phase 3:** Add statistics and analytics features
4. **Phase 4:** Enable modding API for custom analytics

---

## Questions for Implementation

### Design Decisions

1. **Should build history survive city razing?**
   - Current recommendation: No - history tied to city instance
   - Alternative: Transfer to player/global history

2. **Should we track failed/cancelled builds?**
   - Current recommendation: No - only completed builds
   - Would require queue monitoring, much more complex

3. **Should we expose build history via UI?**
   - Current recommendation: Yes, in Phase 2
   - Simple chronological list in city screen

4. **Should we track rebuild information?**
   - Example: Same unit built multiple times in a row
   - Current recommendation: Each build is separate entry

### Technical Details

1. **Dirty tracking needed?**
   - Build history doesn't need network sync
   - Only persisted in saves
   - Recommend: No dirty tracking

2. **List growth strategy?**
   - Start with standard List<T>
   - Consider DictionaryList if needed for performance
   - Unlikely to need optimization (appends only)

3. **XML element naming?**
   - Proposed: `<BuildHistory>` with `<Entry>` children
   - Alternative: `<HistoricalBuilds>`, `<ProductionHistory>`
   - Recommend: `BuildHistory` for consistency with `BuildQueue`

---

## Conclusion

Adding comprehensive build history to Old World's save system is a **high-value, low-risk enhancement**. The feature:

- **Enables valuable analytics** for players, developers, and modders
- **Follows established patterns** in the existing codebase
- **Has acceptable file size impact** (~5-8% compressed for long games)
- **Is trivial to implement** (few hundred lines of code)
- **Provides foundation** for future features

The comprehensive format is recommended over minimal alternatives because:
1. File size difference is negligible with compression
2. Rich context is valuable for debugging and analysis
3. Data cannot be retroactively added
4. Aligns with Old World's design philosophy

**Recommendation: Proceed with implementation of comprehensive per-city build history.**

---

## Appendix A: Code References

### Key Files for Implementation
- `Source/Base/Game/GameCore/City.cs` - Main city serialization
- `Source/Base/Game/GameCore/CityQueueData.cs` - Build data structure pattern
- `Source/Base/Game/GameCore/Structs.cs` - Data structure examples
- `Source/Base/Game/GameCore/Player.cs` - Player-level serialization patterns

### Key Methods
- `City.cs:1129` - `writeGameXML()` - City serialization entry point
- `City.cs:1480` - `readGameXML()` - City deserialization entry point
- `City.cs:8390` - Build completion logic (unit builds)
- `City.cs:8483` - Build completion logic (project builds)
- `CityQueueData.cs:76` - `writeXML()` - Pattern to follow

### Existing Build Tracking
- `City.cs:1273-1285` - Unit production counts serialization
- `City.cs:1288-1299` - Project counts serialization
- `City.cs:1468-1476` - Completed build (single entry) serialization

---

## Appendix B: Example Output

### Sample Build History XML

**Note:** This example demonstrates that military units (UNIT_WARRIOR, UNIT_SLINGER) are now tracked, unlike the current `UnitProductionCounts` system which only tracks civilian units.

```xml
<City ID="5" TileID="1234" Player="0" Family="FAMILY_NONE" Founded="1">
  <Name>Rome</Name>
  <Citizens>8</Citizens>

  <!-- Existing city data... -->

  <BuildHistory>
    <Entry>
      <Build>UNIT_BUILD</Build>
      <Type>UNIT_WARRIOR</Type> <!-- Military unit - NEW! Not tracked in current system -->
      <Turn>5</Turn>
      <Population>3</Population>
      <Player>0</Player>
      <YieldCosts>
        <YIELD_TRAINING>25</YIELD_TRAINING>
      </YieldCosts>
    </Entry>
    <Entry>
      <Build>UNIT_BUILD</Build>
      <Type>UNIT_SLINGER</Type> <!-- Military unit - NEW! Not tracked in current system -->
      <Turn>8</Turn>
      <Hurried>true</Hurried>
      <Population>4</Population>
      <Player>0</Player>
      <YieldCosts>
        <YIELD_TRAINING>20</YIELD_TRAINING>
        <YIELD_MONEY>15</YIELD_MONEY>
      </YieldCosts>
    </Entry>
    <Entry>
      <Build>PROJECT_BUILD</Build>
      <Type>PROJECT_AMPHITHEATER</Type>
      <Turn>15</Turn>
      <Population>5</Population>
      <Player>0</Player>
      <YieldCosts>
        <YIELD_CIVICS>60</YIELD_CIVICS>
      </YieldCosts>
    </Entry>
    <Entry>
      <Build>SPECIALIST_BUILD</Build>
      <Type>SPECIALIST_FARMER</Type>
      <Turn>20</Turn>
      <Autobuild>true</Autobuild>
      <Population>6</Population>
      <Player>0</Player>
    </Entry>
    <Entry>
      <Build>UNIT_BUILD</Build>
      <Type>UNIT_WARRIOR</Type>
      <Turn>35</Turn>
      <Population>7</Population>
      <Player>1</Player> <!-- City was captured! -->
      <YieldCosts>
        <YIELD_TRAINING>25</YIELD_TRAINING>
      </YieldCosts>
    </Entry>
  </BuildHistory>

  <!-- Existing CompletedBuild, BuildQueue, etc... -->
</City>
```

### Sample Usage in Code

```csharp
// After build completes in City.cs
public void recordCompletedBuild(CityQueueData pBuild)
{
    // Create history entry from completed build
    CityBuildHistoryData historyEntry = new CityBuildHistoryData
    {
        meBuild = pBuild.meBuild,
        miType = pBuild.miType,
        miTurn = game().getTurn(),
        mbHurried = pBuild.mbHurried,
        mbAutobuild = pBuild.mbAutobuild,
        mdYieldCosts = pBuild.mdYieldCosts?.Clone() as DictionaryList<YieldType, int>,
        miPopulation = getPopulation(),
        mePlayer = getPlayer()
    };

    // Add to history list
    mpCurrentData.maBuildHistory.Add(historyEntry);
}

// Query build history
public int countUnitBuilds(UnitType eUnit)
{
    int count = 0;
    foreach (CityBuildHistoryData entry in getBuildHistory())
    {
        if (entry.meBuild == infos().Globals.UNIT_BUILD &&
            entry.miType == (int)eUnit)
        {
            count++;
        }
    }
    return count;
}

// Get builds in turn range
public List<CityBuildHistoryData> getBuildsInTurnRange(int minTurn, int maxTurn)
{
    List<CityBuildHistoryData> results = new List<CityBuildHistoryData>();
    foreach (CityBuildHistoryData entry in getBuildHistory())
    {
        if (entry.miTurn >= minTurn && entry.miTurn <= maxTurn)
        {
            results.Add(entry);
        }
    }
    return results;
}
```

---

**End of Report**
