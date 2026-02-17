"""Generate AI-powered narrative summaries from structured match analysis data.

Uses the pre-computed analysis from match_card.analyze_match() as input,
generating narratives in a single LLM pass per narrative (no extraction
pass needed since the data is already structured).

Three narratives per match:
1. Match summary - overall match story arc
2. Player 1 narrative - P1's strategy and performance
3. Player 2 narrative - P2's strategy and performance

Example:
    >>> from tournament_visualizer.config import Config
    >>> generator = NarrativeGenerator(api_key=Config.ANTHROPIC_API_KEY)
    >>> summary = generator.generate_match_summary(analysis)
    >>> p1_narrative = generator.generate_player_narrative(analysis, "p1")
"""

import logging
from typing import Any

from anthropic.types import MessageParam

from tournament_visualizer.data.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """Generate narrative summaries from structured match analysis data.

    Takes the output of analyze_match() and produces prose narratives
    via single-pass LLM calls.

    Attributes:
        client: AnthropicClient instance
        model: Model name to use
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-20250514",
    ) -> None:
        """Initialize narrative generator.

        Args:
            api_key: Anthropic API key
            model: Model name to use

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.client = AnthropicClient(api_key=api_key)
        self.model = model

    def generate_match_summary(self, analysis: dict[str, Any]) -> str:
        """Generate the overall match narrative summary.

        Args:
            analysis: Full analysis dict from analyze_match()

        Returns:
            2-3 paragraph narrative summary
        """
        match_id = analysis.get("match_id")
        logger.info(f"Generating match summary for match {match_id}")

        serialized = serialize_analysis(analysis)

        prompt = f"""You are writing a narrative summary for a competitive Old World tournament match. Old World is a historical 4X strategy game set in the ancient world.

Here is the structured analysis data for this match:

{serialized}

IMPORTANT context for interpreting the data:
- Player profile stats (cities, army, yields) are END-OF-GAME snapshots. A low city count may reflect cities lost to the opponent, not a deliberate strategy. Cross-reference Key Events (city_lost entries) to understand what actually happened.
- In Army composition, "Support" means civilian workers who build improvements, NOT military support units. A high Support % means the player built many workers, not that they had a support-heavy army. Treat army composition as showing military breakdown (Infantry, Ranged, Cavalry, Siege) plus worker count (Support) separately.

Write a concise 2-3 paragraph narrative summary of this match. Focus on:
- The overall story arc: how did the match unfold from opening to conclusion?
- The key turning point(s) that decided the outcome
- What made this match distinctive (the archetype and decisive factors)

Each paragraph should be just a couple sentences.

Write in past tense. Be specific about turn numbers when referencing events. Make it engaging but factual -- this is for a tournament stats dashboard, not a novel. Avoid cliches and hyperbole. Be fairly succinct.

DO NOT include section headers, bullet points, or labels. Just write the narrative prose. Do not start with the players' names -- start with something that establishes the character of the match."""

        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        narrative = self.client.generate_text(messages=messages, model=self.model)
        narrative = narrative.strip()

        logger.info(f"Match {match_id}: Generated summary ({len(narrative)} chars)")
        return narrative

    def generate_player_narrative(
        self, analysis: dict[str, Any], player_key: str
    ) -> str:
        """Generate a player-specific empire narrative.

        Args:
            analysis: Full analysis dict from analyze_match()
            player_key: "p1" or "p2"

        Returns:
            Single paragraph player narrative
        """
        match_id = analysis.get("match_id")
        profile = analysis.get(f"{player_key}_profile", {})
        player_name = profile.get("player_name", "Unknown")
        civilization = profile.get("civilization", "Unknown")

        winner_name = analysis.get("winner_name", "")
        won_or_lost = "winning" if player_name == winner_name else "losing"

        logger.info(
            f"Generating {player_key} narrative for match {match_id} ({player_name})"
        )

        serialized = serialize_analysis(analysis)

        prompt = f"""You are writing a brief empire profile narrative for {player_name} ({civilization}) in a competitive Old World tournament match.

Here is the structured analysis data for this match:

{serialized}

IMPORTANT context for interpreting the data:
- Player profile stats (cities, army, yields) are END-OF-GAME snapshots. A low city count may reflect cities lost to the opponent, not a deliberate strategy. Cross-reference Key Events (city_lost entries) to understand what actually happened.
- In Army composition, "Support" means civilian workers who build improvements, NOT military support units. A high Support % means the player built many workers, not that they had a support-heavy army. Treat army composition as showing military breakdown (Infantry, Ranged, Cavalry, Siege) plus worker count (Support) separately.

Write a 2-3 sentences describing {player_name}'s strategy and performance in this match. Cover:
- Their strategic approach (expansion pace, economic focus, military posture)
- Key decisions or moments that actually affected the outcome
- How their strategy contributed to {won_or_lost} the match

Focus on what mattered for the result, not just listing achievements.

Make sure to put newlines between paragraphs.

Write in past tense. Be concise and factual. This text appears inside an empire profile card on a dashboard, so brevity is important.

DO NOT include section headers or labels. Just write the narrative prose."""

        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        narrative = self.client.generate_text(messages=messages, model=self.model)
        narrative = narrative.strip()

        logger.info(
            f"Match {match_id}: Generated {player_key} narrative ({len(narrative)} chars)"
        )
        return narrative


def serialize_analysis(analysis: dict[str, Any]) -> str:
    """Convert analysis dict into concise readable text for LLM prompts.

    Produces a structured but human-readable representation that is more
    token-efficient than raw JSON.

    Args:
        analysis: Full analysis dict from analyze_match()

    Returns:
        Formatted text block
    """
    p1_name, p2_name = analysis.get("player_names", ("Player 1", "Player 2"))
    p1_civ, p2_civ = analysis.get("civilizations", ("Unknown", "Unknown"))
    winner_name = analysis.get("winner_name", "Unknown")
    total_turns = analysis.get("total_turns", 0)
    avg_turns = analysis.get("avg_turns", 0)

    vp_analysis = analysis.get("vp_analysis", {})
    territory = analysis.get("territory_analysis", {})
    p1_profile = analysis.get("p1_profile", {})
    p2_profile = analysis.get("p2_profile", {})
    key_events = analysis.get("key_events", [])
    summary = analysis.get("summary", {})
    yield_comparison = analysis.get("yield_comparison", {})

    lines: list[str] = []

    # Match header
    turns_str = f"{total_turns} turns (average {avg_turns})" if avg_turns else f"{total_turns} turns"
    lines.append(f"Match: {p1_name} ({p1_civ}) vs {p2_name} ({p2_civ}), {turns_str}")
    lines.append(f"Winner: {winner_name}")
    lines.append("")

    # VP Analysis
    lines.append("VP Analysis:")
    lines.append(f"  Lead changes: {vp_analysis.get('total_lead_changes', 0)}")
    perm = vp_analysis.get("permanent_lead_turn")
    lines.append(f"  Permanent lead established: {'turn ' + str(perm) if perm else 'never'}")
    lines.append(
        f"  Max {p1_name} lead: {vp_analysis.get('max_p1_lead', 0)} VP "
        f"(turn {vp_analysis.get('max_p1_lead_turn', '?')})"
    )
    lines.append(
        f"  Max {p2_name} lead: {vp_analysis.get('max_p2_lead', 0)} VP "
        f"(turn {vp_analysis.get('max_p2_lead_turn', '?')})"
    )
    lines.append("")

    # Player profiles
    for label, profile, exp_key in [
        (f"{p1_name} ({p1_civ})", p1_profile, "p1"),
        (f"{p2_name} ({p2_civ})", p2_profile, "p2"),
    ]:
        tags = profile.get("playstyle_tags", {})
        lines.append(f"Player: {label}")

        # Army composition (only non-zero)
        army = profile.get("army_composition", {})
        army_parts = [
            f"{k} {v:.0%}" for k, v in army.items() if v and v > 0
        ]
        if army_parts:
            lines.append(f"  Army: {', '.join(army_parts)}")

        lines.append(f"  Economy: {tags.get('economy', '?')}")
        lines.append(f"  Wonders built: {profile.get('wonders_built', 0)}")
        lines.append(f"  Cities (end of game): {territory.get(f'{exp_key}_final_cities', 0)}")

        # Laws from summary
        player_name = profile.get("player_name", "")
        laws_info = summary.get("laws", {}).get(player_name, {})
        if laws_info:
            law_str = f"{laws_info.get('total', 0)} laws"
            swaps = laws_info.get("swaps", 0)
            if swaps:
                law_str += f", {swaps} swap{'s' if swaps != 1 else ''}"
            lines.append(f"  Laws: {law_str}")

        wonder_count = summary.get("wonders", {}).get(player_name, {}).get("count", 0)
        if wonder_count:
            lines.append(f"  Wonders completed: {wonder_count}")

        lines.append("")

    # Key events
    if key_events:
        player_names_dict = dict(
            zip(analysis.get("player_ids", ()), analysis.get("player_names", ()))
        )
        lines.append("Key Events:")
        for evt in key_events:
            turn = evt.get("turn", "?")
            title = evt.get("title", "")
            evt_type = evt.get("event_type", "")
            pid = evt.get("player_id")
            pname = player_names_dict.get(pid, "")
            if pname:
                lines.append(f"  Turn {turn}: {pname} - {title} [{evt_type}]")
            else:
                lines.append(f"  Turn {turn}: {title} [{evt_type}]")
        lines.append("")

    # Yield comparison
    if yield_comparison:
        lines.append("Yield Comparison:")
        for key, data in yield_comparison.items():
            name = data.get("display_name", key)
            p1_total = data.get("p1_total", 0)
            p2_total = data.get("p2_total", 0)
            lines.append(f"  {name}: {p1_name} {p1_total:.0f} vs {p2_name} {p2_total:.0f}")

    return "\n".join(lines)
