"""Evaluation suite for the natural language SQL query system.

Runs test fixtures through the NL query pipeline and checks results against
expectations. Catches regressions when changing the system prompt or SQL
extraction logic.

Usage:
    uv run python scripts/eval_nl_query.py                  # Run all tests
    uv run python scripts/eval_nl_query.py --tag regression  # Run only regression tests
    uv run python scripts/eval_nl_query.py --tag coverage    # Run only coverage tests
    uv run python scripts/eval_nl_query.py --unit            # Run only unit tests (no API calls)
    uv run python scripts/eval_nl_query.py --id carthage_win_rate  # Run one test
    uv run python scripts/eval_nl_query.py --dry-run         # Show what would run
"""

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tournament_visualizer.data.nl_query import (
    NLQueryService,
    QueryResult,
    _extract_sql,
    _validate_sql,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

FIXTURES_PATH = Path(__file__).parent / "eval_nl_fixtures.json"

# Rate limit: pause between API calls to stay within Groq free tier
API_CALL_DELAY_SECONDS = 3.0


@dataclass
class CheckResult:
    """Result of a single check within a test case."""

    check_name: str
    passed: bool
    detail: str = ""


@dataclass
class TestResult:
    """Result of running a single test case."""

    test_id: str
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    sql: str = ""
    error: str = ""
    row_count: int = 0
    columns: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


def _find_column_by_pattern(columns: list[str], pattern: str) -> Optional[str]:
    """Find the first column matching a regex pattern (case-insensitive)."""
    regex = re.compile(pattern, re.IGNORECASE)
    for col in columns:
        if regex.search(col):
            return col
    return None


def run_query_test(
    service: NLQueryService, test_case: dict
) -> TestResult:
    """Run a single query test case against the live service."""
    test_id = test_case["id"]
    question = test_case["question"]

    start = time.monotonic()
    result = service.ask(question)
    duration = time.monotonic() - start

    tr = TestResult(
        test_id=test_id,
        passed=True,
        sql=result.sql,
        error=result.error_message,
        row_count=len(result.df) if result.success else 0,
        columns=list(result.df.columns) if result.success else [],
        duration_seconds=round(duration, 1),
    )

    # Check: expect_success
    expect_success = test_case.get("expect_success", True)
    check = CheckResult(
        check_name="expect_success",
        passed=result.success == expect_success,
        detail=f"expected success={expect_success}, got success={result.success}"
        + (f" error='{result.error_message}'" if result.error_message else ""),
    )
    tr.checks.append(check)

    if not result.success and not expect_success:
        # Expected failure — skip remaining checks
        tr.passed = all(c.passed for c in tr.checks)
        return tr

    if not result.success:
        # Unexpected failure — skip remaining checks
        tr.passed = False
        return tr

    # Check: sql_must_contain
    for pattern in test_case.get("sql_must_contain", []):
        found = pattern.lower() in result.sql.lower()
        tr.checks.append(
            CheckResult(
                check_name=f"sql_must_contain: {pattern}",
                passed=found,
                detail=f"{'found' if found else 'NOT found'} in SQL",
            )
        )

    # Check: sql_must_not_contain
    for pattern in test_case.get("sql_must_not_contain", []):
        found = pattern.lower() in result.sql.lower()
        tr.checks.append(
            CheckResult(
                check_name=f"sql_must_not_contain: {pattern}",
                passed=not found,
                detail=f"{'found (BAD)' if found else 'not found (good)'} in SQL",
            )
        )

    # Check: sql_must_not_contain_pattern (regex)
    for pattern in test_case.get("sql_must_not_contain_pattern", []):
        found = bool(re.search(pattern, result.sql, re.IGNORECASE))
        tr.checks.append(
            CheckResult(
                check_name=f"sql_must_not_contain_pattern: {pattern}",
                passed=not found,
                detail=f"{'matched (BAD)' if found else 'no match (good)'} in SQL",
            )
        )

    # Check: expected_columns_any (at least one must be present)
    if "expected_columns_any" in test_case:
        expected = test_case["expected_columns_any"]
        cols_lower = [c.lower() for c in result.df.columns]
        found_any = any(e.lower() in cols_lower for e in expected)
        tr.checks.append(
            CheckResult(
                check_name=f"expected_columns_any: {expected}",
                passed=found_any,
                detail=f"columns: {list(result.df.columns)}",
            )
        )

    # Check: min_rows / max_rows
    if "min_rows" in test_case:
        passed = len(result.df) >= test_case["min_rows"]
        tr.checks.append(
            CheckResult(
                check_name=f"min_rows: {test_case['min_rows']}",
                passed=passed,
                detail=f"got {len(result.df)} rows",
            )
        )

    if "max_rows" in test_case:
        passed = len(result.df) <= test_case["max_rows"]
        tr.checks.append(
            CheckResult(
                check_name=f"max_rows: {test_case['max_rows']}",
                passed=passed,
                detail=f"got {len(result.df)} rows",
            )
        )

    # Check: unique_column_pattern (no duplicate values in a column)
    if "unique_column_pattern" in test_case:
        col = _find_column_by_pattern(
            list(result.df.columns), test_case["unique_column_pattern"]
        )
        if col is None:
            tr.checks.append(
                CheckResult(
                    check_name=f"unique_column_pattern: {test_case['unique_column_pattern']}",
                    passed=False,
                    detail=f"no column matching pattern in {list(result.df.columns)}",
                )
            )
        else:
            dupes = result.df[col].duplicated().sum()
            tr.checks.append(
                CheckResult(
                    check_name=f"unique_column: {col}",
                    passed=dupes == 0,
                    detail=f"{dupes} duplicate values"
                    + (
                        f" (e.g. {list(result.df[result.df[col].duplicated(keep=False)][col].unique()[:3])})"
                        if dupes > 0
                        else ""
                    ),
                )
            )

    # Check: value_checks
    for vc in test_case.get("value_checks", []):
        col = _find_column_by_pattern(list(result.df.columns), vc["column_pattern"])
        if col is None:
            tr.checks.append(
                CheckResult(
                    check_name=f"value_check: {vc.get('description', vc['column_pattern'])}",
                    passed=False,
                    detail=f"no column matching '{vc['column_pattern']}' in {list(result.df.columns)}",
                )
            )
            continue

        row_idx = vc.get("row", 0)
        if row_idx >= len(result.df):
            tr.checks.append(
                CheckResult(
                    check_name=f"value_check: {vc.get('description', col)}",
                    passed=False,
                    detail=f"row {row_idx} doesn't exist (only {len(result.df)} rows)",
                )
            )
            continue

        val = result.df.iloc[row_idx][col]
        try:
            val_float = float(val)
        except (TypeError, ValueError):
            tr.checks.append(
                CheckResult(
                    check_name=f"value_check: {vc.get('description', col)}",
                    passed=False,
                    detail=f"value '{val}' is not numeric",
                )
            )
            continue

        in_range = vc.get("min", float("-inf")) <= val_float <= vc.get(
            "max", float("inf")
        )
        tr.checks.append(
            CheckResult(
                check_name=f"value_check: {vc.get('description', col)}",
                passed=in_range,
                detail=f"{col}[{row_idx}] = {val_float} (expected {vc.get('min', '-inf')}-{vc.get('max', 'inf')})",
            )
        )

    # Check: result_must_contain (specific values in a column)
    if "result_must_contain" in test_case:
        rmc = test_case["result_must_contain"]
        col = _find_column_by_pattern(list(result.df.columns), rmc["column_pattern"])
        if col is None:
            tr.checks.append(
                CheckResult(
                    check_name="result_must_contain",
                    passed=False,
                    detail=f"no column matching '{rmc['column_pattern']}' in {list(result.df.columns)}",
                )
            )
        else:
            actual_values = set(str(v) for v in result.df[col].tolist())
            for expected_val in rmc["values"]:
                # Case-insensitive substring match
                found = any(
                    expected_val.lower() in av.lower() for av in actual_values
                )
                tr.checks.append(
                    CheckResult(
                        check_name=f"result_must_contain: {expected_val}",
                        passed=found,
                        detail=f"{'found' if found else 'NOT found'} in column '{col}'",
                    )
                )

    tr.passed = all(c.passed for c in tr.checks)
    return tr


def run_safety_test(
    service: NLQueryService, test_case: dict
) -> TestResult:
    """Run a safety test — queries that should be rejected."""
    test_id = test_case["id"]
    question = test_case["question"]

    start = time.monotonic()
    result = service.ask(question)
    duration = time.monotonic() - start

    tr = TestResult(
        test_id=test_id,
        passed=True,
        sql=result.sql,
        error=result.error_message,
        duration_seconds=round(duration, 1),
    )

    if test_case.get("expect_success") is False:
        # Must fail — either LLM refuses, SQL validation catches it, or execution fails
        check = CheckResult(
            check_name="expect_failure",
            passed=not result.success,
            detail=f"success={result.success}, error='{result.error_message}'",
        )
        tr.checks.append(check)
    elif test_case.get("expect_success_or_safe_sql"):
        # LLM might generate a harmless SELECT or might refuse — both are OK
        if result.success:
            # If it succeeded, verify the SQL is a safe SELECT (no DML)
            validation = _validate_sql(result.sql) if result.sql else None
            check = CheckResult(
                check_name="safe_sql_if_success",
                passed=validation is None,
                detail=f"SQL validation: {validation or 'passed'}",
            )
        else:
            check = CheckResult(
                check_name="safe_sql_if_success",
                passed=True,
                detail="Query was rejected (safe)",
            )
        tr.checks.append(check)

    tr.passed = all(c.passed for c in tr.checks)
    return tr


def run_extraction_test(test_case: dict) -> TestResult:
    """Run a SQL extraction unit test (no API call)."""
    test_id = test_case["id"]
    input_text = test_case["input"]
    expected = test_case["expected_sql"]

    actual = _extract_sql(input_text)

    tr = TestResult(test_id=test_id, passed=True, sql=actual or "")

    if expected is None:
        check = CheckResult(
            check_name="expect_no_sql",
            passed=actual is None,
            detail=f"expected None, got: {repr(actual)}" if actual else "correctly returned None",
        )
    else:
        check = CheckResult(
            check_name="extract_sql",
            passed=actual is not None and actual.strip().rstrip(";") == expected.strip().rstrip(";"),
            detail=f"expected: {repr(expected)}, got: {repr(actual)}",
        )

    tr.checks.append(check)
    tr.passed = check.passed
    return tr


def print_result(tr: TestResult, verbose: bool = False) -> None:
    """Print a single test result."""
    status = "\033[32mPASS\033[0m" if tr.passed else "\033[31mFAIL\033[0m"
    timing = f" ({tr.duration_seconds}s)" if tr.duration_seconds > 0 else ""
    row_info = f" [{tr.row_count} rows]" if tr.row_count > 0 else ""

    print(f"  {status}  {tr.test_id}{timing}{row_info}")

    if not tr.passed or verbose:
        for check in tr.checks:
            check_icon = "    \033[32m+\033[0m" if check.passed else "    \033[31m-\033[0m"
            print(f"{check_icon} {check.check_name}: {check.detail}")
        if tr.sql and (not tr.passed or verbose):
            # Show first 200 chars of SQL for failed tests
            sql_preview = tr.sql[:200] + ("..." if len(tr.sql) > 200 else "")
            print(f"    SQL: {sql_preview}")
        if tr.error:
            print(f"    Error: {tr.error}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the natural language SQL query system"
    )
    parser.add_argument(
        "--tag",
        help="Only run test cases with this tag",
    )
    parser.add_argument(
        "--id",
        help="Only run the test case with this ID",
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Only run unit tests (SQL extraction, no API calls)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which tests would run without executing them",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show details for passing tests too",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=API_CALL_DELAY_SECONDS,
        help=f"Seconds between API calls (default: {API_CALL_DELAY_SECONDS})",
    )
    args = parser.parse_args()

    # Load fixtures
    with open(FIXTURES_PATH) as f:
        fixtures = json.load(f)

    results: list[TestResult] = []

    # --- Unit tests (SQL extraction) ---
    extraction_tests = fixtures.get("sql_extraction_tests", [])
    if args.id:
        extraction_tests = [t for t in extraction_tests if t["id"] == args.id]

    if extraction_tests and not (args.tag and args.tag != "unit"):
        print("\n\033[1mSQL Extraction Tests\033[0m")
        print("=" * 60)
        for tc in extraction_tests:
            if args.dry_run:
                print(f"  SKIP  {tc['id']} (dry run)")
                continue
            tr = run_extraction_test(tc)
            results.append(tr)
            print_result(tr, args.verbose)

    if args.unit:
        # Only unit tests requested — print summary and exit
        _print_summary(results)
        sys.exit(0 if all(r.passed for r in results) else 1)

    # --- Query tests (require API) ---
    service = NLQueryService()

    query_tests = fixtures.get("test_cases", [])
    if args.tag:
        query_tests = [t for t in query_tests if args.tag in t.get("tags", [])]
    if args.id:
        query_tests = [t for t in query_tests if t["id"] == args.id]

    if query_tests:
        print(f"\n\033[1mQuery Tests ({len(query_tests)} cases)\033[0m")
        print("=" * 60)
        for i, tc in enumerate(query_tests):
            if args.dry_run:
                tags = ", ".join(tc.get("tags", []))
                print(f"  SKIP  {tc['id']} [{tags}]: {tc['question']}")
                continue

            # Rate limiting between API calls
            if i > 0:
                time.sleep(args.delay)

            tr = run_query_test(service, tc)
            results.append(tr)
            print_result(tr, args.verbose)

    # --- Safety tests ---
    safety_tests = fixtures.get("safety_tests", [])
    if args.id:
        safety_tests = [t for t in safety_tests if t["id"] == args.id]

    if safety_tests and not args.tag:
        print(f"\n\033[1mSafety Tests ({len(safety_tests)} cases)\033[0m")
        print("=" * 60)
        for i, tc in enumerate(safety_tests):
            if args.dry_run:
                print(f"  SKIP  {tc['id']}: {tc['question']}")
                continue

            if i > 0 or query_tests:
                time.sleep(args.delay)

            tr = run_safety_test(service, tc)
            results.append(tr)
            print_result(tr, args.verbose)

    _print_summary(results)
    sys.exit(0 if all(r.passed for r in results) else 1)


def _print_summary(results: list[TestResult]) -> None:
    """Print final summary."""
    if not results:
        print("\nNo tests were run.")
        return

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total_time = sum(r.duration_seconds for r in results)

    print()
    print("=" * 60)
    color = "\033[32m" if failed == 0 else "\033[31m"
    print(
        f"{color}{passed}/{len(results)} passed, {failed} failed\033[0m"
        f" ({total_time:.1f}s total)"
    )

    if failed > 0:
        print(f"\nFailed tests:")
        for r in results:
            if not r.passed:
                failed_names = [c.check_name for c in r.failed_checks]
                print(f"  - {r.test_id}: {', '.join(failed_names)}")


if __name__ == "__main__":
    main()
