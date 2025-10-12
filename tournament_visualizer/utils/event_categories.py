"""Event categorization utilities for meaningful grouping of game events.

This module provides categorization of Old World game events into meaningful
gameplay categories like Military, Diplomacy, Technology, etc.
"""

from typing import Dict


def get_event_category(event_type: str) -> str:
    """Categorize an event type into a meaningful gameplay category.

    Args:
        event_type: The raw event type string (e.g., "TECH_DISCOVERED", "MEMORYPLAYER_ATTACKED_CITY")

    Returns:
        Human-readable category name (e.g., "Technology & Research", "Military & Combat")
    """
    # Normalize to uppercase for consistent matching
    event_upper = event_type.upper()

    # Military & Combat
    if any(
        keyword in event_upper
        for keyword in [
            "ATTACK",
            "RAID",
            "BREACHED",
            "RAZED",
            "SIEGE",
            "WAR",
            "BATTLE",
            "INVASION",
            "KILLED_UNIT",
            "CAPTURE",
        ]
    ):
        return "Military & Combat"

    # Technology & Research (including Laws)
    if any(
        keyword in event_upper
        for keyword in ["TECH_", "LAW_", "RESEARCH", "DISCOVERED", "ADOPTED"]
    ):
        return "Technology & Laws"

    # Diplomatic Actions
    if any(
        keyword in event_upper
        for keyword in [
            "DIPLOMACY",
            "ALLIANCE",
            "PEACE",
            "TREATY",
            "CONTACT",
            "TRUCE",
            "TRIBUTE",
            "GIFT",
            "DEMANDED",
            "OFFER",
        ]
    ):
        return "Diplomacy"

    # Character Events (births, deaths, marriages, relationships)
    if any(
        keyword in event_upper
        for keyword in [
            "CHARACTER_BIRTH",
            "CHARACTER_DEATH",
            "CHARACTER_SUCCESSION",
            "MARRIED",
            "DIVORCED",
            "COURTIER",
            "SPOUSE",
            "HEIR",
            "SUCCESSION",
            "ROMANCE",
            "FRIEND",
            "RIVAL",
        ]
    ):
        return "Character Events"

    # City Development & Infrastructure
    if any(
        keyword in event_upper
        for keyword in [
            "CITY_FOUNDED",
            "WONDER_",
            "IMPROVEMENT",
            "SPECIALIST",
            "HURRIED",
            "BUILT",
        ]
    ):
        return "City Development"

    # Goals & Achievements
    if any(
        keyword in event_upper
        for keyword in ["GOAL_", "ACHIEVEMENT", "AMBITION", "QUEST"]
    ):
        return "Goals & Achievements"

    # Religion & Culture
    if any(
        keyword in event_upper
        for keyword in ["RELIGION_", "THEOLOGY_", "SHRINE", "PROPHET", "HOLY"]
    ):
        return "Religion & Culture"

    # Family & Dynasty
    if "FAMILY" in event_upper or "DYNASTY" in event_upper:
        return "Family & Dynasty"

    # Tribal Relations (specific to tribes, not general diplomacy)
    if "TRIBE" in event_upper and not any(
        keyword in event_upper
        for keyword in ["CONTACT", "DIPLOMACY", "PEACE", "WAR", "ALLIANCE"]
    ):
        return "Tribal Relations"

    # Special Events & Occurrences (random narrative events)
    if any(keyword in event_upper for keyword in ["OCCURRENCE", "EVENT_", "DISASTER"]):
        return "Special Events"

    # Default catch-all
    return "Other"


def get_category_color_map() -> Dict[str, str]:
    """Get color mapping for event categories.

    Returns:
        Dictionary mapping category names to hex color codes
    """
    return {
        "Military & Combat": "#dc3545",  # Red - danger/combat
        "Technology & Laws": "#0d6efd",  # Blue - knowledge
        "Diplomacy": "#198754",  # Green - peace/cooperation
        "Character Events": "#ffc107",  # Yellow - personal/dramatic
        "City Development": "#6f42c1",  # Purple - growth/building
        "Goals & Achievements": "#fd7e14",  # Orange - accomplishment
        "Religion & Culture": "#20c997",  # Teal - spiritual
        "Family & Dynasty": "#d63384",  # Pink - relationships
        "Tribal Relations": "#795548",  # Brown - external relations
        "Special Events": "#17a2b8",  # Cyan - random/special
        "Other": "#6c757d",  # Gray - miscellaneous
    }


def get_category_icon_map() -> Dict[str, str]:
    """Get Bootstrap icon mapping for event categories.

    Returns:
        Dictionary mapping category names to Bootstrap icon class names
    """
    return {
        "Military & Combat": "bi-shield-fill-exclamation",
        "Technology & Laws": "bi-lightbulb-fill",
        "Diplomacy": "bi-chat-dots-fill",
        "Character Events": "bi-person-fill",
        "City Development": "bi-building-fill",
        "Goals & Achievements": "bi-trophy-fill",
        "Religion & Culture": "bi-star-fill",
        "Family & Dynasty": "bi-heart-fill",
        "Tribal Relations": "bi-people-fill",
        "Special Events": "bi-lightning-fill",
        "Other": "bi-question-circle-fill",
    }
