"""Game constants for Old World tournament analysis.

This module contains classification dictionaries and mappings used for timeline
event categorization and display.
"""

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
}

# Event type priority for sorting (lower number = higher priority)
# Death appears before crowning to show narrative flow: ruler dies -> new ruler crowned
EVENT_PRIORITY: dict[str, int] = {
    "death": 1,
    "ruler": 2,
    "capital": 3,
    "city": 4,
    "city_lost": 5,
    "uu_unlock": 6,
    "law": 7,
    "law_swap": 8,
    "tech": 9,
    "wonder_complete": 10,
    "wonder_start": 11,
    "battle": 12,
}
