"""Tests for GAMEDATA sheet parser."""

import pytest

from tournament_visualizer.data.gamedata_parser import (
    find_game_columns,
    find_row_by_label,
    find_round_sections,
    parse_game_columns,
)


class TestFindRoundSections:
    """Test round section detection."""

    def test_finds_round_1(self) -> None:
        """Finds ROUND 1 header."""
        rows = [
            [""],
            ["ROUND 1"],
            [""],
        ]

        rounds = find_round_sections(rows)

        assert len(rounds) == 1
        assert rounds[0]["round_number"] == 1
        assert rounds[0]["label"] == "ROUND 1"
        assert rounds[0]["start_row"] == 1

    def test_finds_multiple_rounds(self) -> None:
        """Finds multiple round headers."""
        rows = [
            ["ROUND 1"],
            ["", "", ""],
            ["", "", ""],
            ["ROUND 2", "UPPER BRACKET ROUND 2, G21-G28"],
            ["", "", ""],
        ]

        rounds = find_round_sections(rows)

        assert len(rounds) == 2
        assert rounds[0]["round_number"] == 1
        assert rounds[1]["round_number"] == 2
        assert rounds[1]["label"] == "ROUND 2"

    def test_handles_empty_sheet(self) -> None:
        """Returns empty list for empty sheet."""
        rounds = find_round_sections([])
        assert rounds == []


class TestFindRowByLabel:
    """Test row label detection."""

    def test_finds_exact_match(self) -> None:
        """Finds row with exact label match."""
        rows = [
            [""],
            ["Game Number"],
            ["Players"],
        ]

        idx = find_row_by_label(rows, "Game Number")
        assert idx == 1

    def test_finds_case_insensitive(self) -> None:
        """Finds row case-insensitively."""
        rows = [
            ["GAME NUMBER"],
            ["players"],
        ]

        idx = find_row_by_label(rows, "game number")
        assert idx == 0

    def test_finds_partial_match(self) -> None:
        """Finds row with label as substring."""
        rows = [
            ["Nation; First Pick"],
        ]

        idx = find_row_by_label(rows, "First Pick")
        assert idx == 0

    def test_returns_none_if_not_found(self) -> None:
        """Returns None if label not found."""
        rows = [[""], ["Other"], [""]]

        idx = find_row_by_label(rows, "Game Number")
        assert idx is None


class TestFindGameColumns:
    """Test game column detection."""

    def test_finds_single_game(self) -> None:
        """Finds columns for single game."""
        row = ["", "", "Game 1", ""]

        games = find_game_columns(row)

        assert len(games) == 1
        assert games[0]["game_number"] == 1
        assert games[0]["col_start"] == 2

    def test_finds_multiple_games(self) -> None:
        """Finds columns for multiple games."""
        row = ["", "", "Game 1", "", "", "Game 2", ""]

        games = find_game_columns(row)

        assert len(games) == 2
        assert games[0]["game_number"] == 1
        assert games[0]["col_start"] == 2
        assert games[1]["game_number"] == 2
        assert games[1]["col_start"] == 5

    def test_handles_empty_row(self) -> None:
        """Returns empty list for empty row."""
        games = find_game_columns([])
        assert games == []


class TestParseGameColumns:
    """Test game data extraction."""

    def test_parses_complete_game(self) -> None:
        """Parses game with all required data."""
        game_number_row = ["", "", "Game 1", ""]
        players_row = ["Players", "", "Becked", "Anarkos"]
        first_pick_row = ["Nation; First Pick", "", "Assyria", ""]
        second_pick_row = ["Second Pick", "", "", "Persia"]

        game = parse_game_columns(
            game_number_row=game_number_row,
            players_row=players_row,
            first_pick_row=first_pick_row,
            second_pick_row=second_pick_row,
            game_col_start=2,
            game_col_end=4,
            round_number=1,
            round_label="ROUND 1",
        )

        assert game is not None
        assert game["game_number"] == 1
        assert game["round_number"] == 1
        assert game["player1_sheet_name"] == "Becked"
        assert game["player2_sheet_name"] == "Anarkos"
        assert game["first_pick_nation"] == "Assyria"
        assert game["second_pick_nation"] == "Persia"

    def test_returns_none_if_missing_players(self) -> None:
        """Returns None if players missing."""
        game_number_row = ["", "", "Game 1"]
        players_row = ["Players", "", ""]  # Missing players
        first_pick_row = ["Nation; First Pick", "", "Assyria"]
        second_pick_row = ["Second Pick", "", "Persia"]

        game = parse_game_columns(
            game_number_row=game_number_row,
            players_row=players_row,
            first_pick_row=first_pick_row,
            second_pick_row=second_pick_row,
            game_col_start=2,
            game_col_end=3,
            round_number=1,
            round_label="ROUND 1",
        )

        assert game is None

    def test_returns_none_if_missing_nations(self) -> None:
        """Returns None if nations missing."""
        game_number_row = ["", "", "Game 1"]
        players_row = ["Players", "", "Player1", "Player2"]
        first_pick_row = ["Nation; First Pick", "", ""]  # Missing
        second_pick_row = ["Second Pick", "", ""]  # Missing

        game = parse_game_columns(
            game_number_row=game_number_row,
            players_row=players_row,
            first_pick_row=first_pick_row,
            second_pick_row=second_pick_row,
            game_col_start=2,
            game_col_end=4,
            round_number=1,
            round_label="ROUND 1",
        )

        assert game is None
