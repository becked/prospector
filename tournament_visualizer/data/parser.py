"""XML parser for Old World game save files.

This module handles parsing of Old World game save XML files to extract
tournament data including match information, players, game state, and events.
"""

import logging
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OldWorldSaveParser:
    """Parser for Old World game save XML files."""

    def __init__(self, zip_file_path: str) -> None:
        """Initialize parser with a zip file path.

        Args:
            zip_file_path: Path to the tournament save zip file
        """
        self.zip_file_path = Path(zip_file_path)
        self.xml_content: Optional[str] = None
        self.root: Optional[ET.Element] = None

    def parse_xml_file(self, xml_file_path: str) -> None:
        """Parse XML directly from a file (for testing purposes).

        Args:
            xml_file_path: Path to the XML file
        """
        xml_path = Path(xml_file_path)
        try:
            with open(xml_path, encoding="utf-8") as f:
                self.xml_content = f.read()

            self.root = ET.fromstring(self.xml_content)
            logger.info(
                f"Successfully parsed XML from {xml_path} with root element: {self.root.tag}"
            )
        except FileNotFoundError:
            raise ValueError(f"XML file not found: {xml_path}")
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML from {xml_path}: {e}")

    def extract_and_parse(self) -> None:
        """Extract XML from zip file and parse it."""
        try:
            with zipfile.ZipFile(self.zip_file_path, "r") as zip_file:
                # Get the first (and likely only) file in the zip
                file_list = zip_file.namelist()
                if not file_list:
                    raise ValueError(f"No files found in {self.zip_file_path}")

                xml_file = file_list[0]
                logger.info(f"Extracting {xml_file} from {self.zip_file_path}")

                # Read the XML content
                with zip_file.open(xml_file) as xml_content:
                    self.xml_content = xml_content.read().decode("utf-8")

        except zipfile.BadZipFile:
            raise ValueError(f"Invalid zip file: {self.zip_file_path}")
        except Exception as e:
            raise ValueError(f"Error extracting file {self.zip_file_path}: {e}")

        # Parse the XML
        try:
            self.root = ET.fromstring(self.xml_content)
            logger.info(f"Successfully parsed XML with root element: {self.root.tag}")
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML from {self.zip_file_path}: {e}")

    def extract_basic_metadata(self) -> Dict[str, Any]:
        """Extract basic match metadata from the save file.

        Returns:
            Dictionary containing match metadata
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        metadata = {
            "file_name": self.zip_file_path.name,
            "game_name": None,
            "save_date": None,
            "game_mode": None,
            "map_size": None,
            "map_class": None,
            "map_aspect_ratio": None,
            "turn_style": None,
            "turn_timer": None,
            "victory_conditions": None,
            "total_turns": 0,
        }

        # Extract metadata from root element attributes (Old World save format)
        root_attrs = self.root.attrib

        # Game name
        metadata["game_name"] = root_attrs.get("GameName")

        # Save date
        save_date_str = root_attrs.get("SaveDate")
        if save_date_str:
            metadata["save_date"] = self._parse_date(save_date_str)

        # Game mode
        metadata["game_mode"] = root_attrs.get("GameMode")

        # Turn style
        turn_style = root_attrs.get("TurnStyle")
        if turn_style:
            # Convert from TURNSTYLE_TIGHT to more readable format
            metadata["turn_style"] = (
                turn_style.replace("TURNSTYLE_", "").replace("_", " ").title()
            )

        # Turn timer
        turn_timer = root_attrs.get("TurnTimer")
        if turn_timer:
            # Convert from TURNTIMER_SLOW to more readable format
            metadata["turn_timer"] = (
                turn_timer.replace("TURNTIMER_", "").replace("_", " ").title()
            )

        # Map information
        map_class = root_attrs.get("MapClass")
        if map_class:
            # Convert from MAPCLASS_CoastalRainBasin to more readable format
            cleaned = map_class.replace("MAPCLASS_", "")
            # Remove Mapscript prefix (case-insensitive)
            import re

            cleaned = re.sub(r"^Mapscript", "", cleaned, flags=re.IGNORECASE)
            # Fix specific names (case-insensitive replacements)
            if "inlandsea" in cleaned.lower():
                cleaned = "Inland Sea"
            elif "coastalrain" in cleaned.lower():
                cleaned = "Coastal Rain Basin"
            elif "continent" in cleaned.lower():
                cleaned = "Continent"
            else:
                # Clean up remaining underscores and title case
                cleaned = cleaned.replace("_", " ").title()
            metadata["map_class"] = cleaned

        map_size = root_attrs.get("MapSize")
        if map_size:
            # Convert from MAPSIZE_SMALLEST to more readable format
            cleaned = map_size.replace("MAPSIZE_", "").replace("_", " ").title()
            # Fix Smallest -> Duel
            if cleaned == "Smallest":
                cleaned = "Duel"
            metadata["map_size"] = cleaned

        # Map aspect ratio
        map_aspect_ratio = root_attrs.get("MapAspectRatio")
        if map_aspect_ratio:
            # Convert from MAPASPECTRATIO_WIDE to Wide
            metadata["map_aspect_ratio"] = (
                map_aspect_ratio.replace("MAPASPECTRATIO_", "")
                .replace("_", " ")
                .title()
            )

        # Map dimensions as backup
        map_width = root_attrs.get("MapWidth")
        if map_width and not metadata["map_size"]:
            metadata["map_size"] = f"{map_width}x{map_width}"

        # Extract victory conditions from VictoryEnabled section
        victory_enabled = self.root.find(".//VictoryEnabled")
        if victory_enabled is not None:
            conditions = []
            for victory_elem in victory_enabled:
                # Add enabled victory types
                victory_type = (
                    victory_elem.tag.replace("VICTORY_", "").replace("_", " ").title()
                )
                conditions.append(victory_type)
            metadata["victory_conditions"] = (
                ", ".join(conditions) if conditions else None
            )

        # Get total turns from Game/Turn element
        game_elem = self.root.find(".//Game")
        if game_elem is not None:
            # Get the turn number from the Game/Turn element
            turn_elem = game_elem.find("Turn")
            if turn_elem is not None and turn_elem.text:
                metadata["total_turns"] = self._safe_int(turn_elem.text, 0)

        # If no turns found, try to extract from filename
        if metadata["total_turns"] == 0:
            # Look for Year pattern in filename (e.g., "Year69")
            import re

            xml_files = []
            try:
                with zipfile.ZipFile(self.zip_file_path, "r") as zip_file:
                    xml_files = zip_file.namelist()
            except:
                pass

            if xml_files:
                xml_filename = xml_files[0]
                year_match = re.search(r"Year(\d+)", xml_filename)
                if year_match:
                    metadata["total_turns"] = int(year_match.group(1))

        return metadata

    def extract_players(self) -> List[Dict[str, Any]]:
        """Extract player information from the save file.

        Returns:
            List of player dictionaries
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        players = []

        # Find all player elements that have OnlineID (human players)
        player_elements = self.root.findall(".//Player")

        for i, player_elem in enumerate(player_elements):
            # Only process players with OnlineID (human players)
            online_id = player_elem.get("OnlineID")
            if not online_id:
                continue

            # Extract civilization from Nation attribute
            nation = player_elem.get("Nation")
            civilization = None
            if nation:
                # Convert from NATION_PERSIA to Persia
                civilization = nation.replace("NATION_", "").replace("_", " ").title()

            # Get player name and normalize it for consistent matching
            original_name = player_elem.get("Name", f"Player {len(players)+1}").strip()

            player_data = {
                "player_name": original_name,
                "player_name_normalized": original_name.lower(),
                "civilization": civilization,
                "team_id": self._safe_int(player_elem.get("team")),
                "difficulty_level": player_elem.get("difficulty"),
                "final_score": self._safe_int(player_elem.get("score"), 0),
                "is_human": True,  # All players with OnlineID are human
                "final_turn_active": None,
            }

            # Try to determine the last turn this player was active
            player_id = player_elem.get("ID")
            if player_id:
                last_turn = self._find_last_active_turn(player_id)
                player_data["final_turn_active"] = last_turn

            players.append(player_data)

        return players

    def extract_game_states(self) -> List[Dict[str, Any]]:
        """Extract turn-by-turn game state information.

        Returns:
            List of game state dictionaries
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        game_states = []

        # Find all turn elements
        turn_elements = self.root.findall(".//Turn")

        for turn_elem in turn_elements:
            turn_number = self._safe_int(turn_elem.get("number"), 0)

            state_data = {
                "turn_number": turn_number,
                "active_player_id": self._safe_int(turn_elem.get("activePlayer")),
                "game_year": self._safe_int(turn_elem.get("year")),
                "turn_timestamp": self._parse_date(turn_elem.get("timestamp")),
            }

            game_states.append(state_data)

        return game_states

    def extract_events(self) -> List[Dict[str, Any]]:
        """Extract game events from MemoryData elements.

        MemoryData contains character and diplomatic memories stored by the game AI.
        This provides limited historical data compared to LogData.

        Player ID Mapping:
            - Owner Player: The Player[@ID] element that contains the MemoryList
              This is whose perspective/memory the event represents.

            - Subject Player: The <Player> child element inside MemoryData
              Only exists for MEMORYPLAYER_* events, represents the OTHER player.

            - For MEMORYPLAYER_*: Use subject player (the <Player> child)
            - For MEMORYTRIBE/FAMILY/RELIGION_*: Use owner player (parent Player[@ID])

            XML uses 0-based IDs, database uses 1-based:
                Example: XML Player[@ID="0"] → database player_id=1
                         XML Player[@ID="1"] → database player_id=2

        Returns:
            List of event dictionaries from memory data, with player IDs mapped
            to 1-based database IDs for consistency with LogData events.
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        events = []

        # Build lookup tables for resolving IDs to names
        character_lookup = self._build_character_lookup()
        city_lookup = self._build_city_lookup()

        # Iterate through Player elements to preserve ownership context
        for player_element in self.root.findall(".//Player[@ID]"):
            # Get the player ID who OWNS this MemoryList (0-based in XML)
            owner_xml_id = self._safe_int(player_element.get("ID"))
            if owner_xml_id is None:
                continue

            # Convert to 1-based database player_id
            owner_player_id = owner_xml_id + 1

            # Find this player's MemoryList
            memory_list = player_element.find("MemoryList")
            if memory_list is None:
                continue

            # Process all MemoryData elements within this player's list
            for mem in memory_list.findall("MemoryData"):
                # Extract basic memory event data
                turn_elem = mem.find("Turn")
                type_elem = mem.find("Type")

                if turn_elem is None or type_elem is None:
                    continue

                event_type = type_elem.text
                turn_number = self._safe_int(turn_elem.text)

                # Determine player_id based on event type:
                # - MEMORYPLAYER_*: Use the <Player> child (subject/opponent)
                # - MEMORYTRIBE/FAMILY/RELIGION_*: Use the owner player (viewer)
                player_elem = mem.find("Player")

                if player_elem is not None:
                    # MEMORYPLAYER_* events: <Player> child is the subject (0-based)
                    raw_subject_id = self._safe_int(player_elem.text)
                    player_id = (
                        (raw_subject_id + 1) if raw_subject_id is not None else None
                    )
                else:
                    # MEMORYTRIBE/FAMILY/RELIGION_* events: use owner
                    player_id = owner_player_id

                # Extract additional context fields (note: actual XML uses IDs)
                context_data = {}

                # Fields that are directly available as text
                text_fields = ["Religion", "Tribe", "Family", "Nation"]
                for field in text_fields:
                    elem = mem.find(field)
                    if elem is not None and elem.text:
                        # Format the value to be more readable
                        context_data[field.lower()] = self._format_context_value(
                            elem.text
                        )

                # Fields that are IDs and need lookup
                character_id_elem = mem.find("CharacterID")
                if character_id_elem is not None and character_id_elem.text:
                    char_id = self._safe_int(character_id_elem.text)
                    if char_id and char_id in character_lookup:
                        context_data["character"] = character_lookup[char_id]
                    else:
                        context_data["character_id"] = char_id

                city_id_elem = mem.find("CityID")
                if city_id_elem is not None and city_id_elem.text:
                    city_id = self._safe_int(city_id_elem.text)
                    if city_id and city_id in city_lookup:
                        context_data["city"] = city_lookup[city_id]
                    else:
                        context_data["city_id"] = city_id

                # Only include event_data if there's actual context data
                event_data_json = context_data if context_data else None

                event_data = {
                    "turn_number": turn_number,
                    "event_type": event_type,
                    "player_id": player_id,
                    "description": self._format_memory_event(event_type, context_data),
                    "x_coordinate": None,
                    "y_coordinate": None,
                    "event_data": event_data_json,
                }

                events.append(event_data)

        return events

    def extract_logdata_events(self) -> List[Dict[str, Any]]:
        """Extract game events from LogData elements in Player/PermanentLogList sections.

        LogData contains comprehensive turn-by-turn gameplay logs, providing much more
        detailed historical information than MemoryData. This includes:
        - Law adoptions (LAW_ADOPTED): Which laws were enacted and when
        - Tech discoveries (TECH_DISCOVERED): Complete tech tree progression
        - Goal tracking: Ambition start/completion events
        - City events: Founding, production, breaches

        The data comes from the PermanentLogList within each Player element, which
        maintains a complete history of significant game events throughout the match.

        Note on Player IDs:
            XML uses 0-based player IDs (ID="0", ID="1", etc.)
            Database uses 1-based player IDs (player_id=1, player_id=2, etc.)
            Conversion: database_player_id = xml_id + 1

        Returns:
            List of event dictionaries with keys:
                - turn_number: Turn when event occurred
                - event_type: Type of event (e.g., 'LAW_ADOPTED', 'TECH_DISCOVERED')
                - player_id: Database player ID (1-based)
                - description: Human-readable event description
                - x_coordinate: Optional X coordinate (None for LogData events)
                - y_coordinate: Optional Y coordinate (None for LogData events)
                - event_data: Optional JSON data with event-specific details

        Raises:
            ValueError: If XML not parsed yet (call extract_and_parse() first)
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        events = []

        # Find all Player elements with OnlineID (human players)
        player_elements = self.root.findall(".//Player[@OnlineID]")

        for player_elem in player_elements:
            # Get player's XML ID (0-based in XML)
            player_xml_id = player_elem.get("ID")
            if player_xml_id is None:
                continue

            # Convert to 1-based player_id for database
            # XML ID="0" is player 1, ID="1" is player 2
            player_id = int(player_xml_id) + 1

            # Find PermanentLogList for this player (main source of LogData)
            perm_log_list = player_elem.find(".//PermanentLogList")
            if perm_log_list is None:
                continue

            # Extract all LogData elements
            log_data_elements = perm_log_list.findall(".//LogData")

            for log_elem in log_data_elements:
                event = self._extract_single_logdata_event(log_elem, player_id)
                if event:
                    events.append(event)

        # Sort events by turn number for consistent ordering
        events.sort(key=lambda e: e["turn_number"])

        return events

    def _extract_single_logdata_event(
        self, log_elem: ET.Element, player_id: int
    ) -> Optional[Dict[str, Any]]:
        """Extract a single LogData event.

        LogData elements contain turn-by-turn gameplay logs. Each element has:
        - Type: Event type (LAW_ADOPTED, TECH_DISCOVERED, etc.)
        - Turn: Game turn number when event occurred
        - Data1/2/3: Event-specific data (e.g., law name, tech name)
        - Text: Human-readable description with HTML tags

        Args:
            log_elem: LogData XML element from PermanentLogList
            player_id: Database player ID (1-based, not XML ID which is 0-based)

        Returns:
            Event dictionary with standardized structure, or None if invalid/incomplete

        Note:
            Player IDs in XML are 0-based (ID="0", ID="1")
            Database player IDs are 1-based (player_id 1, 2, 3...)
            This method receives the already-converted database ID.
        """
        # Extract basic fields
        type_elem = log_elem.find("Type")
        turn_elem = log_elem.find("Turn")

        if type_elem is None or turn_elem is None:
            return None

        event_type = type_elem.text
        turn_number = self._safe_int(turn_elem.text)

        if turn_number is None:
            return None

        # Extract data fields
        data1_elem = log_elem.find("Data1")
        data2_elem = log_elem.find("Data2")
        data3_elem = log_elem.find("Data3")

        data1 = data1_elem.text if data1_elem is not None else None
        data2 = data2_elem.text if data2_elem is not None else None
        data3 = data3_elem.text if data3_elem is not None else None

        # Extract human-readable text
        text_elem = log_elem.find("Text")
        text = text_elem.text if text_elem is not None else None

        # Build event_data based on event type
        event_data = self._build_logdata_event_data(event_type, data1, data2, data3)

        # Build description
        description = self._format_logdata_event(event_type, event_data, text)

        return {
            "turn_number": turn_number,
            "event_type": event_type,
            "player_id": player_id,
            "description": description,
            "x_coordinate": None,
            "y_coordinate": None,
            "event_data": event_data if event_data else None,
        }

    def _build_logdata_event_data(
        self,
        event_type: str,
        data1: Optional[str],
        data2: Optional[str],
        data3: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Build event_data dict based on event type.

        Extracts structured data from LogData Data1/Data2/Data3 fields based on
        the event type. Different event types use these fields for different purposes:
        - LAW_ADOPTED: Data1 contains the law constant (e.g., 'LAW_SLAVERY')
        - TECH_DISCOVERED: Data1 contains the tech constant (e.g., 'TECH_WRITING')

        Args:
            event_type: Type of LogData event (e.g., 'LAW_ADOPTED', 'TECH_DISCOVERED')
            data1: Primary data field (most commonly used)
            data2: Secondary data field (event-specific usage)
            data3: Tertiary data field (event-specific usage)

        Returns:
            Dictionary of event data with event-specific keys, or None if no data to extract

        Note:
            Following YAGNI principle - only implement event types as needed.
            Additional event types can be added here when required.
        """
        if event_type == "LAW_ADOPTED" and data1:
            return {"law": data1}

        if event_type == "TECH_DISCOVERED" and data1:
            return {"tech": data1}

        # Add more event types as needed (YAGNI - only implement what we need now)

        return None

    def _format_logdata_event(
        self, event_type: str, event_data: Optional[Dict[str, Any]], text: Optional[str]
    ) -> str:
        """Format a LogData event into a readable description.

        Creates human-readable descriptions from LogData events by:
        1. Using event-specific formatting for known types (LAW_ADOPTED, TECH_DISCOVERED)
        2. Falling back to the Text field from XML (with HTML tags stripped)
        3. Finally falling back to the event type itself

        Args:
            event_type: Type of event (e.g., 'LAW_ADOPTED', 'TECH_DISCOVERED')
            event_data: Event data dictionary with event-specific keys
            text: Human-readable text from XML (may contain HTML tags like <link>)

        Returns:
            Human-readable description suitable for database storage

        Note:
            Text field often contains HTML markup (e.g., <link help="...">)
            which is stripped for clean database storage. Length is limited to
            200 characters to prevent database bloat.
        """
        if event_type == "LAW_ADOPTED" and event_data and "law" in event_data:
            # Convert LAW_SLAVERY -> Slavery
            law_name = event_data["law"].replace("LAW_", "").replace("_", " ").title()
            return f"Adopted {law_name}"

        if event_type == "TECH_DISCOVERED" and event_data and "tech" in event_data:
            # Convert TECH_WRITING -> Writing
            tech_name = (
                event_data["tech"].replace("TECH_", "").replace("_", " ").title()
            )
            return f"Discovered {tech_name}"

        # Fallback: use event type or text
        if text:
            # Strip HTML tags for database storage
            import re

            clean_text = re.sub(r"<[^>]+>", "", text)
            return clean_text[:200]  # Limit length

        # Final fallback: format event type as title
        return event_type.replace("_", " ").title()

    def _format_memory_event(
        self, event_type: str, context_data: Optional[Dict[str, str]] = None
    ) -> str:
        """Format a memory event type into a readable description.

        Args:
            event_type: Raw event type from MemoryData
            context_data: Optional dictionary of context information

        Returns:
            Human-readable event description
        """
        if not event_type:
            return "Unknown Event"

        # Remove MEMORY prefixes and format base description
        formatted = (
            event_type.replace("MEMORYPLAYER_", "")
            .replace("MEMORYTRIBE_", "")
            .replace("MEMORYFAMILY_", "")
            .replace("MEMORYRELIGION_", "")
            .replace("MEMORYNATION_", "")
            .replace("_", " ")
            .title()
        )

        # Append context if available
        if context_data:
            context_parts = []
            # Order matters for readability
            for key in ["tribe", "family", "religion", "nation", "city", "character"]:
                if key in context_data:
                    context_parts.append(context_data[key])

            if context_parts:
                formatted += f" ({', '.join(context_parts)})"

        return formatted

    def _format_context_value(self, value: str) -> str:
        """Format a context value to be more readable.

        Args:
            value: Raw context value (e.g., TRIBE_THRACIANS, NAME_GUNTHAMUND, CITYNAME_WASET)

        Returns:
            Formatted value (e.g., Thracians, Gunthamund, Waset)
        """
        if not value:
            return value

        # Remove common prefixes
        formatted = (
            value.replace("CITYNAME_", "")
            .replace("NAME_", "")
            .replace("TRIBE_", "")
            .replace("FAMILY_", "")
            .replace("RELIGION_", "")
            .replace("RELIGION_PAGAN_", "")
            .replace("NATION_", "")
            .replace("CITY_", "")
            .replace("CHARACTER_", "")
            .replace("_", " ")
            .title()
        )

        return formatted

    def extract_territories(self) -> List[Dict[str, Any]]:
        """Extract territory control information over time.

        Note: Old World save files only contain final state, not turn-by-turn history.
        This method returns an empty list as historical territory data is unavailable.

        Returns:
            Empty list (no historical territory data available)
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        # No turn-by-turn territory data available in save files
        return []

    def extract_resources(self) -> List[Dict[str, Any]]:
        """Extract player resource information over time.

        Note: Old World save files only contain final state, not turn-by-turn history.
        This method returns an empty list as historical resource data is unavailable.

        Returns:
            Empty list (no historical resource data available)
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        # No turn-by-turn resource data available in save files
        return []

    def extract_technology_progress(self) -> List[Dict[str, Any]]:
        """Extract technology research progress from player data.

        Returns:
            List of technology progress dictionaries with player_id (1-based), tech_name, and count
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        tech_progress = []

        # Find all player elements with OnlineID (human players)
        player_elements = self.root.findall(".//Player")
        player_index = 0  # Track actual player index for human players

        for player_elem in player_elements:
            # Only process players with OnlineID (human players)
            online_id = player_elem.get("OnlineID")
            if not online_id:
                continue

            player_index += 1

            # Find TechCount element
            tech_count_elem = player_elem.find(".//TechCount")
            if tech_count_elem is not None:
                for tech_elem in tech_count_elem:
                    tech_name = tech_elem.tag
                    count = self._safe_int(tech_elem.text, 0)

                    if count > 0:
                        tech_progress.append(
                            {
                                "player_id": player_index,  # 1-based index
                                "tech_name": tech_name,
                                "count": count,
                            }
                        )

        return tech_progress

    def extract_player_statistics(self) -> List[Dict[str, Any]]:
        """Extract player statistics including yield stockpile, bonuses, and law changes.

        Returns:
            List of player statistics dictionaries
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        statistics = []

        # Find all player elements with OnlineID (human players)
        player_elements = self.root.findall(".//Player")
        player_index = 0

        for player_elem in player_elements:
            # Only process players with OnlineID (human players)
            online_id = player_elem.get("OnlineID")
            if not online_id:
                continue

            player_index += 1

            # Extract YieldStockpile
            yield_stockpile = player_elem.find(".//YieldStockpile")
            if yield_stockpile is not None:
                for yield_elem in yield_stockpile:
                    stat_name = yield_elem.tag
                    value = self._safe_int(yield_elem.text, 0)

                    statistics.append(
                        {
                            "player_id": player_index,
                            "stat_category": "yield_stockpile",
                            "stat_name": stat_name,
                            "value": value,
                        }
                    )

            # Extract BonusCount
            bonus_count = player_elem.find(".//BonusCount")
            if bonus_count is not None:
                for bonus_elem in bonus_count:
                    stat_name = bonus_elem.tag
                    value = self._safe_int(bonus_elem.text, 0)

                    if value > 0:  # Only store non-zero values
                        statistics.append(
                            {
                                "player_id": player_index,
                                "stat_category": "bonus_count",
                                "stat_name": stat_name,
                                "value": value,
                            }
                        )

            # Extract LawClassChangeCount
            law_changes = player_elem.find(".//LawClassChangeCount")
            if law_changes is not None:
                for law_elem in law_changes:
                    stat_name = law_elem.tag
                    value = self._safe_int(law_elem.text, 0)

                    if value > 0:
                        statistics.append(
                            {
                                "player_id": player_index,
                                "stat_category": "law_changes",
                                "stat_name": stat_name,
                                "value": value,
                            }
                        )

        return statistics

    def extract_units_produced(self) -> List[Dict[str, Any]]:
        """Extract units produced by each player.

        Returns:
            List of units produced dictionaries
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        units_data = []

        # Find all player elements with OnlineID (human players)
        player_elements = self.root.findall(".//Player")
        player_index = 0

        for player_elem in player_elements:
            # Only process players with OnlineID (human players)
            online_id = player_elem.get("OnlineID")
            if not online_id:
                continue

            player_index += 1

            # Extract UnitsProduced
            units_produced = player_elem.find(".//UnitsProduced")
            if units_produced is not None:
                for unit_elem in units_produced:
                    unit_type = unit_elem.tag
                    count = self._safe_int(unit_elem.text, 0)

                    if count > 0:  # Only store non-zero values
                        units_data.append(
                            {
                                "player_id": player_index,
                                "unit_type": unit_type,
                                "count": count,
                            }
                        )

        return units_data

    def extract_match_metadata(self) -> Dict[str, Any]:
        """Extract detailed match metadata beyond basic info.

        Returns:
            Dictionary with match metadata
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        metadata = {}

        # Extract difficulty (from first human player)
        player_elements = self.root.findall(".//Player")
        for player_elem in player_elements:
            if player_elem.get("OnlineID"):
                difficulty = player_elem.get("Difficulty")
                if difficulty:
                    metadata["difficulty"] = (
                        difficulty.replace("HANDICAP_", "").replace("_", " ").title()
                    )
                break

        # Extract event level from root attributes
        event_level = self.root.get("EventLevel")
        if event_level:
            metadata["event_level"] = (
                event_level.replace("EVENTLEVEL_", "").replace("_", " ").title()
            )

        # Extract victory information
        team_victories = self.root.find(".//TeamVictoriesCompleted")
        if team_victories is not None:
            team_elem = team_victories.find(".//Team")
            if team_elem is not None:
                victory_type = team_elem.get("Victory")
                if victory_type:
                    metadata["victory_type"] = (
                        victory_type.replace("VICTORY_", "").replace("_", " ").title()
                    )

                # Try to extract victory turn
                turn_elem = team_elem.find("Turn")
                if turn_elem is not None and turn_elem.text:
                    metadata["victory_turn"] = self._safe_int(turn_elem.text)

        # Store game options as JSON
        import json

        game_options = {}

        # Extract various game option elements
        option_elements = self.root.findall(".//GameOptions/*")
        for opt in option_elements:
            if opt.text:
                game_options[opt.tag] = opt.text

        if game_options:
            metadata["game_options"] = json.dumps(game_options)

        # Extract DLC content
        dlc_content = {}
        dlc_elements = self.root.findall(".//DLC/*")
        for dlc in dlc_elements:
            if dlc.text:
                dlc_content[dlc.tag] = dlc.text

        if dlc_content:
            metadata["dlc_content"] = json.dumps(dlc_content)

        # Extract map settings
        map_settings = {}
        for attr_name in ["MapAspectRatio", "MapPeaks", "MapRivers", "MapResources"]:
            value = self.root.get(attr_name)
            if value:
                map_settings[attr_name] = value

        if map_settings:
            metadata["map_settings"] = json.dumps(map_settings)

        return metadata

    def determine_winner(self, players: List[Dict[str, Any]]) -> Optional[int]:
        """Determine the winner of the match based on victory conditions.

        Args:
            players: List of player dictionaries

        Returns:
            Player ID of the winner (1-based index), or None if undetermined
        """
        if not players:
            return None

        # Look for team victories (most reliable method)
        team_victories = self.root.find(".//TeamVictoriesCompleted")
        if team_victories is not None:
            # Get the first team that achieved victory
            team_elem = team_victories.find(".//Team")
            if team_elem is not None and team_elem.text:
                winning_team_id = self._safe_int(team_elem.text)
                if winning_team_id is not None:
                    # Find which player is on the winning team
                    # PlayerTeam elements are indexed by player ID
                    player_teams = self.root.findall(".//Team/PlayerTeam")
                    for player_idx, team_elem in enumerate(player_teams):
                        team_id = self._safe_int(team_elem.text)
                        if team_id == winning_team_id:
                            # Return 1-based player ID
                            return player_idx + 1

        # Look for explicit victory markers in the XML (fallback)
        victory_elem = self.root.find(".//Victory")
        if victory_elem is not None:
            winner_id = self._safe_int(victory_elem.get("winner"))
            if winner_id is not None:
                return winner_id

        # Fallback: determine by highest score
        max_score = -1
        winner_id = None

        for i, player in enumerate(players):
            score = player.get("final_score", 0)
            if score > max_score:
                max_score = score
                winner_id = i + 1  # 1-based player IDs

        return winner_id

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse a date string into a datetime object.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None

        # Try different date formats
        formats = [
            "%d %B %Y",  # Old World format: "20 September 2025"
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
            "%Y%m%d_%H%M%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _safe_int(
        self, value: Optional[str], default: Optional[int] = None
    ) -> Optional[int]:
        """Safely convert a string to integer.

        Args:
            value: String value to convert
            default: Default value if conversion fails

        Returns:
            Integer value or default
        """
        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _find_last_active_turn(self, player_id: str) -> Optional[int]:
        """Find the last turn a player was active.

        Args:
            player_id: Player ID to search for

        Returns:
            Last active turn number or None
        """
        if self.root is None:
            return None

        last_turn = None

        # Look through all turns for player activity
        turn_elements = self.root.findall(".//Turn")

        for turn_elem in turn_elements:
            turn_number = self._safe_int(turn_elem.get("number"))
            active_player = turn_elem.get("activePlayer")

            if active_player == player_id and turn_number is not None:
                last_turn = turn_number

        return last_turn

    def _build_character_lookup(self) -> Dict[int, str]:
        """Build a lookup table mapping character IDs to full names.

        Constructs full names from FirstName + Family when available.

        Returns:
            Dictionary mapping character ID to character full name
        """
        if self.root is None:
            return {}

        character_lookup = {}

        # Find all Character elements with ID and FirstName attributes
        for char_elem in self.root.findall(".//Character"):
            char_id = self._safe_int(char_elem.get("ID"))
            char_first_name = char_elem.get("FirstName")

            if char_id is not None and char_first_name:
                # Format the first name (e.g., NAME_GUNTHAMUND -> Gunthamund)
                formatted_first_name = self._format_context_value(char_first_name)

                # Try to get family name from Family child element
                family_elem = char_elem.find("Family")
                if family_elem is not None and family_elem.text:
                    family_name = self._format_context_value(family_elem.text)
                    # Construct full name: FirstName FamilyName
                    full_name = f"{formatted_first_name} {family_name}"
                else:
                    # No family name, use just first name
                    full_name = formatted_first_name

                character_lookup[char_id] = full_name

        return character_lookup

    def _build_city_lookup(self) -> Dict[int, str]:
        """Build a lookup table mapping city IDs to names.

        Returns:
            Dictionary mapping city ID to city name
        """
        if self.root is None:
            return {}

        city_lookup = {}

        # Find all City elements with ID and NameType child element
        for city_elem in self.root.findall(".//City"):
            city_id = self._safe_int(city_elem.get("ID"))
            name_type_elem = city_elem.find("NameType")

            if (
                city_id is not None
                and name_type_elem is not None
                and name_type_elem.text
            ):
                # Format the city name (e.g., CITYNAME_WASET -> Waset)
                formatted_name = self._format_context_value(name_type_elem.text)
                city_lookup[city_id] = formatted_name

        return city_lookup

    def _build_event_description(self, event_elem: ET.Element) -> str:
        """Build a description for an event element.

        Args:
            event_elem: XML element representing an event

        Returns:
            Human-readable event description
        """
        event_type = event_elem.tag

        # Build description based on event type and attributes
        if event_type == "Battle":
            attacker = event_elem.get("attacker")
            defender = event_elem.get("defender")
            return f"Battle between {attacker} and {defender}"
        elif event_type == "CityFounded":
            city_name = event_elem.get("name")
            return f"City founded: {city_name}"
        elif event_type == "TechDiscovered":
            tech_name = event_elem.get("tech")
            return f"Technology discovered: {tech_name}"
        else:
            return f"{event_type} event"

    def _extract_event_attributes(self, event_elem: ET.Element) -> Optional[str]:
        """Extract additional event data as JSON string.

        Args:
            event_elem: XML element representing an event

        Returns:
            JSON string of event attributes or None
        """
        import json

        # Get all attributes except the basic ones
        basic_attrs = {"turn", "player", "x", "y", "description"}
        extra_attrs = {
            key: value
            for key, value in event_elem.attrib.items()
            if key not in basic_attrs
        }

        if extra_attrs:
            try:
                return json.dumps(extra_attrs)
            except (TypeError, ValueError):
                pass

        return None

    def extract_points_history(self) -> List[Dict[str, Any]]:
        """Extract victory points progression from PointsHistory.

        Parses Player/PointsHistory elements which contain turn-by-turn
        victory point totals.

        Returns:
            List of points history dictionaries with:
            - player_id: Database player ID (1-based, converted from 0-based XML ID)
            - turn_number: Game turn number (extracted from TN tags)
            - points: Victory points for that turn

        Example XML:
            <Player ID="0" OnlineID="123">
                <PointsHistory>
                    <T2>1</T2>
                    <T3>2</T3>
                    <T4>5</T4>
                </PointsHistory>
            </Player>
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        points_data = []

        # Find all player elements with OnlineID (human players only)
        player_elements = self.root.findall(".//Player[@OnlineID]")

        for player_elem in player_elements:
            # Get player's XML ID (0-based)
            player_xml_id = player_elem.get("ID")
            if player_xml_id is None:
                continue

            # Convert to 1-based database player ID
            player_id = int(player_xml_id) + 1

            # Find PointsHistory element for this player
            points_history = player_elem.find(".//PointsHistory")
            if points_history is None:
                continue

            # Process each turn element (T2, T3, T4, ...)
            for turn_elem in points_history:
                turn_tag = turn_elem.tag  # e.g., "T2"

                # Skip if not a turn tag
                if not turn_tag.startswith("T"):
                    continue

                # Extract turn number from tag (T2 → 2)
                turn_number = self._safe_int(turn_tag[1:])
                points = self._safe_int(turn_elem.text)

                if turn_number is None or points is None:
                    continue

                points_data.append(
                    {"player_id": player_id, "turn_number": turn_number, "points": points}
                )

        return points_data

    def extract_yield_history(self) -> List[Dict[str, Any]]:
        """Extract yield production rates over time from YieldRateHistory.

        Parses Player/YieldRateHistory elements which contain turn-by-turn
        yield production rates for all yield types (GROWTH, CIVICS, TRAINING, etc.).

        Unlike other history types, yields are nested by type:
        <YieldRateHistory>
            <YIELD_GROWTH>
                <T2>100</T2>
                <T3>120</T3>
            </YIELD_GROWTH>
            <YIELD_CIVICS>
                <T2>50</T2>
                <T3>55</T3>
            </YIELD_CIVICS>
        </YieldRateHistory>

        Returns:
            List of yield history dictionaries with:
            - player_id: Database player ID (1-based)
            - turn_number: Game turn number
            - yield_type: Type of yield (YIELD_GROWTH, YIELD_CIVICS, etc.)
            - amount: Production rate for that yield on that turn
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        yield_data = []

        # Find all player elements with OnlineID (human players)
        player_elements = self.root.findall(".//Player[@OnlineID]")

        for player_elem in player_elements:
            # Get player's XML ID (0-based)
            player_xml_id = player_elem.get("ID")
            if player_xml_id is None:
                continue

            # Convert to 1-based player_id for database
            player_id = int(player_xml_id) + 1

            # Find YieldRateHistory for this player
            yield_history = player_elem.find(".//YieldRateHistory")
            if yield_history is None:
                continue

            # Process each yield type (YIELD_GROWTH, YIELD_CIVICS, etc.)
            for yield_type_elem in yield_history:
                yield_type = yield_type_elem.tag  # e.g., "YIELD_GROWTH"

                # Process each turn within this yield type (T2, T3, ...)
                for turn_elem in yield_type_elem:
                    turn_tag = turn_elem.tag  # e.g., "T2"

                    # Extract turn number from tag (T2 → 2)
                    if not turn_tag.startswith("T"):
                        continue

                    turn_number = self._safe_int(turn_tag[1:])
                    amount = self._safe_int(turn_elem.text)

                    if turn_number is None or amount is None:
                        continue

                    yield_data.append(
                        {
                            "player_id": player_id,
                            "turn_number": turn_number,
                            "yield_type": yield_type,
                            "amount": amount,
                        }
                    )

        return yield_data

    def extract_military_history(self) -> List[Dict[str, Any]]:
        """Extract military power progression from MilitaryPowerHistory.

        Returns:
            List of military history dictionaries with:
            - player_id: Database player ID (1-based)
            - turn_number: Game turn number
            - military_power: Military strength for that turn
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        military_data = []

        player_elements = self.root.findall(".//Player[@OnlineID]")

        for player_elem in player_elements:
            player_xml_id = player_elem.get("ID")
            if player_xml_id is None:
                continue

            player_id = int(player_xml_id) + 1

            military_history = player_elem.find(".//MilitaryPowerHistory")
            if military_history is None:
                continue

            for turn_elem in military_history:
                turn_tag = turn_elem.tag
                if not turn_tag.startswith("T"):
                    continue

                turn_number = self._safe_int(turn_tag[1:])
                military_power = self._safe_int(turn_elem.text)

                if turn_number is None or military_power is None:
                    continue

                military_data.append(
                    {
                        "player_id": player_id,
                        "turn_number": turn_number,
                        "military_power": military_power,
                    }
                )

        return military_data

    def extract_legitimacy_history(self) -> List[Dict[str, Any]]:
        """Extract legitimacy progression from LegitimacyHistory.

        Returns:
            List of legitimacy history dictionaries with:
            - player_id: Database player ID (1-based)
            - turn_number: Game turn number
            - legitimacy: Legitimacy value (0-100) for that turn
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        legitimacy_data = []

        player_elements = self.root.findall(".//Player[@OnlineID]")

        for player_elem in player_elements:
            player_xml_id = player_elem.get("ID")
            if player_xml_id is None:
                continue

            player_id = int(player_xml_id) + 1

            legitimacy_history = player_elem.find(".//LegitimacyHistory")
            if legitimacy_history is None:
                continue

            for turn_elem in legitimacy_history:
                turn_tag = turn_elem.tag
                if not turn_tag.startswith("T"):
                    continue

                turn_number = self._safe_int(turn_tag[1:])
                legitimacy = self._safe_int(turn_elem.text)

                if turn_number is None or legitimacy is None:
                    continue

                legitimacy_data.append(
                    {
                        "player_id": player_id,
                        "turn_number": turn_number,
                        "legitimacy": legitimacy,
                    }
                )

        return legitimacy_data

    def extract_opinion_histories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract family and religion opinion histories.

        Both follow the same nested pattern:
        <FamilyOpinionHistory>
            <FAMILY_NAME>
                <T2>100</T2>
                <T3>95</T3>
            </FAMILY_NAME>
        </FamilyOpinionHistory>

        Returns:
            Dictionary with two keys:
            - 'family_opinions': List of family opinion records
            - 'religion_opinions': List of religion opinion records

            Each record contains:
            - player_id: Database player ID (1-based)
            - turn_number: Game turn number
            - family_name/religion_name: Name of the family/religion
            - opinion: Opinion value (0-100) for that turn
        """
        if self.root is None:
            raise ValueError("XML not parsed. Call extract_and_parse() first.")

        family_opinions = []
        religion_opinions = []

        player_elements = self.root.findall(".//Player[@OnlineID]")

        for player_elem in player_elements:
            player_xml_id = player_elem.get("ID")
            if player_xml_id is None:
                continue

            player_id = int(player_xml_id) + 1

            # Extract family opinions
            family_history = player_elem.find(".//FamilyOpinionHistory")
            if family_history is not None:
                for family_elem in family_history:
                    family_name = family_elem.tag  # e.g., "FAMILY_JULII"

                    for turn_elem in family_elem:
                        turn_tag = turn_elem.tag
                        if not turn_tag.startswith("T"):
                            continue

                        turn_number = self._safe_int(turn_tag[1:])
                        opinion = self._safe_int(turn_elem.text)

                        if turn_number is None or opinion is None:
                            continue

                        family_opinions.append(
                            {
                                "player_id": player_id,
                                "turn_number": turn_number,
                                "family_name": family_name,
                                "opinion": opinion,
                            }
                        )

            # Extract religion opinions (same pattern)
            religion_history = player_elem.find(".//ReligionOpinionHistory")
            if religion_history is not None:
                for religion_elem in religion_history:
                    religion_name = religion_elem.tag  # e.g., "RELIGION_JUPITER"

                    for turn_elem in religion_elem:
                        turn_tag = turn_elem.tag
                        if not turn_tag.startswith("T"):
                            continue

                        turn_number = self._safe_int(turn_tag[1:])
                        opinion = self._safe_int(turn_elem.text)

                        if turn_number is None or opinion is None:
                            continue

                        religion_opinions.append(
                            {
                                "player_id": player_id,
                                "turn_number": turn_number,
                                "religion_name": religion_name,
                                "opinion": opinion,
                            }
                        )

        return {
            "family_opinions": family_opinions,
            "religion_opinions": religion_opinions,
        }


def parse_tournament_file(zip_file_path: str) -> Dict[str, Any]:
    """Parse a tournament save file and extract all data.

    Args:
        zip_file_path: Path to the tournament save zip file

    Returns:
        Dictionary containing all extracted data
    """
    parser = OldWorldSaveParser(zip_file_path)
    parser.extract_and_parse()

    # Extract all data components
    match_metadata = parser.extract_basic_metadata()
    players = parser.extract_players()
    game_states = parser.extract_game_states()

    # Extract both MemoryData and LogData events
    memory_events = (
        parser.extract_events()
    )  # MemoryData: MEMORY* event types (limited historical data)
    logdata_events = (
        parser.extract_logdata_events()
    )  # LogData: LAW_ADOPTED, TECH_DISCOVERED, etc. (comprehensive logs)

    # Merge both event sources
    # No deduplication needed - MemoryData and LogData have completely separate event type namespaces:
    #   - MemoryData: MEMORYPLAYER_*, MEMORYFAMILY_*, etc.
    #   - LogData: LAW_ADOPTED, TECH_DISCOVERED, GOAL_STARTED, etc.
    # They capture different types of historical information and can be safely concatenated.
    events = memory_events + logdata_events

    territories = parser.extract_territories()
    resources = parser.extract_resources()

    # Extract new statistics data
    technology_progress = parser.extract_technology_progress()
    player_statistics = parser.extract_player_statistics()
    units_produced = parser.extract_units_produced()
    detailed_metadata = parser.extract_match_metadata()

    # Extract turn-by-turn history data
    yield_history = parser.extract_yield_history()
    points_history = parser.extract_points_history()
    military_history = parser.extract_military_history()
    legitimacy_history = parser.extract_legitimacy_history()
    opinion_histories = parser.extract_opinion_histories()

    # Determine winner
    winner_player_id = parser.determine_winner(players)
    match_metadata["winner_player_id"] = winner_player_id

    return {
        "match_metadata": match_metadata,
        "players": players,
        "game_states": game_states,
        "events": events,
        "territories": territories,
        "resources": resources,
        "technology_progress": technology_progress,
        "player_statistics": player_statistics,
        "units_produced": units_produced,
        "detailed_metadata": detailed_metadata,
        # Turn-by-turn history data
        "yield_history": yield_history,
        "points_history": points_history,
        "military_history": military_history,
        "legitimacy_history": legitimacy_history,
        "family_opinion_history": opinion_histories["family_opinions"],
        "religion_opinion_history": opinion_histories["religion_opinions"],
    }
