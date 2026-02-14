"""Folder consolidation, scanning, and invoice-based organization."""
import logging
import shutil
from pathlib import Path
from typing import Dict, List

import pandas as pd

from core.models import OperationSummary
from utils.persistence import safe_move

logger = logging.getLogger(__name__)


class FolderConsolidator:
    """Copy folders into a target root with optional name prefix."""

    def __init__(self, target_root: Path) -> None:
        self.target_root = Path(target_root)
        self.target_root.mkdir(parents=True, exist_ok=True)

    def _build_destination(self, folder: Path, use_prefix: bool) -> Path:
        if use_prefix:
            name = f"{folder.parent.name}_{folder.name}"
        else:
            name = folder.name
        return self.target_root / name

    def copy_folders(
        self,
        folders: List[Path],
        use_prefix: bool = True,
    ) -> int:
        """Copy folders to target root. Returns number of folders copied."""
        count = 0
        for folder in folders:
            dest = self._build_destination(folder, use_prefix)
            try:
                shutil.copytree(folder, dest, dirs_exist_ok=True)
                count += 1
                print(f"Copiada: {folder.name} -> {dest.name}")
            except Exception as e:
                logger.error("Copy failed %s -> %s: %s", folder, dest, e)
        return count


class FolderScanner:
    """Scan filesystem for leaf directories that contain files."""

    @staticmethod
    def is_leaf_with_files(path: Path) -> bool:
        """True if path is a directory and contains at least one file."""
        if not path.is_dir():
            return False
        return any(item.is_file() for item in path.iterdir())

    def get_content_folders(self, source_root: Path) -> List[Path]:
        """Return directories under source_root that contain files (leaf dirs with files)."""
        return [
            folder
            for folder in Path(source_root).rglob("**/")
            if self.is_leaf_with_files(folder)
        ]


class InvoiceFolderService:
    """Organize invoice folders from staging to final structure using a DataFrame index."""

    def __init__(
        self,
        df: pd.DataFrame,
        staging_base: Path,
        final_base: Path,
    ) -> None:
        self.df = df
        self.staging_base = Path(staging_base)
        self.final_base = Path(final_base)
        self._logger = logging.getLogger(__name__)
        self._staging_cache: Dict[str, Path] = {}

    def _index_staging_area(self) -> None:
        for folder in self.staging_base.iterdir():
            if folder.is_dir():
                self._staging_cache[folder.name] = folder

    def organize(self, dry_run: bool = False) -> OperationSummary:
        """Move folders from staging to final paths (from df index and Ruta column)."""
        self._index_staging_area()
        stats = {"moved": 0, "failed": 0, "not_found": 0, "errors": []}
        for invoice_id, row in self.df.iterrows():
            source_path = next(
                (path for name, path in self._staging_cache.items() if str(invoice_id) in name),
                None,
            )
            if not source_path:
                self._logger.warning("Not found in staging: %s", invoice_id)
                stats["not_found"] += 1
                continue
            destination_path = self.final_base / row["Ruta"]
            if dry_run:
                self._logger.info("DRY RUN %s -> %s", source_path.name, destination_path)
                stats["moved"] += 1
                continue
            if safe_move(source_path, destination_path):
                stats["moved"] += 1
            else:
                stats["failed"] += 1
                stats["errors"].append(f"Move failed: {invoice_id}")
        return OperationSummary(
            moved=stats["moved"],
            failed=stats["failed"],
            not_found=stats["not_found"],
            errors=stats["errors"],
        )
