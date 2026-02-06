import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict

import numpy as np
import pandas as pd

from utils import Util

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class InvoiceFolderService:
    """
    Service to manage, stage, and organize invoice folders based on DataFrame metadata.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        staging_base: Path,
        final_base: Path,
    ):
        self.df = df.copy()
        self.staging_base = Path(staging_base)
        self.final_base = Path(final_base)

    def _safe_move(self, src: Path, dest: Path) -> None:
        """
        Handles the physical movement and directory creation.
        """
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                logging.error(f"Collision: Destination already exists {dest}")
                return

            shutil.move(str(src), str(dest))
            logging.info(f"Moved: {src.name} -> {dest.relative_to(dest.parents[2])}")
        except Exception as e:
            logging.error(f"Error moving {src}: {e}")

    def organize_to_destination(self, dry_run: bool = False) -> None:
        """
        PHASE 2: Move folders from staging to the final organized hierarchy.
        """
        for invoice_id, row in self.df.iterrows():
            # Look for the folder in staging (it should be there after Phase 1)
            # We use glob to find the folder that matches the ID in staging
            matching_folders = list(self.staging_base.glob(f"*{invoice_id}*"))

            if not matching_folders:
                logging.warning(f"Not found in staging: {invoice_id}")
                continue

            source_path = matching_folders[0]
            final_path = self.final_base / row["Ruta"]

            if dry_run:
                logging.info(f"[DRY-RUN] Final: {source_path} -> {final_path}")
            else:
                self._safe_move(source_path, final_path)
