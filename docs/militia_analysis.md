# Militia Unit Analysis: Built vs Converted

## Overview

In Old World, militia units can be created in two ways:
1. **Built** - Produced from cities like other military units
2. **Converted** - Created by converting worker units into militia

This document explains how to distinguish between these two sources using save file data.

## Method

The save file XML contains a `UnitsProduced` section that tracks units that were **built from cities**. By comparing the total militia count against the built count, you can determine how many were converted.

### Step-by-Step Process

1. **Count total militia units**
   - Search for all `<Unit>` elements with `Type="UNIT_MILITIA"`
   - Count per player if needed

2. **Find built militia count**
   - Locate the `<UnitsProduced>` section (may be per-player in `<Player>` elements)
   - Find the `<UNIT_MILITIA>` tag value

3. **Calculate converted militia**
   ```
   Converted = Total Militia - Built Militia
   ```

## Example

From a Persia vs Assyria save file (Year 69):

```xml
<!-- Player 0's production stats -->
<UnitsProduced>
  <UNIT_MILITIA>6</UNIT_MILITIA>
</UnitsProduced>

<!-- Total militia units found: 6 (3 for Player 0, 3 for Player 1) -->
```

**Result**: 6 built, 0 converted (all militia were produced from cities)

## Python Code Example

```python
import xml.etree.ElementTree as ET

tree = ET.parse('save_file.xml')
root = tree.getroot()

# Count total militia units
total_militia = sum(1 for unit in root.iter('Unit')
                   if unit.get('Type') == 'UNIT_MILITIA')

# Get built militia count
built_militia = 0
for elem in root.iter('UnitsProduced'):
    for child in elem:
        if child.tag == 'UNIT_MILITIA':
            built_militia += int(child.text)

# Calculate conversions
converted_militia = total_militia - built_militia

print(f"Total militia: {total_militia}")
print(f"Built: {built_militia}")
print(f"Converted from workers: {converted_militia}")
```

## Per-Player Analysis

To analyze per player, check the `<Player>` elements for individual `UnitsProduced` sections:

```python
for player_elem in root.iter('Player'):
    player_id = player_elem.get('ID')

    # Count militia for this player
    player_militia = sum(1 for unit in root.iter('Unit')
                        if unit.get('Type') == 'UNIT_MILITIA'
                        and unit.get('Player') == player_id)

    # Get built count
    built = 0
    for stats in player_elem.iter('UnitsProduced'):
        militia_elem = stats.find('UNIT_MILITIA')
        if militia_elem is not None:
            built = int(militia_elem.text)
        break

    converted = player_militia - built
    print(f"Player {player_id}: {player_militia} total ({built} built, {converted} converted)")
```

## Related Data

### Other Unit Statistics

The save file also tracks:
- `STAT_UNIT_TRAINED` - Total units trained
- `UnitsProducedTurn` - Turn numbers when units were produced
- `CreateTurn` - Individual unit's creation turn (in `<Unit>` element)

### Unit Fields

Each militia unit contains:
- `CreateTurn` - Turn when created
- `Player` - Owning player
- `OriginalPlayer` - Original owner (for captured units)
- No direct field indicating conversion vs building

## Notes

- The `UnitsProduced` counter only tracks **built** units
- Worker-to-militia conversion does not increment `UnitsProduced`
- This method works for all unit types, not just militia
- Disbanded units may still count in `UnitsProduced` but won't appear in active units
