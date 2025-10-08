#!/usr/bin/env python3
"""
Script to download all attachments from a Challonge tournament.
Uses pychallonge library to interact with the Challonge API.
"""

import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

import challonge
from dotenv import load_dotenv


def load_config() -> tuple[str, str, str]:
    """Load username, API key and tournament ID from environment variables."""
    load_dotenv()

    username = os.getenv("challonge_username")
    api_key = os.getenv("challonge_api_key")
    tournament_id = os.getenv("challonge_tournament_id")

    if not username:
        raise ValueError("challonge_username not found in .env file")
    if not api_key:
        raise ValueError("challonge_api_key not found in .env file")
    if not tournament_id:
        raise ValueError("challonge_tournament_id not found in .env file")

    return username, api_key, tournament_id


def setup_challonge_client(username: str, api_key: str) -> None:
    """Initialize the Challonge client with username and API key."""
    challonge.set_credentials(username, api_key)


def get_tournament_matches(tournament_id: str) -> List[Dict[str, Any]]:
    """Retrieve all matches from the tournament."""
    try:
        matches = challonge.matches.index(tournament_id)
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
    matches: List[Dict[str, Any]], tournament_id: str
) -> List[Dict[str, str]]:
    """Extract attachment information from matches."""
    attachments = []

    for match in matches:
        # Handle both nested and flat API response structure
        if "match" in match:
            match_data = match["match"]
        else:
            match_data = match

        attachment_count = match_data.get("attachment_count", 0)

        if attachment_count and attachment_count > 0:
            match_id = match_data.get("id")
            # Get match attachments using correct API call
            try:
                match_attachments = challonge.attachments.index(tournament_id, match_id)

                for attachment in match_attachments:
                    # Handle both nested and flat attachment structure
                    if "match_attachment" in attachment:
                        att_data = attachment["match_attachment"]
                    else:
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
        username, api_key, tournament_id = load_config()

        # Setup Challonge client
        setup_challonge_client(username, api_key)

        # Create downloads directory
        downloads_dir = Path("tournament_attachments")
        downloads_dir.mkdir(exist_ok=True)

        print(f"Downloading attachments for tournament: {tournament_id}")

        # Get tournament matches
        matches = get_tournament_matches(tournament_id)
        if not matches:
            print("No matches found or error retrieving matches")
            return

        print(f"Found {len(matches)} matches")

        # Extract attachments from matches
        attachments = extract_attachments_from_matches(matches, tournament_id)

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
            f"\nDownload complete: {successful_downloads}/{len(attachments)} files downloaded successfully"
        )
        print(f"Files saved to: {downloads_dir.absolute()}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
