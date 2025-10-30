"""Tests for city data parsing.

Test Strategy:
- Use sample XML with known city data
- Test happy path (normal cities)
- Test edge cases (capitals, captured cities, empty production)
- Test player ID conversion (XML 0-based → DB 1-based)
- Verify all required fields are extracted
"""

import pytest
from pathlib import Path
from tournament_visualizer.data.parser import OldWorldSaveParser


class TestCityParsing:
    """Test parsing city data from XML."""

    @pytest.fixture
    def sample_xml_with_cities(self, tmp_path: Path) -> Path:
        """Create sample XML with city data.

        Returns:
            Path to temporary XML file
        """
        xml_content = """<?xml version="1.0"?>
<Game
    Version="1.0.75"
    Turn="69">

    <Player ID="0">
        <Name>anarkos</Name>
        <Civilization>PERSIA</Civilization>
    </Player>

    <Player ID="1">
        <Name>becked</Name>
        <Civilization>ASSYRIA</Civilization>
    </Player>

    <City
        ID="0"
        TileID="1292"
        Player="1"
        Family="FAMILY_TUDIYA"
        Founded="1">
        <NameType>CITYNAME_NINEVEH</NameType>
        <GovernorID>72</GovernorID>
        <Citizens>3</Citizens>
        <Capital />
        <FirstPlayer>1</FirstPlayer>
        <LastPlayer>1</LastPlayer>
        <UnitProductionCounts>
            <UNIT_SETTLER>4</UNIT_SETTLER>
            <UNIT_WORKER>1</UNIT_WORKER>
            <UNIT_SPEARMAN>2</UNIT_SPEARMAN>
        </UnitProductionCounts>
        <ProjectCount>
            <PROJECT_FORUM_2>1</PROJECT_FORUM_2>
            <PROJECT_SWORD_CULT_TITHE>1</PROJECT_SWORD_CULT_TITHE>
        </ProjectCount>
    </City>

    <City
        ID="1"
        TileID="1375"
        Player="0"
        Family="FAMILY_ACHAEMENID"
        Founded="1">
        <NameType>CITYNAME_PERSEPOLIS</NameType>
        <GovernorID>61</GovernorID>
        <Citizens>5</Citizens>
        <Capital />
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts>
            <UNIT_SETTLER>4</UNIT_SETTLER>
            <UNIT_WORKER>1</UNIT_WORKER>
        </UnitProductionCounts>
        <ProjectCount>
            <PROJECT_GRAIN_DOLE>1</PROJECT_GRAIN_DOLE>
        </ProjectCount>
    </City>

    <City
        ID="2"
        TileID="1073"
        Player="1"
        Family="FAMILY_TUDIYA"
        Founded="7">
        <NameType>CITYNAME_SAREISA</NameType>
        <Citizens>1</Citizens>
        <FirstPlayer>1</FirstPlayer>
        <LastPlayer>1</LastPlayer>
        <UnitProductionCounts>
            <UNIT_WORKER>2</UNIT_WORKER>
        </UnitProductionCounts>
        <ProjectCount>
            <PROJECT_FORUM_1>1</PROJECT_FORUM_1>
        </ProjectCount>
    </City>

    <City
        ID="3"
        TileID="999"
        Player="1"
        Family="FAMILY_ADASI"
        Founded="20">
        <NameType>CITYNAME_CAPTURED</NameType>
        <Citizens>2</Citizens>
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>1</LastPlayer>
        <UnitProductionCounts />
        <ProjectCount />
    </City>
</Game>
"""
        xml_file = tmp_path / "test_cities.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_extract_cities_basic(self, sample_xml_with_cities: Path) -> None:
        """Test extracting basic city data from XML."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # Should find 4 cities
        assert len(cities) == 4

        # Check first city (Nineveh)
        nineveh = cities[0]
        assert nineveh['city_id'] == 0
        assert nineveh['city_name'] == 'CITYNAME_NINEVEH'
        assert nineveh['tile_id'] == 1292
        assert nineveh['founded_turn'] == 1
        assert nineveh['family_name'] == 'FAMILY_TUDIYA'
        assert nineveh['population'] == 3
        assert nineveh['governor_id'] == 72

    def test_player_id_conversion(self, sample_xml_with_cities: Path) -> None:
        """Test that player IDs are converted from XML (0-based) to DB (1-based).

        CRITICAL: XML uses 0-based IDs, database uses 1-based.
        XML Player="0" → DB player_id=1
        """
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # Nineveh: XML Player="1" → DB player_id=2
        nineveh = cities[0]
        assert nineveh['player_id'] == 2, "XML Player=1 should become DB player_id=2"

        # Persepolis: XML Player="0" → DB player_id=1
        persepolis = cities[1]
        assert persepolis['player_id'] == 1, "XML Player=0 should become DB player_id=1"

    def test_capital_flag(self, sample_xml_with_cities: Path) -> None:
        """Test that capital cities are identified correctly."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # First two cities are capitals (have <Capital /> element)
        assert cities[0]['is_capital'] is True
        assert cities[1]['is_capital'] is True

        # Third city is not a capital
        assert cities[2]['is_capital'] is False

    def test_captured_city_detection(self, sample_xml_with_cities: Path) -> None:
        """Test that captured cities are detected correctly.

        Captured city: FirstPlayer != LastPlayer
        """
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        cities = parser.extract_cities()

        # Fourth city was captured
        captured = cities[3]
        assert captured['first_player_id'] == 1  # XML FirstPlayer="0" → DB 1
        assert captured['player_id'] == 2  # XML LastPlayer="1" → DB 2
        assert captured['first_player_id'] != captured['player_id']

        # First city was not captured
        nineveh = cities[0]
        assert nineveh['first_player_id'] == nineveh['player_id']

    def test_extract_unit_production(self, sample_xml_with_cities: Path) -> None:
        """Test extracting unit production counts."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        production = parser.extract_city_unit_production()

        # Should have production from cities 0, 1, 2 (city 3 is empty)
        # City 0: 3 unit types (SETTLER, WORKER, SPEARMAN)
        # City 1: 2 unit types (SETTLER, WORKER)
        # City 2: 1 unit type (WORKER)
        # Total: 6 records
        assert len(production) == 6

        # Check Nineveh's production (city_id=0)
        nineveh_production = [p for p in production if p['city_id'] == 0]
        assert len(nineveh_production) == 3

        # Check settler production
        settlers = [p for p in nineveh_production if p['unit_type'] == 'UNIT_SETTLER']
        assert len(settlers) == 1
        assert settlers[0]['count'] == 4

    def test_extract_city_projects(self, sample_xml_with_cities: Path) -> None:
        """Test extracting city project counts."""
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        projects = parser.extract_city_projects()

        # City 0: 2 projects
        # City 1: 1 project
        # City 2: 1 project
        # City 3: 0 projects (empty)
        # Total: 4 records
        assert len(projects) == 4

        # Check Nineveh's projects (city_id=0)
        nineveh_projects = [p for p in projects if p['city_id'] == 0]
        assert len(nineveh_projects) == 2

        # Check forum project
        forums = [p for p in nineveh_projects if p['project_type'] == 'PROJECT_FORUM_2']
        assert len(forums) == 1
        assert forums[0]['count'] == 1

    def test_empty_production(self, sample_xml_with_cities: Path) -> None:
        """Test handling cities with no production.

        Edge case: City 3 has <UnitProductionCounts /> (empty)
        Should not error, just return empty list for that city.
        """
        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(sample_xml_with_cities))

        production = parser.extract_city_unit_production()

        # City 3 should have no production records
        city_3_production = [p for p in production if p['city_id'] == 3]
        assert len(city_3_production) == 0

    def test_missing_optional_fields(self, tmp_path: Path) -> None:
        """Test handling cities with missing optional fields.

        Optional fields: governor_id, population, family_name
        """
        xml_content = """<?xml version="1.0"?>
<Game Turn="10">
    <City
        ID="0"
        TileID="100"
        Player="0"
        Founded="5">
        <NameType>CITYNAME_TEST</NameType>
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts />
        <ProjectCount />
    </City>
</Game>
"""
        xml_file = tmp_path / "test_minimal.xml"
        xml_file.write_text(xml_content)

        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(xml_file))

        cities = parser.extract_cities()

        assert len(cities) == 1
        city = cities[0]

        # Required fields should exist
        assert city['city_id'] == 0
        assert city['city_name'] == 'CITYNAME_TEST'

        # Optional fields should be None or have defaults
        assert city.get('governor_id') is None
        assert city.get('population') is None or city.get('population') == 0
        assert city.get('family_name') is None
        assert city['is_capital'] is False

    def test_zero_player_id_valid(self, tmp_path: Path) -> None:
        """Test that Player ID 0 is valid and not skipped.

        CRITICAL: Player ID="0" is valid! Don't skip it.
        XML Player="0" → DB player_id=1
        """
        xml_content = """<?xml version="1.0"?>
<Game Turn="1">
    <City
        ID="0"
        TileID="100"
        Player="0"
        Founded="1">
        <NameType>CITYNAME_CAPITAL</NameType>
        <Capital />
        <FirstPlayer>0</FirstPlayer>
        <LastPlayer>0</LastPlayer>
        <UnitProductionCounts />
        <ProjectCount />
    </City>
</Game>
"""
        xml_file = tmp_path / "test_player_zero.xml"
        xml_file.write_text(xml_content)

        parser = OldWorldSaveParser("")
        parser.parse_xml_file(str(xml_file))

        cities = parser.extract_cities()

        assert len(cities) == 1
        assert cities[0]['player_id'] == 1  # XML 0 → DB 1
