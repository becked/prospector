#!/usr/bin/env python3
"""
Script to download all attachments from a Challonge tournament.
Uses chyllonge library to interact with the Challonge API.

Falls back to Google Drive for files that exceed Challonge's 250KB limit.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

# Load environment variables before importing Config
# (Config class variables are evaluated at import time)
load_dotenv()

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.gdrive_client import GoogleDriveClient


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


def download_attachment(
    url: str, filename: str, save_dir: Path, expected_size: int | None = None
) -> bool:
    """Download an attachment from URL to the specified directory.

    Skips download if file already exists with matching size.
    Re-downloads if size mismatch indicates corruption or incomplete download.
    """
    save_path = save_dir / filename

    # Skip if file already exists and size matches (if provided)
    if save_path.exists():
        if expected_size is None:
            print(f"Skipped (already exists): {filename}")
            return True

        actual_size = save_path.stat().st_size
        if actual_size == expected_size:
            print(f"Skipped (already exists, size verified): {filename}")
            return True
        else:
            print(
                f"Re-downloading (size mismatch: {actual_size} vs {expected_size}): "
                f"{filename}"
            )

    try:
        urllib.request.urlretrieve(url, save_path)
        print(f"Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False


def extract_gdrive_file_id(url: str) -> str | None:
    """Extract Google Drive file ID from various URL formats.

    Supported formats:
    - https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    - https://drive.google.com/file/d/FILE_ID/view?usp=drive_link
    - https://drive.google.com/open?id=FILE_ID
    - https://docs.google.com/uc?id=FILE_ID

    Args:
        url: Google Drive sharing URL

    Returns:
        File ID string, or None if URL doesn't match expected patterns
    """
    if not url:
        return None

    # Pattern 1: /file/d/FILE_ID/
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)

    # Pattern 2: id=FILE_ID (query parameter)
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)

    return None


def load_gdrive_mapping(mapping_path: Path = Path("data/gdrive_match_mapping.json")) -> dict[str, Any]:
    """Load Google Drive match mapping file.

    Args:
        mapping_path: Path to mapping JSON file

    Returns:
        Mapping dictionary, or empty dict if file doesn't exist
    """
    if not mapping_path.exists():
        print(f"No Google Drive mapping file found at {mapping_path}")
        return {"matches": {}}

    try:
        with open(mapping_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading GDrive mapping: {e}")
        return {"matches": {}}


def download_from_gdrive(
    gdrive_client: GoogleDriveClient,
    file_id: str,
    filename: str,
    save_dir: Path,
) -> bool:
    """Download file from Google Drive.

    Args:
        gdrive_client: Google Drive client instance
        file_id: Google Drive file ID
        filename: Filename to save as
        save_dir: Directory to save file in

    Returns:
        True if download successful, False otherwise
    """
    save_path = save_dir / filename

    # Skip if already exists
    if save_path.exists():
        print(f"Skipped (already exists): {filename}")
        return True

    print(f"Downloading from Google Drive: {filename}")
    success = gdrive_client.download_file(file_id, save_path)

    if success:
        print(f"✓ Downloaded from GDrive: {filename}")
    else:
        print(f"✗ GDrive download failed: {filename}")

    return success


def download_match_save(
    match_data: dict[str, Any],
    api: ChallongeApi,
    tournament_id: str,
    save_dir: Path,
    gdrive_client: GoogleDriveClient | None,
    gdrive_mapping: dict[str, Any],
) -> tuple[bool, str]:
    """Download save file for a match from best available source.

    Tries Challonge first, falls back to Google Drive if needed.

    Args:
        match_data: Match data from Challonge API
        api: Challonge API client
        tournament_id: Tournament ID
        save_dir: Directory to save files
        gdrive_client: Google Drive client (or None if not configured)
        gdrive_mapping: GDrive match mapping dictionary

    Returns:
        Tuple of (success: bool, source: str)
        source is "challonge", "gdrive", or "none"
    """
    match_id = match_data.get("id")
    attachment_count = match_data.get("attachment_count", 0)

    # Try Challonge first
    if attachment_count and attachment_count > 0:
        try:
            attachments = api.attachments.get_all(tournament_id, match_id)

            for attachment in attachments:
                asset_url = attachment.get("asset_url")
                if asset_url:
                    # Fix URL protocol if missing
                    if asset_url.startswith("//"):
                        asset_url = "https:" + asset_url

                    # Use original filename
                    filename = attachment.get("asset_file_name") or f"match_{match_id}.zip"
                    safe_filename = f"match_{match_id}_{filename}"
                    safe_filename = "".join(
                        c for c in safe_filename if c.isalnum() or c in "._- "
                    )

                    # Try to download
                    if download_attachment(
                        asset_url,
                        safe_filename,
                        save_dir,
                        attachment.get("asset_file_size"),
                    ):
                        return True, "challonge"

                # Check for Google Drive link attachment (no direct upload)
                elif gdrive_client:
                    link_url = attachment.get("url")
                    gdrive_file_id = extract_gdrive_file_id(link_url)
                    if gdrive_file_id:
                        # Generate filename from attachment description or match ID
                        description = attachment.get("description", "")
                        gdrive_filename = f"match_{match_id}_{description or 'save'}.zip"
                        safe_filename = "".join(
                            c for c in gdrive_filename if c.isalnum() or c in "._- "
                        )

                        print(f"Found Google Drive link attachment for match {match_id}")
                        if download_from_gdrive(gdrive_client, gdrive_file_id, safe_filename, save_dir):
                            return True, "gdrive_link"
        except Exception as e:
            print(f"Challonge download failed for match {match_id}: {e}")

    # Fall back to Google Drive mapping
    if gdrive_client and str(match_id) in gdrive_mapping.get("matches", {}):
        mapping_entry = gdrive_mapping["matches"][str(match_id)]
        file_id = mapping_entry["gdrive_file_id"]
        gdrive_filename = mapping_entry["gdrive_filename"]

        safe_filename = f"match_{match_id}_{gdrive_filename}"
        safe_filename = "".join(
            c for c in safe_filename if c.isalnum() or c in "._- "
        )

        if download_from_gdrive(gdrive_client, file_id, safe_filename, save_dir):
            return True, "gdrive"

    return False, "none"


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
                                "size": att_data.get("asset_file_size"),
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

        # Initialize Google Drive client (if API key configured)
        gdrive_client = None
        gdrive_mapping = load_gdrive_mapping()

        if Config.GOOGLE_DRIVE_API_KEY:
            try:
                gdrive_client = GoogleDriveClient(
                    api_key=Config.GOOGLE_DRIVE_API_KEY,
                    folder_id=Config.GOOGLE_DRIVE_FOLDER_ID,
                )
                print(f"✓ Google Drive integration enabled")
                print(f"  Loaded {len(gdrive_mapping.get('matches', {}))} GDrive mappings")
            except Exception as e:
                print(f"⚠ Google Drive initialization failed: {e}")
                print("  Will only use Challonge attachments")
        else:
            print("ℹ Google Drive API key not configured (will only use Challonge)")

        # Create downloads directory
        downloads_dir = Path(os.getenv("SAVES_DIRECTORY", "saves"))
        downloads_dir.mkdir(exist_ok=True)

        print(f"Downloading attachments for tournament: {tournament_id}")

        # Get tournament matches
        matches = get_tournament_matches(api, tournament_id)
        if not matches:
            print("No matches found or error retrieving matches")
            return

        print(f"Found {len(matches)} matches")

        # Download saves for each match
        successful_downloads = 0
        challonge_downloads = 0
        gdrive_downloads = 0
        failed_downloads = 0

        for match in matches:
            success, source = download_match_save(
                match,
                api,
                tournament_id,
                downloads_dir,
                gdrive_client,
                gdrive_mapping,
            )

            if success:
                successful_downloads += 1
                if source == "challonge":
                    challonge_downloads += 1
                elif source == "gdrive":
                    gdrive_downloads += 1
            else:
                failed_downloads += 1
                print(f"⚠ No save file found for match {match.get('id')}")

        print(f"\nDownload complete:")
        print(f"  Total successful: {successful_downloads}/{len(matches)}")
        print(f"  From Challonge: {challonge_downloads}")
        print(f"  From Google Drive: {gdrive_downloads}")
        print(f"  Failed: {failed_downloads}")
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
