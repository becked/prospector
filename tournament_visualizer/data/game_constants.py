"""Game constants for Old World tournament analysis.

This module contains classification dictionaries and mappings used for timeline
event categorization and display.
"""

from pathlib import Path
from typing import Optional

# Base path for icon assets on filesystem
_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "icons"

# Tech types classified by thematic focus: science, civics, training, growth
# All 43 non-bonus techs from database
TECH_TYPES: dict[str, str] = {
    "TECH_ADMINISTRATION": "growth",  # Granary, Treasury, Caravansary
    "TECH_ARCHITECTURE": "civics",  # Courthouse, Colosseum
    "TECH_ARISTOCRACY": "civics",  # Council, Chancellor
    "TECH_BALLISTICS": "training",  # Ballista, Siege improvements
    "TECH_BATTLELINE": "training",  # Swordsman, formation combat
    "TECH_BODKIN_ARROW": "training",  # Marksman archer upgrade
    "TECH_CARTOGRAPHY": "growth",  # Harbor, trade routes
    "TECH_CITIZENSHIP": "civics",  # Legal Code law, civic buildings
    "TECH_COHORTS": "training",  # Legion, military organization
    "TECH_COINAGE": "growth",  # Mint, economic buildings
    "TECH_COMPOSITE_BOW": "training",  # Archer unit
    "TECH_DIVINATION": "science",  # Shrine, Oracle, religious knowledge
    "TECH_DOCTRINE": "civics",  # Cathedral, religious civics
    "TECH_DRAMA": "growth",  # Theater, Odeon, culture
    "TECH_ECONOMIC_REFORM": "growth",  # Market, economic improvements
    "TECH_FORESTRY": "growth",  # Lumbermill, resource extraction
    "TECH_HUSBANDRY": "growth",  # Pasture, animal resources
    "TECH_HYDRAULICS": "civics",  # Aqueduct, public works
    "TECH_INFANTRY_SQUARE": "training",  # Spearman formations
    "TECH_IRONWORKING": "training",  # Warrior, basic military
    "TECH_JURISPRUDENCE": "civics",  # Laws, legal system
    "TECH_LABOR_FORCE": "growth",  # Quarry, resource production
    "TECH_LAND_CONSOLIDATION": "growth",  # Farm improvements
    "TECH_MACHINERY": "civics",  # Workshop, engineering
    "TECH_MANOR": "growth",  # Manor house, rural economy
    "TECH_MARTIAL_CODE": "training",  # Military laws and discipline
    "TECH_METAPHYSICS": "science",  # Academy, philosophical knowledge
    "TECH_MILITARY_DRILL": "training",  # Officer, military training
    "TECH_MONASTICISM": "science",  # Monastery, religious scholarship
    "TECH_NAVIGATION": "growth",  # Port, naval trade
    "TECH_PHALANX": "training",  # Spearman unit
    "TECH_POLIS": "civics",  # City governance
    "TECH_PORTCULLIS": "civics",  # Stronghold, defensive civics
    "TECH_RHETORIC": "civics",  # Ambassador, diplomacy
    "TECH_SCHOLARSHIP": "science",  # Library, knowledge buildings
    "TECH_SOVEREIGNTY": "civics",  # Throne, royal authority
    "TECH_SPOKED_WHEEL": "training",  # Chariot unit
    "TECH_STEEL": "training",  # Advanced military equipment
    "TECH_STIRRUPS": "training",  # Horseman improvements
    "TECH_STONECUTTING": "growth",  # Quarry, stone resources
    "TECH_TRAPPING": "training",  # Scout, Hunter units
    "TECH_VAULTING": "civics",  # Basilica, monumental buildings
    "TECH_WINDLASS": "training",  # Crossbowman unit
}

# Law classes group mutually exclusive laws (adopting one replaces the other)
LAW_CLASSES: dict[str, list[str]] = {
    "slavery_freedom": ["LAW_SLAVERY", "LAW_FREEDOM"],
    "centralization_vassalage": ["LAW_CENTRALIZATION", "LAW_VASSALAGE"],
    "colonies_serfdom": ["LAW_COLONIES", "LAW_SERFDOM"],
    "monotheism_polytheism": ["LAW_MONOTHEISM", "LAW_POLYTHEISM"],
    "tyranny_constitution": ["LAW_TYRANNY", "LAW_CONSTITUTION"],
    "epics_exploration": ["LAW_EPICS", "LAW_EXPLORATION"],
    "divine_rule_legal_code": ["LAW_DIVINE_RULE", "LAW_LEGAL_CODE"],
    "guilds_elites": ["LAW_GUILDS", "LAW_ELITES"],
    "iconography_calligraphy": ["LAW_ICONOGRAPHY", "LAW_CALLIGRAPHY"],
    "philosophy_engineering": ["LAW_PHILOSOPHY", "LAW_ENGINEERING"],
    "professional_army_volunteers": ["LAW_PROFESSIONAL_ARMY", "LAW_VOLUNTEERS"],
    "tolerance_orthodoxy": ["LAW_TOLERANCE", "LAW_ORTHODOXY"],
}

# Succession laws to ignore (not shown in timeline, not competitive choices)
IGNORED_LAWS: set[str] = {"LAW_PRIMOGENITURE", "LAW_SENIORITY", "LAW_ULTIMOGENITURE"}

# Reverse lookup: law -> class name
LAW_TO_CLASS: dict[str, str] = {
    law: class_name for class_name, laws in LAW_CLASSES.items() for law in laws
}

# Timeline icons for event display
TIMELINE_ICONS: dict[str, str] = {
    "tech": "🔬",
    "law": "⚖️",
    "law_swap": "⚖️",
    "wonder_start": "🏗️",
    "wonder_complete": "🏛️",
    "city": "🏠",
    "city_lost": "🏚️",
    "capital": "🏰",
    "ruler": "👑",
    "death": "💀",
    "battle": "⚔️",
    "uu_unlock": "🗡️",
    "ambition": "🏆",
    "religion": "⛪",
}

# Event type priority for sorting (lower number = higher priority)
# Death appears before crowning to show narrative flow: ruler dies -> new ruler crowned
EVENT_PRIORITY: dict[str, int] = {
    "death": 1,
    "ruler": 2,
    "capital": 3,
    "religion": 4,  # Religion founding after capital, before city
    "city": 5,
    "city_lost": 6,
    "uu_unlock": 7,
    "ambition": 8,  # Ambition completion after uu_unlock, before law
    "law": 9,
    "law_swap": 10,
    "tech": 11,
    "wonder_complete": 12,
    "wonder_start": 13,
    "battle": 14,
}

# =============================================================================
# Icon Path Mappings for Timeline Display
# =============================================================================
# All paths are relative to Dash assets folder (/assets/icons/...)

ICON_BASE_PATH = "/assets/icons"

# Ruler archetype icons - maps archetype name to icon filename
ARCHETYPE_ICONS: dict[str, str] = {
    "Builder": f"{ICON_BASE_PATH}/traits/TRAIT_BUILDER.png",
    "Commander": f"{ICON_BASE_PATH}/traits/TRAIT_COMMANDER.png",
    "Diplomat": f"{ICON_BASE_PATH}/traits/TRAIT_DIPLOMAT.png",
    "Hero": f"{ICON_BASE_PATH}/traits/TRAIT_HERO.png",
    "Judge": f"{ICON_BASE_PATH}/traits/TRAIT_JUDGE.png",
    "Orator": f"{ICON_BASE_PATH}/traits/TRAIT_ORATOR.png",
    "Schemer": f"{ICON_BASE_PATH}/traits/TRAIT_SCHEMER.png",
    "Scholar": f"{ICON_BASE_PATH}/traits/TRAIT_SCHOLAR.png",
    "Tactician": f"{ICON_BASE_PATH}/traits/TRAIT_TACTICIAN.png",
    "Zealot": f"{ICON_BASE_PATH}/traits/TRAIT_ZEALOT.png",
}


def get_tech_icon_path(tech_name: str) -> Optional[str]:
    """Get icon path for a technology.

    Args:
        tech_name: Display name like "Forestry" or "Military Drill"

    Returns:
        Icon path like "/assets/icons/techs/TECH_FORESTRY.png", or None if not found
    """
    tech_key = f"TECH_{tech_name.upper().replace(' ', '_')}"
    icon_file = _ASSETS_DIR / "techs" / f"{tech_key}.png"
    if icon_file.exists():
        return f"{ICON_BASE_PATH}/techs/{tech_key}.png"
    return None


def get_law_icon_path(law_name: str) -> Optional[str]:
    """Get icon path for a law.

    Args:
        law_name: Display name like "Slavery" or "Professional Army"

    Returns:
        Icon path like "/assets/icons/laws/LAW_SLAVERY.png", or None if not found
    """
    law_key = f"LAW_{law_name.upper().replace(' ', '_')}"
    icon_file = _ASSETS_DIR / "laws" / f"{law_key}.png"
    if icon_file.exists():
        return f"{ICON_BASE_PATH}/laws/{law_key}.png"
    return None


# Wonder name mappings for localized names and special cases
WONDER_NAME_MAPPINGS: dict[str, str] = {
    # English names -> improvement key (without IMPROVEMENT_ prefix)
    "Acropolis": "ACROPOLIS",
    "Apadana": "APADANA",
    "Circus Maximus": "CIRCUS_MAXIMUS",
    "Colosseum": "COLOSSEUM",
    "Colossus": "COLOSSUS",
    "Cothon": "COTHON",
    "Hanging Gardens": "HANGING_GARDENS",
    "Heliopolis": "HELIOPOLIS",
    "Ishtar Gate": "ISHTAR_GATE",
    "Jebel Barkal": "JEBEL_BARKAL",
    "Jerwan Aqueduct": "JERWAN_AQUEDUCT",
    "Lighthouse": "LIGHTHOUSE",
    "Mausoleum": "MAUSOLEUM",
    "Musaeum": "MUSAEUM",
    "Necropolis": "NECROPOLIS",
    "Oracle": "ORACLE",
    "Pantheon": "PANTHEON",
    "Pyramids": "PYRAMIDS",
    "Yazilikaya": "YAZILIKAYA",
    "Ziggurat": "GREAT_ZIGGURAT",
    # German names
    "Hängende Gärten": "HANGING_GARDENS",
    "Jervan-Aquädukt": "JERWAN_AQUEDUCT",
    "Nekropole": "NECROPOLIS",
    # Russian names (transliterated)
    "Висячие сады": "HANGING_GARDENS",
    "Акрополь": "ACROPOLIS",
    "Джерванский акведук": "JERWAN_AQUEDUCT",
    "Зиккурат": "GREAT_ZIGGURAT",
    "Мавзолей": "MAUSOLEUM",
}


# Family-to-archetype mappings by nation
NATION_FAMILIES: dict[str, dict[str, str]] = {
    "Assyria": {
        "Sargonid": "Champions",
        "Tudiya": "Hunters",
        "Adasi": "Patrons",
        "Erishum": "Clerics",
    },
    "Babylonia": {
        "Kassite": "Hunters",
        "Chaldean": "Artisans",
        "Isin": "Traders",
        "Amorite": "Sages",
    },
    "Carthage": {
        "Barcid": "Riders",
        "Magonid": "Artisans",
        "Hannonid": "Traders",
        "Didonian": "Statesmen",
    },
    "Egypt": {
        "Ramesside": "Riders",
        "Saite": "Landowners",
        "Amarna": "Clerics",
        "Thutmosid": "Sages",
    },
    "Greece": {
        "Argead": "Champions",
        "Cypselid": "Artisans",
        "Seleucid": "Patrons",
        "Alcmaeonid": "Sages",
    },
    "Persia": {
        "Sasanid": "Clerics",
        "Mihranid": "Hunters",
        "Arsacid": "Riders",
        "Achaemenid": "Statesmen",
    },
    "Rome": {
        "Fabius": "Champions",
        "Claudius": "Landowners",
        "Valerius": "Patrons",
        "Julius": "Statesmen",
    },
    "Hittite": {
        "Kussaran": "Riders",
        "Nenassan": "Landowners",
        "Zalpuwan": "Patrons",
        "Hattusan": "Traders",
    },
    "Kush": {
        "Yam": "Hunters",
        "Irtjet": "Artisans",
        "Wawat": "Traders",
        "Setju": "Landowners",
    },
    "Aksum": {
        "Agaw": "Champions",
        "Agazi": "Traders",
        "Tigrayan": "Clerics",
        "Barya": "Patrons",
    },
}

# Reverse lookup: family name -> archetype (flattened from NATION_FAMILIES)
FAMILY_TO_ARCHETYPE: dict[str, str] = {
    family: archetype
    for nation_families in NATION_FAMILIES.values()
    for family, archetype in nation_families.items()
}


def get_family_crest_icon_path(family_name: str, is_seat: bool = False) -> Optional[str]:
    """Get icon path for a family crest based on archetype.

    Args:
        family_name: Database family name like "FAMILY_BARCID", display name like "Barcid",
                     or direct archetype like "ARCHETYPE_CLERICS"
        is_seat: If True, return the seat (capital) version of the crest

    Returns:
        Icon path like "/assets/icons/crests/CREST_ARCHETYPE_RIDERS.png", or None if not found
    """
    # Handle direct archetype reference (from event_data for rebel/captured cities)
    if family_name.startswith("ARCHETYPE_"):
        archetype = family_name.replace("ARCHETYPE_", "")
        suffix = "_SEAT" if is_seat else ""
        crest_key = f"CREST_ARCHETYPE_{archetype.upper()}{suffix}"
        icon_file = _ASSETS_DIR / "crests" / f"{crest_key}.png"
        if icon_file.exists():
            return f"{ICON_BASE_PATH}/crests/{crest_key}.png"
        return None

    # Strip FAMILY_ prefix if present and capitalize
    name = family_name.replace("FAMILY_", "").replace("_", " ").title().replace(" ", "")

    # Handle names like "AKSUM_AGAW" -> "Agaw"
    if "_" in family_name:
        parts = family_name.replace("FAMILY_", "").split("_")
        name = parts[-1].title()  # Take last part (the actual family name)

    archetype = FAMILY_TO_ARCHETYPE.get(name)
    if not archetype:
        return None

    suffix = "_SEAT" if is_seat else ""
    crest_key = f"CREST_ARCHETYPE_{archetype.upper()}{suffix}"
    icon_file = _ASSETS_DIR / "crests" / f"{crest_key}.png"
    if icon_file.exists():
        return f"{ICON_BASE_PATH}/crests/{crest_key}.png"
    return None


def get_wonder_icon_path(wonder_name: str) -> Optional[str]:
    """Get icon path for a wonder.

    Args:
        wonder_name: Display name like "The Hanging Gardens" or "Pyramids"

    Returns:
        Icon path like "/assets/icons/wonders/IMPROVEMENT_HANGING_GARDENS.png",
        or None if not found
    """
    # Strip "The " prefix if present
    name = wonder_name.strip()
    if name.startswith("The "):
        name = name[4:]

    # Check mapping first for localized names
    if name in WONDER_NAME_MAPPINGS:
        wonder_key = f"IMPROVEMENT_{WONDER_NAME_MAPPINGS[name]}"
    else:
        # Try direct conversion
        wonder_key = f"IMPROVEMENT_{name.upper().replace(' ', '_')}"

    icon_file = _ASSETS_DIR / "wonders" / f"{wonder_key}.png"
    if icon_file.exists():
        return f"{ICON_BASE_PATH}/wonders/{wonder_key}.png"
    return None


def get_nation_crest_icon_path(civilization: str) -> Optional[str]:
    """Get icon path for a nation crest.

    Args:
        civilization: Civilization name like "Carthage", "CARTHAGE", or "NATION_CARTHAGE"

    Returns:
        Icon path like "/assets/icons/crests/CREST_NATION_CARTHAGE.png" or None
    """
    if not civilization:
        return None
    name = civilization.upper().replace("NATION_", "")
    # Handle HATTI/HITTITE alias (game uses Hatti internally, assets use Hittite)
    if name == "HATTI":
        name = "HITTITE"
    icon_file = _ASSETS_DIR / "crests" / f"CREST_NATION_{name}.png"
    if icon_file.exists():
        return f"{ICON_BASE_PATH}/crests/CREST_NATION_{name}.png"
    return None
