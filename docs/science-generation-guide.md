# Old World Science Generation - Complete Reference Guide

This document covers all methods of generating science in Old World, including specialists, improvements, modifiers, and how to interpret science values in save files.

---

## Table of Contents

1. [Specialists](#1-specialists)
2. [Improvements](#2-improvements)
3. [City Projects](#3-city-projects)
4. [Character Traits](#4-character-traits)
5. [Family Bonuses](#5-family-bonuses)
6. [Nation Bonuses](#6-nation-bonuses)
7. [Laws](#7-laws)
8. [Religion & Theology](#8-religion--theology)
9. [Steles](#9-steles)
10. [Events](#10-events)
11. [Game Settings & Difficulty](#11-game-settings--difficulty)
12. [Understanding Science in Save Files](#12-understanding-science-in-save-files)
13. [Quick Reference Tables](#13-quick-reference-tables)

---

## 1. Specialists

**All specialists generate science.** Every specialist has two effects:
1. A **tier-based effect** that applies to all specialists at that tier (provides base science)
2. A **specialist-specific effect** that provides their primary yield (some add additional science)

### Base Science from Specialist Tiers

Every specialist generates science based on their tier classification:

| Tier | Effect ID | XML Value | In-Game Display | Specialists |
|------|-----------|-----------|-----------------|-------------|
| **Rural** | `EFFECTCITY_SPECIALIST_RURAL` | 10 | ~1 | Farmer, Miner, Stonecutter, Woodcutter, Rancher, Trapper, Gardener, Fisher |
| **Apprentice** (Tier 1) | `EFFECTCITY_SPECIALIST_APPRENTICE` | 20 | ~2 | All tier 1 urban specialists |
| **Master** (Tier 2) | `EFFECTCITY_SPECIALIST_MASTER` | 30 | ~3 | All tier 2 urban specialists |
| **Elder** (Tier 3) | `EFFECTCITY_SPECIALIST_ELDER` | 40 | ~4 | All tier 3 urban specialists |

> **Note on Display Scaling:** The XML values appear to be ~10x what's shown in-game. A rural specialist shows as ~1 science in-game but has `iValue>10` in the XML. All values in this document are **raw XML values** unless noted otherwise.

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 5401-5439)

### Philosopher (Bonus Science Specialist)

Philosophers get **additional** science on top of their tier-based science:

| Tier | Tier Science | Philosopher Bonus | **Total Science/Turn** | Training Cost |
|------|--------------|-------------------|------------------------|---------------|
| 1 | 20 (Apprentice) | +20 | **40** | 40 food, 40 civics |
| 2 | 30 (Master) | +30 | **60** | 60 food, 60 civics |
| 3 | 40 (Elder) | +40 | **80** | 80 food, 80 civics |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 5287-5315)

### Doctor (Hybrid: Growth + Science)

Doctors primarily generate growth but also provide bonus science at higher tiers (in addition to tier-based science):

| Tier | Tier Science | Doctor Bonus | **Total Science** | Growth/Turn |
|------|--------------|--------------|-------------------|-------------|
| 1 | 20 (Apprentice) | +0 | **20** | 20 |
| 2 | 30 (Master) | +10 | **40** | 30 |
| 3 | 40 (Elder) | +20 | **60** | 40 |

**Note:** Doctor science bonus uses "culture-dependent yield" which may vary based on city culture level.

### Other Urban Specialists (Science from Tier Only)

All other urban specialists produce science solely from their tier effect:

| Specialist Class | Tier 1 | Tier 2 | Tier 3 |
|-----------------|--------|--------|--------|
| Acolyte | 20 | 30 | 40 |
| Monk | 20 | 30 | 40 |
| Priest | 20 | 30 | 40 |
| Officer | 20 | 30 | 40 |
| Poet | 20 | 30 | 40 |
| Scribe | 20 | 30 | 40 |
| Shopkeeper | 20 | 30 | 40 |
| Bishop | 20 | 30 | 40 |

### Rural Specialists (10 Science Each)

All rural specialists produce 10 science/turn regardless of which resource they gather:

| Specialist | Primary Yield | Science/Turn |
|------------|---------------|--------------|
| Farmer | Food (farms) | 10 |
| Miner | Iron (mines) | 10 |
| Stonecutter | Stone (quarries) | 10 |
| Woodcutter | Wood (lumbermills) | 10 |
| Rancher | Food (pastures) | 10 |
| Trapper | Food (camps) | 10 |
| Gardener | Food (groves) | 10 |
| Fisher | Food (nets) | 10 |

---

## 2. Improvements

### Direct Science-Generating Improvements

#### Mills (Universal)

| Improvement | Science/Turn | Cost | Upkeep | Requirement |
|-------------|--------------|------|--------|-------------|
| **Watermill** | 20 | 40 wood | -10 wood/turn | River tile |
| **Windmill** | 20 | 40 stone | -10 stone/turn | Hill terrain |

**XML Location:** `Reference/XML/Infos/improvement.xml` (lines 1431, 1472)

#### Pagan Shrines (Nation-Specific)

| Improvement | Science/Turn | Cost | Nation | Religion |
|-------------|--------------|------|--------|----------|
| **Shrine of Nabu** | 10 | 40 stone | Babylonia | Pagan Babylonia |
| **Shrine of Athena** | 10 | 40 stone | Greece | Pagan Greece |

**XML Location:** `Reference/XML/Infos/improvement.xml` (lines 2825, 2877)

#### Monasteries (Religion-Specific)

All monasteries provide identical science output but require different religions:

| Improvement | Science/Turn | Cost | Upkeep | Religion |
|-------------|--------------|------|--------|----------|
| **Monastery (Christianity)** | 20 | 60 wood | -20 wood/turn | Christianity |
| **Monastery (Judaism)** | 20 | 60 wood | -20 wood/turn | Judaism |
| **Monastery (Manichaeism)** | 20 | 60 wood | -20 wood/turn | Manichaeism |
| **Monastery (Zoroastrianism)** | 20 | 60 wood | -20 wood/turn | Zoroastrianism |

**XML Location:** `Reference/XML/Infos/improvement.xml` (line 4075+)

### Science Modifier Improvements

These don't produce science directly but multiply all science in the city:

#### Library Chain

| Improvement | Science Modifier | Additional Effect | Upgrade From |
|-------------|-----------------|-------------------|--------------|
| **Library 1** | +10% | - | None |
| **Library 2** | +20% | - | Library 1 |
| **Library 3** | +30% | +10% civics | Library 2 |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 1526-1556)

#### Musaeum (Wonder)

| Stat | Value |
|------|-------|
| Science Modifier | **+50%** |
| Additional Effect | +10 civics to all Elder specialists |
| Cost | 300 civics, 400 wood, 800 stone |

**XML Location:** `Reference/XML/Infos/improvement.xml` (line 5234)

The Musaeum is the single strongest science modifier in the game.

---

## 3. City Projects

### Archive Projects (Science Focus)

Archive projects are the main city project for science generation. Each tier significantly increases output:

| Project | Science/Turn | Additional | Cumulative |
|---------|--------------|------------|------------|
| **Archive 1** | +10 | - | 10/turn |
| **Archive 2** | +20 | - | 30/turn |
| **Archive 3** | +40 | - | 70/turn |
| **Archive 4** | +80 | +10 happiness | 150/turn |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 3461-3510)

### Scientific Method Project

| Effect | Value |
|--------|-------|
| Science Modifier | +10% |
| Orders | +10/turn |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (line 4072)

---

## 4. Character Traits

### Intelligent Trait

Characters with the Intelligent trait provide science bonuses:

| Effect | Scope | Bonus |
|--------|-------|-------|
| City science | Governor's city | +10 science/turn |
| Family-wide | All family cities | +5 science/turn |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 5774-5794)

### Foolish Trait

The opposite of Intelligent, this trait reduces science:

| Effect | Scope | Penalty |
|--------|-------|---------|
| City science modifier | Governor's city | -20% |
| Family-wide modifier | All family cities | -10% |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 5796-5815)

### Scholar Archetype

Characters with the Scholar archetype provide special bonuses:

| Effect | Value |
|--------|-------|
| Archive project rate | +20 science |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 5584-5595)

---

## 5. Family Bonuses

### Sages Family

The Sages family specializes in science and civics:

| Effect | Value |
|--------|-------|
| Base civics | +20/turn |
| Specialist science | +10 science for all specialists in family cities |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 1117-1131)

This means every specialist (not just Philosophers) in a Sages city gains +10 science/turn.

---

## 6. Nation Bonuses

### Babylonia

Babylonia is the science-focused nation:

| Effect | Value |
|--------|-------|
| Science | +10/turn (all cities) |
| Growth modifier | +20% |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 2320-2343)

---

## 7. Laws

### Philosophy Law

| Effect | Value |
|--------|-------|
| Specialist training time | -20% |
| Forum project bonus | +10 science |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 2125-2143)

### Centralization Law (Capital)

| Effect | Value | Scope |
|--------|-------|-------|
| Science | +20/turn | Capital only |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 2005-2013)

### Constitution Law

| Effect | Value |
|--------|-------|
| Urban specialist yield rate | +10 science |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 2033-2041)

---

## 8. Religion & Theology

### Dualism Theology

| Effect | Value |
|--------|-------|
| Science yield rate | +10 (religion-dependent) |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 5469-5476)

### Gnosticism Theology

| Effect | Value |
|--------|-------|
| Archive project bonus | +20 civics |

---

## 9. Steles

### Clerics Family Steles

The Clerics family steles focus on science modifiers:

| Stele | Science Modifier |
|-------|-----------------|
| **Stele 1 (Clerics)** | +10% |
| **Stele 2 (Clerics)** | +25% |
| **Stele 3 (Clerics)** | +50% |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 6690-6717)

---

## 10. Events

Events can provide one-time science gains. The amounts scale based on game state:

### Standard Science Gain Bonuses

| Bonus ID | Base Amount | Scaling | Typical Total |
|----------|-------------|---------|---------------|
| `BONUS_SCIENCE_GAIN_MINIMAL` | 4 | +1 per factor | ~4-5 |
| `BONUS_SCIENCE_GAIN_TINY` | 8 | +2 per factor | ~8-10 |
| `BONUS_SCIENCE_GAIN_SMALL` | 20 | +5 per factor | ~20-25 |
| `BONUS_SCIENCE_GAIN_AVERAGE` | 40 | +10 per factor | ~40-50 |
| `BONUS_SCIENCE_GAIN_LARGE` | 60 | +15 per factor | ~60-75 |
| `BONUS_SCIENCE_GAIN_HUGE` | 80 | +20 per factor | ~80-100 |
| `BONUS_SCIENCE_GAIN_GIGANTIC` | 120 | +30 per factor | ~120+ |

**XML Location:** `Reference/XML/Infos/bonus.xml` (lines 3096-3195)

### Common Event Sources

- Ruins exploration
- Comet sighted events
- Tribe peace offerings
- Character study events
- Random narrative events

---

## 11. Game Settings & Difficulty

### Starting Bonuses

| Setting | Science Bonus |
|---------|---------------|
| Traditional Starting Bonuses | +20/turn |
| No Starting Techs | +80/turn |
| Competitive Mode | +40/turn |

**XML Location:** `Reference/XML/Infos/effectPlayer.xml` (lines 110-163)

### AI Advantage System

AI players receive science modifiers based on difficulty:

| Advantage Level | Science Modifier |
|----------------|------------------|
| Small | +10% |
| Moderate | +20% |
| High | +50% |
| Very High | +100% |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 563-655)

### Player Penalties (When Playing at Advantage)

| Penalty Level | Science Modifier |
|---------------|------------------|
| Small | -5% |
| Moderate | -10% |
| High | -25% |

**XML Location:** `Reference/XML/Infos/effectCity.xml` (lines 467-561)

---

## 12. Understanding Science in Save Files

### Display Scaling

**Important:** XML values appear to use a 10:1 ratio compared to in-game display. When the XML shows `iValue>10`, the game displays ~1 science. This applies to all yield values in the XML files. Keep this in mind when interpreting save files or modding.

### Yield Mechanics

Science is defined as `YIELD_SCIENCE` in the yield system:

| Property | Value |
|----------|-------|
| Triangle offset | -2 |
| Per connected foreign city | +5 science |
| Negative happiness penalty | -5% per level |

**XML Location:** `Reference/XML/Infos/yield.xml` (lines 172-182)

### How Science is Calculated

Total city science = (Base Science + Specialist Science + Improvement Science + Bonuses) × (1 + Sum of Modifiers)

**Example calculation:**

```
Base sources:
  - 2 Philosopher 3s: 80 × 2 = 160 (each gets 40 tier + 40 bonus)
  - 1 Scribe 2: 30 (Master tier only)
  - Watermill: 20
  - Archive 3: 40
  - Sages bonus (3 specialists): 10 × 3 = 30
  Subtotal: 280

Modifiers:
  - Library 3: +30%
  - Musaeum: +50%
  - Clerics Stele 2: +25%
  Total modifier: +105%

Final science: 280 × 2.05 = 574/turn
```

### Save File Interpretation

In save files, science values appear in several contexts:

1. **City yields** - Current production values
2. **Player totals** - Accumulated science toward current research
3. **Tech progress** - Percentage toward next technology

Key XML tags in save data:
- `<iScience>` - Raw science value
- `<aiYield>` - Array of all yields (science is typically index 4)
- `<iModifier>` - Percentage modifier being applied

---

## 13. Quick Reference Tables

### Top Science Sources (Base Output)

| Rank | Source | Science/Turn | Type |
|------|--------|--------------|------|
| 1 | Archive 4 | 80 | Project |
| 2 | Philosopher 3 | 80 | Specialist (40 tier + 40 bonus) |
| 3 | Philosopher 2 / Doctor 3 | 60 | Specialist |
| 4 | Philosopher 1 / Doctor 2 / Any Elder | 40 | Specialist |
| 5 | Any Master specialist | 30 | Specialist |
| 6 | Watermill/Windmill | 20 | Improvement |
| 7 | Monastery / Any Apprentice | 20 | Improvement / Specialist |
| 8 | Rural specialists | 10 | Specialist |
| 9 | Shrine / Archive 1 | 10 | Improvement / Project |

### Top Science Modifiers

| Rank | Source | Modifier | Type |
|------|--------|----------|------|
| 1 | Musaeum | +50% | Wonder |
| 2 | Clerics Stele 3 | +50% | Stele |
| 3 | Library 3 | +30% | Improvement |
| 4 | Clerics Stele 2 | +25% | Stele |
| 5 | Library 2 | +20% | Improvement |
| 6 | Clerics Stele 1 / Scientific Method | +10% | Stele/Project |
| 7 | Library 1 | +10% | Improvement |

### Stacking Modifiers Example

For maximum science in a single city:

| Source | Modifier |
|--------|----------|
| Musaeum | +50% |
| Library 3 | +30% |
| Clerics Stele 3 | +50% |
| Scientific Method | +10% |
| **Total** | **+140%** |

This would multiply all base science by 2.4×.

---

## File Reference

| Content | File Path |
|---------|-----------|
| Specialist definitions | `Reference/XML/Infos/specialist.xml` |
| Improvement definitions | `Reference/XML/Infos/improvement.xml` |
| Effect definitions | `Reference/XML/Infos/effectCity.xml` |
| Player effects | `Reference/XML/Infos/effectPlayer.xml` |
| Bonus definitions | `Reference/XML/Infos/bonus.xml` |
| Yield definitions | `Reference/XML/Infos/yield.xml` |
| Event bonuses | `Reference/XML/Infos/bonus-event.xml` |

---

*Document generated from Old World Reference XML files.*
