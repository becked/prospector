"""Tests for Google Drive client."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from tournament_visualizer.data.gdrive_client import GoogleDriveClient


class TestGoogleDriveClient:
    """Test GoogleDriveClient class."""

    def test_init_with_valid_api_key(self) -> None:
        """Client initializes with valid API key."""
        client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")

        assert client.api_key == "test_key"
        assert client.folder_id == "test_folder"

    def test_init_requires_api_key(self) -> None:
        """Client requires API key on initialization."""
        with pytest.raises(ValueError, match="API key is required"):
            GoogleDriveClient(api_key="", folder_id="test_folder")

    def test_list_files_returns_file_metadata(self) -> None:
        """list_files() returns list of file metadata dicts."""
        # Mock the Google API service
        with patch('tournament_visualizer.data.gdrive_client.build') as mock_build:
            mock_service = Mock()
            mock_files = Mock()
            mock_list = Mock()

            # Setup mock chain
            mock_build.return_value = mock_service
            mock_service.files.return_value = mock_files
            mock_files.list.return_value = mock_list
            mock_list.execute.return_value = {
                'files': [
                    {'id': '123', 'name': 'test.zip', 'size': '1000'},
                    {'id': '456', 'name': 'test2.zip', 'size': '2000'},
                ]
            }

            client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")
            files = client.list_files()

            assert len(files) == 2
            assert files[0]['id'] == '123'
            assert files[0]['name'] == 'test.zip'
            assert files[1]['id'] == '456'

    def test_download_file_success(self, tmp_path: Path) -> None:
        """download_file() downloads file to specified path."""
        output_path = tmp_path / "test.zip"

        with patch('tournament_visualizer.data.gdrive_client.build') as mock_build:
            with patch('tournament_visualizer.data.gdrive_client.MediaIoBaseDownload') as mock_download:
                # Setup mocks
                mock_service = Mock()
                mock_build.return_value = mock_service

                # Mock download behavior
                mock_downloader = Mock()
                mock_downloader.next_chunk.side_effect = [
                    (Mock(progress=lambda: 0.5), False),  # First chunk
                    (Mock(progress=lambda: 1.0), True),   # Complete
                ]
                mock_download.return_value = mock_downloader

                client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")

                # Create dummy file for test
                output_path.write_bytes(b"test content")

                result = client.download_file("file_id_123", output_path)

                assert result is True
                assert output_path.exists()

    def test_download_file_handles_errors(self, tmp_path: Path) -> None:
        """download_file() returns False on error."""
        output_path = tmp_path / "test.zip"

        with patch('tournament_visualizer.data.gdrive_client.build') as mock_build:
            mock_build.side_effect = Exception("API Error")

            client = GoogleDriveClient(api_key="test_key", folder_id="test_folder")
            result = client.download_file("file_id_123", output_path)

            assert result is False
