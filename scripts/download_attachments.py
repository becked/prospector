#!/usr/bin/env python3
"""
Script to download all attachments from a Challonge tournament.
Uses chyllonge library to interact with the Challonge API.
"""

import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv


def load_config() -> str:
    """Load tournament ID from environment variables.

    Note: chyllonge uses CHALLONGE_KEY and CHALLONGE_USER env vars automatically.

    Environment variables are loaded from .env file in development,
    or directly from environment in production (Fly.io secrets).
    """
    # Try to load .env file (development), silently skip if not found (production)
    load_dotenv()

    tournament_id = os.getenv("challonge_tournament_id")

    if not tournament_id:
        raise ValueError(
            "challonge_tournament_id not found in environment variables. "
            "In development: check .env file. "
            "In production: set via 'flyctl secrets set challonge_tournament_id=VALUE'"
        )

    # Verify other required environment variables
    if not os.getenv("CHALLONGE_KEY"):
        raise ValueError(
            "CHALLONGE_KEY not found in environment variables. "
            "Required for Challonge API access."
        )

    if not os.getenv("CHALLONGE_USER"):
        raise ValueError(
            "CHALLONGE_USER not found in environment variables. "
            "Required for Challonge API access."
        )

    return tournament_id


def create_challonge_client() -> ChallongeApi:
    """Create and return a Challonge API client.

    Requires CHALLONGE_KEY and CHALLONGE_USER environment variables.
    """
    return ChallongeApi()


def get_tournament_matches(
    api: ChallongeApi, tournament_id: str
) -> list[dict[str, Any]]:
    """Retrieve all matches from the tournament."""
    try:
        matches = api.matches.get_all(tournament_id)
        return matches
    except Exception as e:
        print(f"Error retrieving matches: {e}")
        return []


def download_attachment(url: str, filename: str, save_dir: Path) -> bool:
    """Download an attachment from URL to the specified directory."""
    try:
        save_path = save_dir / filename
        urllib.request.urlretrieve(url, save_path)
        print(f"Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False


def extract_attachments_from_matches(
    api: ChallongeApi, matches: list[dict[str, Any]], tournament_id: str
) -> list[dict[str, str]]:
    """Extract attachment information from matches."""
    attachments = []

    for match in matches:
        # chyllonge get_all() returns flat dictionaries
        # (already extracted from nested structure)
        match_data = match

        attachment_count = match_data.get("attachment_count", 0)

        if attachment_count and attachment_count > 0:
            match_id = match_data.get("id")
            # Get match attachments using chyllonge API
            try:
                match_attachments = api.attachments.get_all(tournament_id, match_id)

                for attachment in match_attachments:
                    # chyllonge get_all() returns flat dictionaries
                    att_data = attachment

                    # Use asset_url instead of url, and asset_file_name for filename
                    asset_url = att_data.get("asset_url")
                    if asset_url:
                        # Fix URL protocol if missing
                        if asset_url.startswith("//"):
                            asset_url = "https:" + asset_url

                        # Use original filename if available, otherwise generate one
                        filename = att_data.get("asset_file_name") or att_data.get(
                            "original_file_name"
                        )
                        if not filename:
                            file_id = att_data.get("id", "unknown")
                            filename = f"attachment_{file_id}.file"

                        attachments.append(
                            {
                                "url": asset_url,
                                "filename": filename,
                                "match_id": str(match_id),
                            }
                        )
            except Exception as e:
                print(f"Error getting attachments for match {match_id}: {e}")

    return attachments


def main() -> None:
    """Main function to download all tournament attachments."""
    try:
        # Load configuration
        tournament_id = load_config()

        # Create Challonge API client
        api = create_challonge_client()

        # Create downloads directory
        # Use SAVES_DIRECTORY env var if set, otherwise default to "saves"
        downloads_dir = Path(os.getenv("SAVES_DIRECTORY", "saves"))
        downloads_dir.mkdir(exist_ok=True)

        print(f"Downloading attachments for tournament: {tournament_id}")

        # Get tournament matches
        matches = get_tournament_matches(api, tournament_id)
        if not matches:
            print("No matches found or error retrieving matches")
            return

        print(f"Found {len(matches)} matches")

        # Extract attachments from matches
        attachments = extract_attachments_from_matches(api, matches, tournament_id)

        if not attachments:
            print("No attachments found in tournament")
            return

        print(f"Found {len(attachments)} attachments to download")

        # Download each attachment
        successful_downloads = 0
        for attachment in attachments:
            # Create filename with match ID prefix for organization
            safe_filename = f"match_{attachment['match_id']}_{attachment['filename']}"
            # Remove or replace invalid filename characters
            safe_filename = "".join(
                c for c in safe_filename if c.isalnum() or c in "._- "
            )

            if download_attachment(attachment["url"], safe_filename, downloads_dir):
                successful_downloads += 1

        print(
            f"\nDownload complete: {successful_downloads}/{len(attachments)} "
            "files downloaded successfully"
        )
        print(f"Files saved to: {downloads_dir.absolute()}")

    except ValueError as e:
        # Configuration errors (missing env vars)
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Unexpected errors
        print(f"Unexpected Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
