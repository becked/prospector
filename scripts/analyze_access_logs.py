"""Analyze access logs from the Fly.io persistent volume.

Pulls access.log from the deployed app via `fly ssh console` and reports
visitor and page analytics.

Usage:
    uv run python scripts/analyze_access_logs.py visitors              # Unique visitor summary
    uv run python scripts/analyze_access_logs.py visitors --daily      # Daily breakdown
    uv run python scripts/analyze_access_logs.py visitors --monthly    # Monthly breakdown
    uv run python scripts/analyze_access_logs.py visitors --all        # Everything

    uv run python scripts/analyze_access_logs.py pages                 # Page visit summary
    uv run python scripts/analyze_access_logs.py pages --daily         # Daily breakdown
    uv run python scripts/analyze_access_logs.py pages --monthly       # Monthly breakdown
    uv run python scripts/analyze_access_logs.py pages --all           # Everything
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

APP_NAME = "prospector"
LOG_PATH = "/data/logs/access.log"

# Matches the X-Forwarded-For IP(s) at the start, then the date in brackets
# Example: 74.108.139.73, 66.241.125.158 - - [19/Feb/2026:19:24:26 +0000] "GET / HTTP/1.1" ...
LOG_PATTERN = re.compile(
    r'^([\d., ]+)\s+-\s+-\s+\[(\d{2}/\w{3}/\d{4}):\d{2}:\d{2}:\d{2}\s+[+\-]\d{4}\]\s+"(\w+)\s+(\S+)'
)

# Map URL paths to friendly page names
PAGE_NAMES: dict[str, str] = {
    "/": "Overview",
    "/matches": "Matches",
    "/players": "Players",
    "/maps": "Maps",
    "/chat": "Chat",
}

# Reverse lookup: friendly name -> bare path (for detecting query-param-only URLs)
PAGE_NAMES_INV: dict[str, str] = {v: k for k, v in PAGE_NAMES.items()}

# Paths that aren't real page visits
SKIP_PATHS = {"/health", "/favicon.ico"}


def fetch_logs() -> str:
    """Pull access log contents from the Fly.io machine."""
    result = subprocess.run(
        ["fly", "ssh", "console", "--app", APP_NAME, "-C", f"cat {LOG_PATH}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error fetching logs: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def parse_logs(raw: str) -> list[dict[str, str]]:
    """Parse log lines into structured records, filtering out health checks and static assets."""
    records: list[dict[str, str]] = []
    for line in raw.strip().splitlines():
        if "Consul Health Check" in line:
            continue

        match = LOG_PATTERN.match(line)
        if not match:
            continue

        ip_chain, date_str, method, path = match.groups()

        # First IP in X-Forwarded-For is the real client
        client_ip = ip_chain.split(",")[0].strip()

        # Skip static asset requests and Dash internals
        if path.startswith("/_dash-") or path.startswith("/assets/") or path.startswith("/_favicon"):
            continue

        # Skip health checks and other non-page paths
        parsed = urlparse(path)
        if parsed.path in SKIP_PATHS:
            continue

        # Normalize to base page path (strip query params for grouping)
        base_path = parsed.path.rstrip("/") or "/"
        page_name = PAGE_NAMES.get(base_path, base_path)

        records.append({
            "ip": client_ip,
            "date": date_str,
            "method": method,
            "path": path,
            "page": page_name,
        })
    return records


# ---------------------------------------------------------------------------
# Visitors subcommand
# ---------------------------------------------------------------------------

def visitors_total(records: list[dict[str, str]]) -> None:
    """Print total unique visitor count."""
    unique_ips = {r["ip"] for r in records}
    print(f"\n{'='*40}")
    print(f" Total unique visitors: {len(unique_ips)}")
    print(f" Total page requests:   {len(records)}")
    print(f"{'='*40}")

    if unique_ips:
        ip_counts: dict[str, int] = defaultdict(int)
        for r in records:
            ip_counts[r["ip"]] += 1
        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)

        print(f"\n Top visitors:")
        for ip, count in sorted_ips[:10]:
            print(f"   {ip:<20s} {count:>4d} requests")


def visitors_daily(records: list[dict[str, str]]) -> None:
    """Print daily unique visitor breakdown."""
    daily: dict[str, set[str]] = defaultdict(set)
    daily_requests: dict[str, int] = defaultdict(int)
    for r in records:
        daily[r["date"]].add(r["ip"])
        daily_requests[r["date"]] += 1

    sorted_dates = sorted(
        daily.keys(),
        key=lambda d: datetime.strptime(d, "%d/%b/%Y"),
    )

    print(f"\n{'='*40}")
    print(f" Daily unique visitors")
    print(f"{'='*40}")
    print(f" {'Date':<15s} {'Unique':>7s} {'Requests':>9s}")
    print(f" {'-'*15} {'-'*7} {'-'*9}")
    for date in sorted_dates:
        print(f" {date:<15s} {len(daily[date]):>7d} {daily_requests[date]:>9d}")


def visitors_monthly(records: list[dict[str, str]]) -> None:
    """Print monthly unique visitor breakdown."""
    monthly: dict[str, set[str]] = defaultdict(set)
    monthly_requests: dict[str, int] = defaultdict(int)
    for r in records:
        dt = datetime.strptime(r["date"], "%d/%b/%Y")
        month_key = dt.strftime("%Y-%m")
        monthly[month_key].add(r["ip"])
        monthly_requests[month_key] += 1

    sorted_months = sorted(monthly.keys())

    print(f"\n{'='*40}")
    print(f" Monthly unique visitors")
    print(f"{'='*40}")
    print(f" {'Month':<10s} {'Unique':>7s} {'Requests':>9s}")
    print(f" {'-'*10} {'-'*7} {'-'*9}")
    for month in sorted_months:
        print(f" {month:<10s} {len(monthly[month]):>7d} {monthly_requests[month]:>9d}")


# ---------------------------------------------------------------------------
# Pages subcommand
# ---------------------------------------------------------------------------

def pages_total(records: list[dict[str, str]]) -> None:
    """Print page visit counts with full URL detail per category."""
    # Category-level summary
    cat_hits: dict[str, int] = defaultdict(int)
    cat_visitors: dict[str, set[str]] = defaultdict(set)
    # Full-path detail grouped by category
    path_hits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    path_visitors: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for r in records:
        cat_hits[r["page"]] += 1
        cat_visitors[r["page"]].add(r["ip"])
        path_hits[r["page"]][r["path"]] += 1
        path_visitors[r["page"]][r["path"]].add(r["ip"])

    sorted_cats = sorted(cat_hits.items(), key=lambda x: x[1], reverse=True)

    print(f"\n{'='*60}")
    print(f" Page visits")
    print(f"{'='*60}")
    for page, hits in sorted_cats:
        uniq = len(cat_visitors[page])
        print(f"\n {page}  ({hits} hits, {uniq} unique)")

        # Show individual paths if there's more than one, or if the path
        # differs from the bare page URL (has query params)
        paths = path_hits[page]
        sorted_paths = sorted(paths.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_paths) > 1 or sorted_paths[0][0] != PAGE_NAMES_INV.get(page, ""):
            for path, count in sorted_paths:
                puniq = len(path_visitors[page][path])
                print(f"   {path:<40s} {count:>4d} hits  {puniq:>3d} unique")


def pages_daily(records: list[dict[str, str]]) -> None:
    """Print daily page visit breakdown."""
    # date -> page -> count
    daily: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    all_pages: set[str] = set()
    for r in records:
        daily[r["date"]][r["page"]] += 1
        all_pages.add(r["page"])

    sorted_dates = sorted(
        daily.keys(),
        key=lambda d: datetime.strptime(d, "%d/%b/%Y"),
    )
    # Order columns by total hits descending
    page_totals = defaultdict(int)
    for counts in daily.values():
        for page, count in counts.items():
            page_totals[page] += count
    sorted_pages = sorted(all_pages, key=lambda p: page_totals[p], reverse=True)

    col_w = 10
    header = f" {'Date':<15s}" + "".join(f" {p:>{col_w}s}" for p in sorted_pages)

    print(f"\n{'='* len(header)}")
    print(f" Daily page visits")
    print(f"{'='* len(header)}")
    print(header)
    print(f" {'-'*15}" + "".join(f" {'-'*col_w}" for _ in sorted_pages))
    for date in sorted_dates:
        row = f" {date:<15s}"
        for page in sorted_pages:
            row += f" {daily[date].get(page, 0):>{col_w}d}"
        print(row)


def pages_monthly(records: list[dict[str, str]]) -> None:
    """Print monthly page visit breakdown."""
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    all_pages: set[str] = set()
    for r in records:
        dt = datetime.strptime(r["date"], "%d/%b/%Y")
        month_key = dt.strftime("%Y-%m")
        monthly[month_key][r["page"]] += 1
        all_pages.add(r["page"])

    sorted_months = sorted(monthly.keys())
    page_totals: dict[str, int] = defaultdict(int)
    for counts in monthly.values():
        for page, count in counts.items():
            page_totals[page] += count
    sorted_pages = sorted(all_pages, key=lambda p: page_totals[p], reverse=True)

    col_w = 10
    header = f" {'Month':<10s}" + "".join(f" {p:>{col_w}s}" for p in sorted_pages)

    print(f"\n{'='* len(header)}")
    print(f" Monthly page visits")
    print(f"{'='* len(header)}")
    print(header)
    print(f" {'-'*10}" + "".join(f" {'-'*col_w}" for _ in sorted_pages))
    for month in sorted_months:
        row = f" {month:<10s}"
        for page in sorted_pages:
            row += f" {monthly[month].get(page, 0):>{col_w}d}"
        print(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_time_args(parser: argparse.ArgumentParser) -> None:
    """Add --daily / --monthly / --all flags shared by both subcommands."""
    parser.add_argument("--daily", action="store_true", help="Show daily breakdown")
    parser.add_argument("--monthly", action="store_true", help="Show monthly breakdown")
    parser.add_argument("--all", action="store_true", help="Show all reports")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Fly.io access logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    visitors_parser = subparsers.add_parser("visitors", help="Unique visitor analytics")
    _add_time_args(visitors_parser)

    pages_parser = subparsers.add_parser("pages", help="Page visit analytics")
    _add_time_args(pages_parser)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    print("Fetching logs from Fly.io...")
    raw = fetch_logs()
    records = parse_logs(raw)

    if not records:
        print("No visitor requests found in logs (only health checks/static assets).")
        return

    show_all = args.all or (not args.daily and not args.monthly)

    if args.command == "visitors":
        if show_all or not (args.daily or args.monthly):
            visitors_total(records)
        if args.daily or args.all:
            visitors_daily(records)
        if args.monthly or args.all:
            visitors_monthly(records)

    elif args.command == "pages":
        if show_all or not (args.daily or args.monthly):
            pages_total(records)
        if args.daily or args.all:
            pages_daily(records)
        if args.monthly or args.all:
            pages_monthly(records)


if __name__ == "__main__":
    main()
