# Old World Save File Analysis

## Save File Overview: AssyriaTurn56.zip

**File Details:**
- Size: 1.4 MB (1,437,159 bytes)
- Created: October 6, 2025
- Contains: AssyriaTurn56.xml (6,320,196 bytes uncompressed)
- Total lines: 171,453

## Game Information

**Basic Settings:**
- Date: September 9, 2025
- Turn: 56
- Map: Small continent (66 width, latitudes 20-50)
- Game Mode: Single player
- Difficulty: Magnificent (player) vs Strong AI
- Turn Style: Strict turns
- Version: 1.0.79513

**Game Configuration:**
- Advanced development with moderate advantage
- Raging tribes difficulty
- Standard mortality and yearly turn scale
- Moderate event level
- Absolute cognatic primogeniture succession

**Active Content/DLCs:**
- Base game
- Pharaohs expansion
- Wonders & Dynasties
- Various event packs (Religion, Scandal, Calamities)
- Nation content (Hittites, Aksum)

## Nations and Current Laws

### Assyria (Player - Ashurbanipal Dynasty)
- **Order:** Primogeniture 
- **Exploration:** Exploration
- **Slavery/Freedom:** Slavery
- **Centralization/Vassalage:** Centralization
- **Tyranny/Constitution:** Tyranny
- **Divine Rule/Legal Code:** Divine Rule

### Egypt (AI - Hatshepsut Dynasty)
- **Order:** Primogeniture
- **Slavery/Freedom:** Freedom
- **Centralization/Vassalage:** Vassalage
- **Colonies/Serfdom:** Colonies

### Carthage (AI - Dido Dynasty)
- **Order:** Primogeniture
- **Slavery/Freedom:** Freedom  
- **Centralization/Vassalage:** Centralization
- **Colonies/Serfdom:** Colonies
- **Monotheism/Polytheism:** Monotheism
- **Divine Rule/Legal Code:** Divine Rule

### Aksum (AI - Kaleb Dynasty)
- **Order:** Primogeniture
- **Exploration:** Epics
- **Slavery/Freedom:** Freedom
- **Centralization/Vassalage:** Centralization  
- **Tyranny/Constitution:** Tyranny
- **Colonies/Serfdom:** Colonies

## Turn History Examples

### Event Stories by Turn
- **Turn 3:** War Ambassador event
- **Turn 9:** Border Dispute and Political Prisoner contact events, High Water calamity
- **Turn 16:** Tribe declared war
- **Turn 17:** Ruins Burly Smith event
- **Turn 21:** Player declared war
- **Turn 27:** Sharing the Loot event
- **Turn 29:** A Flirtation event
- **Turn 44:** Momentous Meeting contact event
- **Turn 46:** Lethal Affliction contact event
- **Turn 48:** Calamities "Do I Have the Gift" event

### Character Events
- **Galsuintha the Vandal:** Born turn -20, died turn 33 from severe illness
- **Canute the Dane:** Born turn -19, still alive
- Various other characters with birth/death dates tracked

### Military Activity
- Wars started on turns 16 (tribe) and 21 (player declaration)
- Unit production: 5 settlers, 10 workers, 3 slingers produced over the game

## XML Structure Analysis

The save file contains comprehensive game state data including:

**Major Sections:**
- Game settings and content configuration
- 4 Players (1 human + 3 AI)
- Multiple Tribes
- Complete map data with all tiles
- Turn-by-turn history logs

**Key Data Categories:**
- Player statistics and relationships
- Economic data (yields, resources, stockpiles)
- Technology research progress
- Military unit positions and status
- Character traits, relationships, and life events
- Event history and story progression
- Law adoption and political changes
- Religious conversions and founding
- City development and improvements

## Potential Analytics Across Multiple Save Files

### Strategic Analysis
- **Law adoption patterns** - Which laws are most commonly chosen by turn X? Success rates of different legal combinations
- **Technology progression paths** - Compare tech trees, identify optimal research orders, bottlenecks
- **Victory condition tracking** - Which strategies lead to wins most often?
- **Difficulty scaling** - How do playstyles change across difficulty levels?

### Character & Dynasty Analytics
- **Trait inheritance patterns** - Which traits appear most in successful dynasties?
- **Marriage network analysis** - Diplomatic relationship patterns through royal marriages
- **Character lifespans** - Death causes, age distributions, succession stability
- **Leadership effectiveness** - Correlate ruler traits with empire performance

### Economic & Military Insights
- **Resource optimization** - Identify most valuable luxury goods, trade routes
- **Unit composition effectiveness** - Army compositions that win wars
- **City development patterns** - Growth trajectories, specialization strategies
- **War outcome prediction** - Military strength vs actual battle results

### Meta-Game Patterns
- **Player learning curves** - How strategies evolve across multiple games
- **Map type performance** - Which civs excel on different terrain types
- **Turn timing analysis** - When do critical events typically occur?
- **RNG impact assessment** - How much does randomness affect outcomes?

### Comparative Civilization Analysis
- **Civ tier rankings** - Win rates, average scores by civilization
- **Unique ability effectiveness** - Measure impact of civ-specific bonuses
- **Diplomatic relationship networks** - Alliance patterns, betrayal frequencies

## Technical Notes

The XML structure is highly parseable and contains:
- Hierarchical organization with clear element names
- Consistent naming conventions (e.g., NATION_, LAW_, TECH_ prefixes)
- Comprehensive turn-by-turn logging
- Rich character and relationship data
- Complete economic and military state information

This makes the save files excellent candidates for building comprehensive Old World strategy databases and analytical tools.