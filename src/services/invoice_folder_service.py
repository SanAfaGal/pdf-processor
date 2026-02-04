"""Invoice folder orchestration and organization service."""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd

from ..config.logger import setup_logger
from ..config.exceptions import FileOperationError, InvoiceProcessingError

logger = setup_logger(__name__)


class InvoiceFolderService:
    """
    Manages invoice folder organization and staging/final movement pipeline.

    Handles:
    - Source → Staging folder migration
    - Folder hierarchy creation based on invoice metadata
    - File validation and cleanup
    - Staging → Final folder movement
    """

    def __init__(
        self,
        source_path: Path,
        staging_path: Path,
        final_path: Path,
    ) -> None:
        """
        Initialize InvoiceFolderService.

        Args:
            source_path: Source directory with unprocessed files
            staging_path: Staging directory for intermediate processing
            final_path: Final destination directory

        Raises:
            FileOperationError: If paths don't exist or aren't writable
        """
        self.source_path = source_path.resolve()
        self.staging_path = staging_path.resolve()
        self.final_path = final_path.resolve()

        # Ensure directories exist
        for path in [self.source_path, self.staging_path, self.final_path]:
            if not path.exists():
                logger.warning(f"Creating directory: {path}")
                path.mkdir(parents=True, exist_ok=True)

        # Cache for folder hierarchy
        self._folder_cache: Dict[str, Path] = {}

        logger.info(
            f"InvoiceFolderService initialized: "
            f"source={self.source_path.name}, "
            f"staging={self.staging_path.name}, "
            f"final={self.final_path.name}"
        )

    def stage_files(
        self,
        dry_run: bool = True,
    ) -> dict:
        """
        Move files from source to staging directory.

        Args:
            dry_run: If True, only report what would be moved

        Returns:
            Dictionary with moved/skipped counts
        """
        if not self.source_path.exists():
            logger.error(f"Source path not found: {self.source_path}")
            return {"moved": 0, "skipped": 0, "failed": 0}

        files = [
            f for f in self.source_path.rglob("*") if f.is_file()
        ]
        results = {"moved": 0, "skipped": 0, "failed": 0}

        for file_path in files:
            destination = self.staging_path / file_path.relative_to(
                self.source_path
            )

            if dry_run:
                logger.info(
                    f"[DRY-RUN] Would stage: {file_path.name} → {destination.parent.name}"
                )
                results["skipped"] += 1
            else:
                if self._move_file_safe(file_path, destination):
                    results["moved"] += 1
                else:
                    results["failed"] += 1

        logger.info(
            f"Staging complete: {results['moved']} moved, "
            f"{results['failed']} failed"
        )
        return results

    def organize_by_hierarchy(
        self,
        invoice_mapping: Dict[str, Path],
        dry_run: bool = True,
    ) -> dict:
        """
        Organize staged files according to invoice hierarchy.

        Args:
            invoice_mapping: Dict mapping invoice IDs → folder paths
            dry_run: If True, only report what would be organized

        Returns:
            Dictionary with organized/unmatched counts
        """
        results = {"organized": 0, "unmatched": 0, "failed": 0}
        self._folder_cache.clear()  # Reset cache

        staged_files = [
            f for f in self.staging_path.rglob("*") if f.is_file()
        ]

        for file_path in staged_files:
            # Extract invoice ID from filename or path
            invoice_id = self._extract_invoice_code(file_path.name)

            if not invoice_id or invoice_id not in invoice_mapping:
                logger.warning(
                    f"No matching invoice for: {file_path.name}"
                )
                results["unmatched"] += 1
                continue

            target_folder = self.staging_path / invoice_mapping[invoice_id]
            target_path = target_folder / file_path.name

            if dry_run:
                logger.info(
                    f"[DRY-RUN] Would organize: {file_path.name} → {target_folder}"
                )
                results["unmatched"] += 1
            else:
                if self._move_file_safe(file_path, target_path):
                    results["organized"] += 1
                else:
                    results["failed"] += 1

        logger.info(
            f"Organization complete: {results['organized']} organized, "
            f"{results['unmatched']} unmatched"
        )
        return results

    def finalize_files(
        self,
        dry_run: bool = True,
    ) -> dict:
        """
        Move organized files from staging to final destination.

        Args:
            dry_run: If True, only report what would be moved

        Returns:
            Dictionary with finalized/skipped counts
        """
        results = {"finalized": 0, "skipped": 0, "failed": 0}

        # Get all staged files while maintaining hierarchy
        staged_files = [
            f for f in self.staging_path.rglob("*") if f.is_file()
        ]

        for file_path in staged_files:
            relative_path = file_path.relative_to(self.staging_path)
            target_path = self.final_path / relative_path

            if dry_run:
                logger.info(
                    f"[DRY-RUN] Would finalize: {file_path.name} → "
                    f"{target_path.parent.name}"
                )
                results["skipped"] += 1
            else:
                if self._move_file_safe(file_path, target_path):
                    results["finalized"] += 1
                else:
                    results["failed"] += 1

        logger.info(
            f"Finalization complete: {results['finalized']} finalized, "
            f"{results['failed']} failed"
        )
        return results

    def validate_final_structure(
        self,
        expected_invoices: List[str],
    ) -> dict:
        """
        Validate that final directory contains expected invoices.

        Args:
            expected_invoices: List of expected invoice IDs

        Returns:
            Dictionary with found/missing counts and missing invoice list
        """
        results = {"found": 0, "missing": 0, "missing_invoices": []}

        for invoice_id in expected_invoices:
            # Search for invoice folder
            invoice_folders = list(
                self.final_path.rglob(invoice_id)
            )

            if invoice_folders:
                results["found"] += 1
            else:
                results["missing"] += 1
                results["missing_invoices"].append(invoice_id)

        logger.info(
            f"Validation: {results['found']} found, "
            f"{results['missing']} missing"
        )
        return results

    def cleanup_staging(self, dry_run: bool = True) -> dict:
        """
        Clean up staging directory after successful processing.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with deleted/skipped counts
        """
        results = {"deleted": 0, "skipped": 0}

        if not self.staging_path.exists():
            return results

        items = [
            p for p in self.staging_path.rglob("*") if p.is_file()
        ]

        for item in items:
            if dry_run:
                logger.info(f"[DRY-RUN] Would delete: {item.name}")
                results["skipped"] += 1
            else:
                try:
                    item.unlink()
                    results["deleted"] += 1
                except Exception as e:
                    logger.error(f"Failed to delete {item.name}: {str(e)}")

        # Remove empty directories
        for folder in sorted(
            self.staging_path.rglob("*"),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            if folder.is_dir():
                try:
                    folder.rmdir()
                except OSError:
                    pass

        logger.info(f"Cleanup: {results['deleted']} deleted")
        return results

    def _extract_invoice_code(self, filename: str) -> Optional[str]:
        """
        Extract invoice code from filename.

        Expected format contains: [PREFIX][DIGITS] (e.g., "HSL354753")

        Args:
            filename: Filename to parse

        Returns:
            Invoice code or None if not found
        """
        # Match pattern: letters followed by digits
        match = re.search(r"([A-Z]+\d+)", filename.upper())
        if match:
            return match.group(1)
        return None

    def _move_file_safe(
        self,
        source: Path,
        destination: Path,
    ) -> bool:
        """
        Move file with collision detection and error handling.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if successful, False otherwise
        """
        if not source.exists():
            logger.error(f"Source not found: {source}")
            return False

        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Handle collisions
        if destination.exists():
            # Rename source with counter
            stem = destination.stem
            suffix = destination.suffix
            counter = 1
            while destination.exists():
                destination = destination.parent / f"{stem}_{counter}{suffix}"
                counter += 1
            logger.warning(
                f"Collision detected, renaming to: {destination.name}"
            )

        try:
            import shutil

            shutil.move(str(source), str(destination))
            logger.debug(f"Moved: {source.name} → {destination}")
            return True
        except Exception as e:
            logger.error(f"Move failed: {source.name}: {str(e)}")
            return False
