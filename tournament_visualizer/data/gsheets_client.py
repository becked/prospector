"""Google Sheets client for accessing tournament data spreadsheets.

This module provides a simple interface to the Google Sheets API for
reading tournament data (e.g., pick order information). Uses API key
authentication since spreadsheets are publicly accessible.

Example:
    >>> from tournament_visualizer.config import Config
    >>> client = GoogleSheetsClient(api_key=Config.GOOGLE_DRIVE_API_KEY)
    >>> data = client.get_sheet_values(
    ...     spreadsheet_id=Config.GOOGLE_SHEETS_SPREADSHEET_ID,
    ...     range_name="GAMEDATA!A1:Z200"
    ... )
    >>> print(f"Got {len(data)} rows")
"""

import logging
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Client for reading data from Google Sheets.

    Uses API key authentication to access publicly shared spreadsheets.
    No OAuth required.

    Attributes:
        api_key: Google API key with Sheets API enabled
    """

    def __init__(self, api_key: str) -> None:
        """Initialize Google Sheets client.

        Args:
            api_key: Google API key with Sheets API enabled

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self._service = None

    def _get_service(self) -> Any:
        """Get or create Sheets API service instance.

        Lazy initialization - only creates service when needed.

        Returns:
            Google Sheets API service instance
        """
        if self._service is None:
            self._service = build('sheets', 'v4', developerKey=self.api_key)
        return self._service

    def get_sheet_values(
        self,
        spreadsheet_id: str,
        range_name: str,
    ) -> list[list[str]]:
        """Get cell values from a spreadsheet range.

        Args:
            spreadsheet_id: The spreadsheet ID (from the URL)
            range_name: The A1 notation range (e.g., "Sheet1!A1:D10")

        Returns:
            List of rows, where each row is a list of cell values.
            Empty cells return as empty strings.
            Rows may have different lengths if trailing cells are empty.

        Raises:
            HttpError: If API request fails (e.g., 404 not found, 403 forbidden)

        Example:
            >>> values = client.get_sheet_values(
            ...     "19t5AbJtQr5kZ62pw8FJ-r2b9LVkz01zl2GUNWkIrhAc",
            ...     "GAMEDATA!A1:K100"
            ... )
            >>> print(f"First cell: {values[0][0]}")
        """
        try:
            service = self._get_service()

            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            ).execute()

            values = result.get('values', [])
            logger.info(
                f"Fetched {len(values)} rows from sheet "
                f"(range: {range_name})"
            )

            return values

        except HttpError as e:
            logger.error(
                f"Failed to fetch sheet data: {e.status_code} {e.reason}"
            )
            raise

    def get_sheet_metadata(self, spreadsheet_id: str) -> dict[str, Any]:
        """Get metadata about a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            Dictionary with spreadsheet metadata including:
            - properties: Title, locale, timezone
            - sheets: List of sheet metadata (title, gridProperties, etc.)

        Raises:
            HttpError: If API request fails
        """
        try:
            service = self._get_service()

            result = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            logger.info(
                f"Fetched metadata for spreadsheet: {result.get('properties', {}).get('title')}"
            )

            return result

        except HttpError as e:
            logger.error(
                f"Failed to fetch sheet metadata: {e.status_code} {e.reason}"
            )
            raise
