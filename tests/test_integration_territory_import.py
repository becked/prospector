"""Integration test for territory tile detail import."""

import tempfile
import zipfile
from pathlib import Path
from tournament_visualizer.data.parser import OldWorldSaveParser
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.etl import TournamentETL


def test_full_territory_import_with_tile_details() -> None:
    """Test complete import pipeline with specialists and improvements."""

    # Create minimal valid save file
    xml_content = """<?xml version="1.0"?>
<Root
    MapWidth="3"
    Turn="2"
    GameName="Test Game"
    Year="100">
    <Player ID="0" OnlineID="12345" Name="TestPlayer" Team="0" />
    <GameState Turn="1" Year="100" />
    <GameState Turn="2" Year="101" />
    <Tile ID="0">
        <Terrain>TERRAIN_GRASSLAND</Terrain>
        <Improvement>IMPROVEMENT_FARM</Improvement>
        <Resource>RESOURCE_WHEAT</Resource>
        <Road />
        <OwnerHistory><T1>0</T1></OwnerHistory>
    </Tile>
    <Tile ID="1">
        <Terrain>TERRAIN_TEMPERATE</Terrain>
        <Improvement>IMPROVEMENT_MINE</Improvement>
        <Specialist>SPECIALIST_MINER</Specialist>
        <Road />
        <OwnerHistory><T1>0</T1></OwnerHistory>
    </Tile>
    <Tile ID="2">
        <Terrain>TERRAIN_WATER</Terrain>
    </Tile>
</Root>
"""

    # Create temporary zip file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Write XML to zip
        zip_path = tmpdir_path / "test_game.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test_game.xml", xml_content)

        # Create temporary database
        db_path = tmpdir_path / "test.duckdb"
        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        # Import via ETL pipeline
        etl = TournamentETL(db)
        match_id = etl.process_tournament_file(str(zip_path))

        assert match_id is not None

        # Verify territories were imported with new fields
        with db.get_connection() as conn:
            territories = conn.execute("""
                SELECT
                    turn_number,
                    x_coordinate,
                    y_coordinate,
                    terrain_type,
                    improvement_type,
                    specialist_type,
                    resource_type,
                    has_road
                FROM territories
                WHERE match_id = ?
                ORDER BY turn_number, x_coordinate, y_coordinate
            """, [match_id]).fetchall()

        # Should have 3 tiles × 2 turns = 6 records
        assert len(territories) == 6

        # Check turn 2, tile 0 (farm with wheat and road)
        t2_tile0 = [t for t in territories if t[0] == 2 and t[1] == 0][0]
        assert t2_tile0[3] == "TERRAIN_GRASSLAND"
        assert t2_tile0[4] == "IMPROVEMENT_FARM"
        assert t2_tile0[5] is None  # No specialist
        assert t2_tile0[6] == "RESOURCE_WHEAT"
        assert t2_tile0[7] is True  # Has road

        # Check turn 2, tile 1 (mine with specialist)
        t2_tile1 = [t for t in territories if t[0] == 2 and t[1] == 1][0]
        assert t2_tile1[3] == "TERRAIN_TEMPERATE"
        assert t2_tile1[4] == "IMPROVEMENT_MINE"
        assert t2_tile1[5] == "SPECIALIST_MINER"
        assert t2_tile1[6] is None  # No resource
        assert t2_tile1[7] is True  # Has road

        # Check turn 2, tile 2 (water, no features)
        t2_tile2 = [t for t in territories if t[0] == 2 and t[1] == 2][0]
        assert t2_tile2[3] == "TERRAIN_WATER"
        assert t2_tile2[4] is None  # No improvement
        assert t2_tile2[5] is None  # No specialist
        assert t2_tile2[6] is None  # No resource
        assert t2_tile2[7] is False  # No road
