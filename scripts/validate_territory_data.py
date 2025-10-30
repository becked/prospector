"""Validate territory tile detail data after import.

Checks:
- Specialist assignments are on valid tiles
- Improvements exist where expected
- Resources match improvement types
- Data consistency across matches
"""

import logging
from tournament_visualizer.data.database import TournamentDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_specialist_counts() -> bool:
    """Verify specialist assignments look reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        COUNT(*) as total_tiles_with_specialists,
        COUNT(DISTINCT specialist_type) as unique_specialist_types,
        COUNT(*) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    WHERE specialist_type IS NOT NULL
    """

    with db.get_connection() as conn:
        result = conn.execute(query).fetchone()
    matches, total, unique_types, avg = result

    logger.info(f"Specialist validation:")
    logger.info(f"  Matches with specialists: {matches}")
    logger.info(f"  Total specialist assignments: {total}")
    logger.info(f"  Unique specialist types: {unique_types}")
    logger.info(f"  Average per match: {avg:.1f}")

    # Sanity checks
    if unique_types < 5:
        logger.error(f"Too few specialist types: {unique_types} (expected 10+)")
        return False

    if avg < 10:
        logger.warning(f"Low average specialists per match: {avg:.1f}")

    return True


def validate_improvement_counts() -> bool:
    """Verify improvement distribution looks reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        COUNT(*) as total_tiles_with_improvements,
        COUNT(DISTINCT improvement_type) as unique_improvement_types,
        COUNT(*) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    WHERE improvement_type IS NOT NULL
    """

    with db.get_connection() as conn:
        result = conn.execute(query).fetchone()
    matches, total, unique_types, avg = result

    logger.info(f"\nImprovement validation:")
    logger.info(f"  Matches with improvements: {matches}")
    logger.info(f"  Total improvement tiles: {total}")
    logger.info(f"  Unique improvement types: {unique_types}")
    logger.info(f"  Average per match: {avg:.1f}")

    # Sanity checks
    if unique_types < 10:
        logger.error(f"Too few improvement types: {unique_types} (expected 20+)")
        return False

    if avg < 50:
        logger.warning(f"Low average improvements per match: {avg:.1f}")

    return True


def validate_resource_counts() -> bool:
    """Verify resource distribution looks reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        COUNT(*) as total_tiles_with_resources,
        COUNT(DISTINCT resource_type) as unique_resource_types,
        COUNT(*) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    WHERE resource_type IS NOT NULL
    """

    with db.get_connection() as conn:
        result = conn.execute(query).fetchone()
    matches, total, unique_types, avg = result

    logger.info(f"\nResource validation:")
    logger.info(f"  Matches with resources: {matches}")
    logger.info(f"  Total resource tiles: {total}")
    logger.info(f"  Unique resource types: {unique_types}")
    logger.info(f"  Average per match: {avg:.1f}")

    # Sanity checks
    if unique_types < 10:
        logger.error(f"Too few resource types: {unique_types} (expected 20+)")
        return False

    return True


def validate_road_counts() -> bool:
    """Verify road network data looks reasonable."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        COUNT(DISTINCT match_id) as matches,
        SUM(CASE WHEN has_road THEN 1 ELSE 0 END) as total_road_tiles,
        SUM(CASE WHEN has_road THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT match_id) as avg_per_match
    FROM territories
    """

    with db.get_connection() as conn:
        result = conn.execute(query).fetchone()
    matches, total, avg = result

    logger.info(f"\nRoad validation:")
    logger.info(f"  Matches with roads: {matches}")
    logger.info(f"  Total road tiles: {total}")
    logger.info(f"  Average per match: {avg:.1f}")

    if avg < 10:
        logger.warning(f"Low average road tiles per match: {avg:.1f}")

    return True


def validate_specialist_improvement_correlation() -> bool:
    """Check that specialists are on appropriate improvement types."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    query = """
    SELECT
        specialist_type,
        improvement_type,
        COUNT(*) as count
    FROM territories
    WHERE specialist_type IS NOT NULL
    GROUP BY specialist_type, improvement_type
    ORDER BY specialist_type, count DESC
    """

    with db.get_connection() as conn:
        results = conn.execute(query).fetchall()

    logger.info(f"\nSpecialist-Improvement correlation:")
    logger.info(f"  (Checking specialists are on appropriate tiles)")

    for spec_type, imp_type, count in results[:20]:  # Top 20
        logger.info(f"  {spec_type} on {imp_type}: {count}")

    # Look for known good patterns
    expected_patterns = [
        ("SPECIALIST_MINER", "IMPROVEMENT_MINE"),
        ("SPECIALIST_RANCHER", "IMPROVEMENT_PASTURE"),
        ("SPECIALIST_STONECUTTER", "IMPROVEMENT_QUARRY"),
    ]

    found_patterns = {(r[0], r[1]) for r in results}

    for spec, imp in expected_patterns:
        if (spec, imp) in found_patterns:
            logger.info(f"  ✓ Found expected pattern: {spec} on {imp}")
        else:
            logger.warning(f"  ⚠ Missing expected pattern: {spec} on {imp}")

    return True


def validate_sample_match() -> bool:
    """Deep dive into one match to verify data quality."""
    db = TournamentDatabase("data/tournament_data.duckdb")

    with db.get_connection() as conn:
        # Get first match with specialists
        query = """
        SELECT DISTINCT match_id
        FROM territories
        WHERE specialist_type IS NOT NULL
        LIMIT 1
        """
        match_id = conn.execute(query).fetchone()[0]

        logger.info(f"\nSample match deep dive (match_id={match_id}):")

        # Check final turn snapshot
        query = """
        SELECT
            COUNT(*) as total_tiles,
            COUNT(DISTINCT terrain_type) as terrain_types,
            COUNT(improvement_type) as tiles_with_improvements,
            COUNT(specialist_type) as tiles_with_specialists,
            COUNT(resource_type) as tiles_with_resources,
            SUM(CASE WHEN has_road THEN 1 ELSE 0 END) as tiles_with_roads,
            MAX(turn_number) as final_turn
        FROM territories
        WHERE match_id = ?
        GROUP BY turn_number
        ORDER BY turn_number DESC
        LIMIT 1
        """

        result = conn.execute(query, [match_id]).fetchone()

    if result:
        tiles, terrains, imps, specs, res, roads, turn = result
        logger.info(f"  Final turn: {turn}")
        logger.info(f"  Total tiles: {tiles}")
        logger.info(f"  Terrain types: {terrains}")
        logger.info(f"  Tiles with improvements: {imps}")
        logger.info(f"  Tiles with specialists: {specs}")
        logger.info(f"  Tiles with resources: {res}")
        logger.info(f"  Tiles with roads: {roads}")

        if specs == 0:
            logger.warning("  No specialists found in sample match")
            return False

    return True


def main() -> int:
    """Run all validation checks."""
    logger.info("=" * 60)
    logger.info("Territory Tile Detail Validation")
    logger.info("=" * 60)

    checks = [
        ("Specialist counts", validate_specialist_counts),
        ("Improvement counts", validate_improvement_counts),
        ("Resource counts", validate_resource_counts),
        ("Road counts", validate_road_counts),
        ("Specialist-Improvement correlation", validate_specialist_improvement_correlation),
        ("Sample match", validate_sample_match),
    ]

    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"Check '{name}' failed with error: {e}")
            results.append((name, False))

    logger.info("\n" + "=" * 60)
    logger.info("Validation Summary")
    logger.info("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        logger.info("\n✓ All validation checks passed!")
        return 0
    else:
        logger.error("\n✗ Some validation checks failed")
        return 1


if __name__ == "__main__":
    exit(main())
