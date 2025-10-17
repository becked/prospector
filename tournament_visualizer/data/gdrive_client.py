"""Google Drive client for accessing public tournament save files.

This module provides a simple interface to the Google Drive API for
downloading save files from public folders. Uses API key authentication
(no OAuth) since the folder is publicly accessible.
"""

import io
import logging
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """Client for interacting with Google Drive public folders.

    Uses API key authentication to access publicly shared folders.
    No OAuth required.

    Example:
        >>> client = GoogleDriveClient(api_key="your_key", folder_id="folder_id")
        >>> files = client.list_files()
        >>> client.download_file(files[0]['id'], Path("output.zip"))
    """

    def __init__(self, api_key: str, folder_id: str) -> None:
        """Initialize Google Drive client.

        Args:
            api_key: Google Drive API key
            folder_id: ID of the public folder to access

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.folder_id = folder_id
        self._service = None

    def _get_service(self) -> Any:
        """Get or create Drive API service instance.

        Lazy initialization - only creates service when needed.

        Returns:
            Google Drive API service instance
        """
        if self._service is None:
            self._service = build('drive', 'v3', developerKey=self.api_key)
        return self._service

    def list_files(self) -> list[dict[str, Any]]:
        """List all files in the configured folder.

        Returns:
            List of file metadata dictionaries with keys:
            - id: File ID
            - name: Filename
            - size: File size in bytes (as string)
            - modifiedTime: Last modified timestamp

        Raises:
            Exception: If API request fails
        """
        try:
            service = self._get_service()

            # Query for files in the specified folder
            results = service.files().list(
                q=f"'{self.folder_id}' in parents and trashed=false",
                fields="files(id, name, size, modifiedTime)",
                orderBy="name",
                supportsAllDrives=True
            ).execute()

            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in Google Drive folder")

            return files

        except Exception as e:
            logger.error(f"Failed to list files from Google Drive: {e}")
            raise

    def download_file(self, file_id: str, output_path: Path) -> bool:
        """Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID
            output_path: Local path to save the file

        Returns:
            True if download successful, False otherwise
        """
        try:
            service = self._get_service()

            # Request file download
            request = service.files().get_media(fileId=file_id)

            # Download to memory buffer first
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(
                        f"Download progress: {int(status.progress() * 100)}%"
                    )

            # Write to disk
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())

            logger.info(f"Downloaded file to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return False

    def get_file_metadata(self, file_id: str) -> dict[str, Any] | None:
        """Get metadata for a specific file.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dict or None if not found
        """
        try:
            service = self._get_service()

            file_metadata = service.files().get(
                fileId=file_id,
                fields="id, name, size, modifiedTime"
            ).execute()

            return file_metadata

        except Exception as e:
            logger.error(f"Failed to get metadata for file {file_id}: {e}")
            return None
