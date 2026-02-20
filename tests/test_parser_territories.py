"""Tests for territory extraction from Old World save files."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tournament_visualizer.data.parser import OldWorldSaveParser


@pytest.fixture
def minimal_xml_tree():
    """Create minimal XML tree for testing territory extraction."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <Root MapWidth="3" TurnScale="TURNSCALE_YEAR">
      <Tile ID="0">
        <Terrain>TERRAIN_GRASSLAND</Terrain>
        <OwnerHistory>
          <T1>0</T1>
          <T2>0</T2>
        </OwnerHistory>
      </Tile>
      <Tile ID="1">
        <Terrain>TERRAIN_WATER</Terrain>
      </Tile>
      <Tile ID="2">
        <Terrain>TERRAIN_DESERT</Terrain>
        <OwnerHistory>
          <T1>1</T1>
        </OwnerHistory>
      </Tile>
    </Root>
    """
    return ET.ElementTree(ET.fromstring(xml_content))


def test_extract_territories_basic_structure(minimal_xml_tree):
    """Test that extract_territories returns correct structure."""
    parser = OldWorldSaveParser("")
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Should have 3 tiles × 2 turns = 6 records
    assert len(territories) == 6

    # Check first record structure
    first = territories[0]
    assert "match_id" in first
    assert "tile_id" in first
    assert "x_coordinate" in first
    assert "y_coordinate" in first
    assert "turn_number" in first
    assert "terrain_type" in first
    assert "owner_player_id" in first


def test_extract_territories_coordinates(minimal_xml_tree):
    """Test that tile IDs are correctly converted to x,y coordinates."""
    parser = OldWorldSaveParser("")
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=1)

    # Map width is 3, so:
    # Tile 0: x=0, y=0
    # Tile 1: x=1, y=0
    # Tile 2: x=2, y=0

    tile_coords = {
        t["tile_id"]: (t["x_coordinate"], t["y_coordinate"])
        for t in territories
        if t["turn_number"] == 1
    }

    assert tile_coords[0] == (0, 0)
    assert tile_coords[1] == (1, 0)
    assert tile_coords[2] == (2, 0)


def test_extract_territories_ownership(minimal_xml_tree):
    """Test that ownership is correctly extracted and mapped."""
    parser = OldWorldSaveParser("")
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Without player_id_mapping, slot IDs are stored as-is (1-based from XML 0-based)
    # Tile 0, turn 1: owned by player 0 (XML) -> slot 1
    tile0_turn1 = [
        t for t in territories if t["tile_id"] == 0 and t["turn_number"] == 1
    ][0]
    assert tile0_turn1["owner_player_id"] == 1  # XML 0 -> slot 1

    # Tile 1, turn 1: no owner -> NULL
    tile1_turn1 = [
        t for t in territories if t["tile_id"] == 1 and t["turn_number"] == 1
    ][0]
    assert tile1_turn1["owner_player_id"] is None

    # Tile 2, turn 1: owned by player 1 (XML) -> slot 2
    tile2_turn1 = [
        t for t in territories if t["tile_id"] == 2 and t["turn_number"] == 1
    ][0]
    assert tile2_turn1["owner_player_id"] == 2  # XML 1 -> slot 2


def test_extract_territories_ownership_with_mapping(minimal_xml_tree):
    """Test that player_id_mapping converts slot IDs to global player IDs."""
    parser = OldWorldSaveParser("")
    parser.root = minimal_xml_tree.getroot()

    # Simulate match 5 where slot 1 -> player_id 9, slot 2 -> player_id 10
    mapping = {1: 9, 2: 10}
    territories = parser.extract_territories(
        match_id=5, final_turn=2, player_id_mapping=mapping
    )

    # Tile 0, turn 1: XML player 0 -> slot 1 -> global player_id 9
    tile0_turn1 = [
        t for t in territories if t["tile_id"] == 0 and t["turn_number"] == 1
    ][0]
    assert tile0_turn1["owner_player_id"] == 9

    # Tile 1, turn 1: no owner -> still None
    tile1_turn1 = [
        t for t in territories if t["tile_id"] == 1 and t["turn_number"] == 1
    ][0]
    assert tile1_turn1["owner_player_id"] is None

    # Tile 2, turn 1: XML player 1 -> slot 2 -> global player_id 10
    tile2_turn1 = [
        t for t in territories if t["tile_id"] == 2 and t["turn_number"] == 1
    ][0]
    assert tile2_turn1["owner_player_id"] == 10


def test_extract_territories_terrain(minimal_xml_tree):
    """Test that terrain types are correctly extracted."""
    parser = OldWorldSaveParser("")
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=1)

    # Check terrain for each tile (turn 1)
    terrains = {
        t["tile_id"]: t["terrain_type"]
        for t in territories
        if t["turn_number"] == 1
    }

    assert terrains[0] == "TERRAIN_GRASSLAND"
    assert terrains[1] == "TERRAIN_WATER"
    assert terrains[2] == "TERRAIN_DESERT"


def test_extract_territories_all_turns(minimal_xml_tree):
    """Test that all turns are generated for all tiles."""
    parser = OldWorldSaveParser("")
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Group by tile and turn
    tiles_by_turn = {}
    for t in territories:
        key = (t["tile_id"], t["turn_number"])
        tiles_by_turn[key] = t

    # Should have records for all combinations
    assert (0, 1) in tiles_by_turn
    assert (0, 2) in tiles_by_turn
    assert (1, 1) in tiles_by_turn
    assert (1, 2) in tiles_by_turn
    assert (2, 1) in tiles_by_turn
    assert (2, 2) in tiles_by_turn

    # Tile 0, turn 2: still owned by player 0
    assert tiles_by_turn[(0, 2)]["owner_player_id"] == 1


def test_extract_territories_ownership_persistence(minimal_xml_tree):
    """Test that ownership persists across turns until changed."""
    parser = OldWorldSaveParser("")
    parser.root = minimal_xml_tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=2)

    # Tile 2: owned by player 1 at turn 1, no entry for turn 2
    # Should persist ownership to turn 2
    tile2_turn1 = [
        t for t in territories if t["tile_id"] == 2 and t["turn_number"] == 1
    ][0]
    tile2_turn2 = [
        t for t in territories if t["tile_id"] == 2 and t["turn_number"] == 2
    ][0]

    assert tile2_turn1["owner_player_id"] == 2
    assert tile2_turn2["owner_player_id"] == 2  # Persisted


def test_extract_territories_empty_xml():
    """Test graceful handling of XML with no tiles."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <Root MapWidth="10" TurnScale="TURNSCALE_YEAR">
    </Root>
    """
    tree = ET.ElementTree(ET.fromstring(xml_content))

    parser = OldWorldSaveParser("")
    parser.root = tree.getroot()

    territories = parser.extract_territories(match_id=1, final_turn=10)

    # Should return empty list, not error
    assert territories == []


def test_extract_territories_no_map_width():
    """Test error handling when MapWidth attribute is missing."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <Root TurnScale="TURNSCALE_YEAR">
      <Tile ID="0">
        <Terrain>TERRAIN_GRASSLAND</Terrain>
      </Tile>
    </Root>
    """
    tree = ET.ElementTree(ET.fromstring(xml_content))

    parser = OldWorldSaveParser("")
    parser.root = tree.getroot()

    with pytest.raises(ValueError, match="MapWidth"):
        parser.extract_territories(match_id=1, final_turn=1)


def test_extract_territories_includes_specialists() -> None:
    """Test that extract_territories captures specialist assignments."""
    # Create minimal XML with specialist on a tile
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="0">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Specialist>SPECIALIST_MINER</Specialist>
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    # Find the tile record
    tile_record = next(t for t in territories if t["tile_id"] == 0)

    assert tile_record["specialist_type"] == "SPECIALIST_MINER"
    assert tile_record["x_coordinate"] == 0
    assert tile_record["y_coordinate"] == 0


def test_extract_territories_includes_improvements() -> None:
    """Test that extract_territories captures improvement types."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="5">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Improvement>IMPROVEMENT_MINE</Improvement>
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 5)

    assert tile_record["improvement_type"] == "IMPROVEMENT_MINE"


def test_extract_territories_includes_resources() -> None:
    """Test that extract_territories captures natural resources."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="7">
            <Terrain>TERRAIN_GRASSLAND</Terrain>
            <Resource>RESOURCE_HORSE</Resource>
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 7)

    assert tile_record["resource_type"] == "RESOURCE_HORSE"


def test_extract_territories_includes_roads() -> None:
    """Test that extract_territories captures road network."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="3">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Road />
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 3)

    assert tile_record["has_road"] is True


def test_extract_territories_defaults_to_none_when_missing() -> None:
    """Test that tiles without specialists/improvements/resources have None values."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="10">
            <Terrain>TERRAIN_WATER</Terrain>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 10)

    assert tile_record["specialist_type"] is None
    assert tile_record["improvement_type"] is None
    assert tile_record["resource_type"] is None
    assert tile_record["has_road"] is False


def test_extract_territories_combines_all_attributes() -> None:
    """Test that a tile can have multiple attributes simultaneously."""
    xml_content = """<?xml version="1.0"?>
    <Root MapWidth="10">
        <Player ID="0" OnlineID="12345" Name="TestPlayer" />
        <Tile ID="15">
            <Terrain>TERRAIN_TEMPERATE</Terrain>
            <Improvement>IMPROVEMENT_PASTURE</Improvement>
            <Specialist>SPECIALIST_RANCHER</Specialist>
            <Resource>RESOURCE_HORSE</Resource>
            <Road />
            <OwnerHistory><T1>0</T1></OwnerHistory>
        </Tile>
    </Root>
    """

    parser = OldWorldSaveParser("")
    parser.root = ET.fromstring(xml_content)

    territories = parser.extract_territories(match_id=1, final_turn=1)

    tile_record = next(t for t in territories if t["tile_id"] == 15)

    assert tile_record["improvement_type"] == "IMPROVEMENT_PASTURE"
    assert tile_record["specialist_type"] == "SPECIALIST_RANCHER"
    assert tile_record["resource_type"] == "RESOURCE_HORSE"
    assert tile_record["has_road"] is True
    assert tile_record["terrain_type"] == "TERRAIN_TEMPERATE"
