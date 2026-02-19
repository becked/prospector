"""Analyze access logs from the Fly.io persistent volume.

Pulls access.log from the deployed app via `fly ssh console` and reports
unique visitor counts (total, daily, monthly).

Usage:
    uv run python scripts/analyze_access_logs.py              # Summary of all
    uv run python scripts/analyze_access_logs.py --daily      # Daily breakdown
    uv run python scripts/analyze_access_logs.py --monthly    # Monthly breakdown
    uv run python scripts/analyze_access_logs.py --all        # Everything
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

APP_NAME = "prospector"
LOG_PATH = "/data/logs/access.log"

# Matches the X-Forwarded-For IP(s) at the start, then the date in brackets
# Example: 74.108.139.73, 66.241.125.158 - - [19/Feb/2026:19:24:26 +0000] "GET / HTTP/1.1" ...
LOG_PATTERN = re.compile(
    r'^([\d., ]+)\s+-\s+-\s+\[(\d{2}/\w{3}/\d{4}):\d{2}:\d{2}:\d{2}\s+[+\-]\d{4}\]\s+"(\w+)\s+(\S+)'
)


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
        # Skip health checks (no real IP)
        if "Consul Health Check" in line:
            continue

        match = LOG_PATTERN.match(line)
        if not match:
            continue

        ip_chain, date_str, method, path = match.groups()

        # First IP in X-Forwarded-For is the real client
        client_ip = ip_chain.split(",")[0].strip()

        # Skip static asset requests — only count page/API visits
        if path.startswith("/_dash-") or path.startswith("/assets/"):
            continue

        records.append({
            "ip": client_ip,
            "date": date_str,
            "method": method,
            "path": path,
        })
    return records


def print_total(records: list[dict[str, str]]) -> None:
    """Print total unique visitor count."""
    unique_ips = {r["ip"] for r in records}
    print(f"\n{'='*40}")
    print(f" Total unique visitors: {len(unique_ips)}")
    print(f" Total page requests:   {len(records)}")
    print(f"{'='*40}")

    if unique_ips:
        # Show top visitors
        ip_counts: dict[str, int] = defaultdict(int)
        for r in records:
            ip_counts[r["ip"]] += 1
        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)

        print(f"\n Top visitors:")
        for ip, count in sorted_ips[:10]:
            print(f"   {ip:<20s} {count:>4d} requests")


def print_daily(records: list[dict[str, str]]) -> None:
    """Print daily unique visitor breakdown."""
    daily: dict[str, set[str]] = defaultdict(set)
    daily_requests: dict[str, int] = defaultdict(int)
    for r in records:
        daily[r["date"]].add(r["ip"])
        daily_requests[r["date"]] += 1

    # Sort by date
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


def print_monthly(records: list[dict[str, str]]) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Fly.io access logs for unique visitors")
    parser.add_argument("--daily", action="store_true", help="Show daily breakdown")
    parser.add_argument("--monthly", action="store_true", help="Show monthly breakdown")
    parser.add_argument("--all", action="store_true", help="Show all reports")
    args = parser.parse_args()

    print("Fetching logs from Fly.io...")
    raw = fetch_logs()
    records = parse_logs(raw)

    if not records:
        print("No visitor requests found in logs (only health checks/static assets).")
        return

    show_all = args.all or (not args.daily and not args.monthly)

    if show_all or not (args.daily or args.monthly):
        print_total(records)
    if args.daily or args.all:
        print_daily(records)
    if args.monthly or args.all:
        print_monthly(records)


if __name__ == "__main__":
    main()
