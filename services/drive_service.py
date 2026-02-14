"""Google Drive API: search and download files/folders."""
import io
import logging
from pathlib import Path
from typing import List, Union

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


def _escape_query_string(s: str) -> str:
    """Escape single quotes for Drive API query (reduce injection risk)."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


class GoogleDriveService:
    """Search and download from Google Drive using service account."""

    DRIVE_FOLDER_MIME = DRIVE_FOLDER_MIME

    def __init__(
        self,
        credentials_path: Union[str, Path],
        scopes: List[str],
    ) -> None:
        self.creds = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=scopes
        )
        self.service = build("drive", "v3", credentials=self.creds)

    def find_folders_by_name(self, folder_name: str) -> List[dict]:
        """Return list of folder dicts (id, name, parents) matching name."""
        safe_name = _escape_query_string(folder_name)
        query = (
            f"name contains '{safe_name}' "
            f"and mimeType = '{self.DRIVE_FOLDER_MIME}' "
            f"and trashed = false"
        )
        results = (
            self.service.files()
            .list(q=query, fields="files(id, name, parents)", pageSize=10)
            .execute()
        )
        return results.get("files", [])

    def download_file(
        self,
        file_id: str,
        file_name: str,
        local_dir: Union[str, Path],
    ) -> None:
        """Download one file to local_dir. Logs errors."""
        local_dir = Path(local_dir)
        try:
            request = self.service.files().get_media(fileId=file_id)
            local_dir.mkdir(parents=True, exist_ok=True)
            path = local_dir / file_name
            with io.FileIO(str(path), "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            logger.info("Downloaded: %s", file_name)
        except Exception as e:
            logger.error("Download failed %s: %s", file_name, e)

    def download_recursive(
        self,
        folder_id: str,
        local_path: Union[str, Path],
        depth: int = 0,
    ) -> None:
        """Download folder and subfolders recursively. Prints progress."""
        local_path = Path(local_path)
        indent = "  " * depth
        print(f"{indent}Folder: {local_path.name}")
        query = f"'{folder_id}' in parents and trashed = false"
        results = (
            self.service.files()
            .list(q=query, fields="files(id, name, mimeType)")
            .execute()
        )
        items = results.get("files", [])
        if not items and depth == 0:
            print(f"{indent}  (empty)")
        for item in items:
            name = item["name"]
            id_ = item["id"]
            if item["mimeType"] == self.DRIVE_FOLDER_MIME:
                self.download_recursive(id_, local_path / name, depth + 1)
            else:
                if "google-apps" not in item["mimeType"]:
                    print(f"{indent}  Download: {name}")
                    self.download_file(id_, name, local_path)
                else:
                    print(f"{indent}  Skip (Google Doc): {name}")

    def sync_missing_folders(
        self,
        folder_names: List[str],
        local_root: Union[str, Path],
    ) -> None:
        """Find each folder name on Drive and download recursively."""
        local_root = Path(local_root)
        for target in folder_names:
            logger.info("Searching Drive: %s", target)
            found = self.find_folders_by_name(target)
            if not found:
                logger.warning("Folder not found: %s", target)
                continue
            for folder in found:
                dest = local_root / folder["name"]
                self.download_recursive(folder["id"], dest)

    def sync_specific_files(
        self,
        file_names: List[str],
        local_root: Union[str, Path],
    ) -> List[str]:
        """Find and download files by exact name. Returns list of names not found."""
        local_root = Path(local_root)
        not_found: List[str] = []
        print(f"Searching for {len(file_names)} file(s)...")
        for name in file_names:
            safe = _escape_query_string(name)
            query = (
                f"name = '{safe}' "
                f"and mimeType != '{self.DRIVE_FOLDER_MIME}' "
                f"and trashed = false"
            )
            results = (
                self.service.files()
                .list(q=query, fields="files(id, name)", pageSize=1)
                .execute()
            )
            files = results.get("files", [])
            if not files:
                not_found.append(name)
                continue
            self.download_file(files[0]["id"], files[0]["name"], local_root)
        return not_found
