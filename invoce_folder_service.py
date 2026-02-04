import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class InvoiceFolderService:
    """
    Service to manage, stage, and organize invoice folders based on DataFrame metadata.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        source_base: Path,
        staging_base: Path,
        final_base: Path,
    ):
        self.df = df.copy()
        self.source_base = Path(source_base)
        self.staging_base = Path(staging_base)
        self.final_base = Path(final_base)

        # Internal cache for folder mapping to boost performance
        self._source_folders_cache: Dict[str, Path] = {}

    def _extract_invoice_code(self, folder_name: str) -> Optional[str]:
        """
        Extracts invoice code (e.g., HSL354753) from folder names using Regex.
        """
        match = re.search(r"([A-Z]{2,5})\s*[_\-]?\s*(\d{4,})", folder_name.upper())
        return f"{match.group(1)}{match.group(2)}" if match else None

    def _index_source_folders(self) -> None:
        """
        Scans source_base once and maps invoice codes to their Path.
        Performance: O(n) instead of O(n^2).
        """
        logging.info(f"Indexing folders in {self.source_base}...")
        for path in self.source_base.rglob("*"):
            if path.is_dir():
                code = self._extract_invoice_code(path.name)
                if code:
                    self._source_folders_cache[code] = path

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

    def collect_to_staging(self, dry_run: bool = False) -> None:
        """
        PHASE 1: Move folders from messy source to a flat staging directory.
        Keeps the original folder name.
        """
        if not self._source_folders_cache:
            self._index_source_folders()

        self.staging_base.mkdir(parents=True, exist_ok=True)

        for invoice_id in self.df.index:
            source_path = self._source_folders_cache.get(invoice_id)

            if not source_path:
                logging.warning(f"Not found in source: {invoice_id}")
                continue

            destination = self.staging_base / source_path.name

            if dry_run:
                logging.info(f"[DRY-RUN] Stage: {source_path} -> {destination}")
            else:
                self._safe_move(source_path, destination)

    def delete_empty_source_dirs(self, dry_run: bool = False) -> None:
        """
        Deletes empty directories in the source base path.
        """
        for dir_path in sorted(self.source_base.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                if dry_run:
                    logging.info(f"[DRY-RUN] Delete empty dir: {dir_path}")
                else:
                    try:
                        dir_path.rmdir()
                        logging.info(f"Deleted empty dir: {dir_path}")
                    except Exception as e:
                        logging.error(f"Error deleting {dir_path}: {e}")

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

    def _save_report(
        self, df: pd.DataFrame, default_name: str, custom_path: Optional[Path] = None
    ):
        """
        Generic helper to save DataFrames as Excel or CSV based on extension.
        """
        if df.empty:
            logging.info(f"✨ No records to save for {default_name}.")
            return

        file_to_save = custom_path or Path(default_name)

        try:
            if file_to_save.suffix.lower() == ".csv":
                # utf-8-sig permite que Excel reconozca tildes y caracteres especiales
                df.to_csv(file_to_save, index=False, sep=";", encoding="utf-8-sig")
            else:
                # Por defecto guarda en Excel si no es CSV
                file_to_save = file_to_save.with_suffix(".xlsx")
                df.to_excel(file_to_save, index=False)

            logging.info(f"✅ Report saved: {len(df)} records in {file_to_save}")
        except Exception as e:
            logging.error(f"❌ Error saving report {file_to_save}: {e}")

    def export_missing_invoices(
        self, output_path: Optional[Path] = None
    ) -> pd.DataFrame:
        """
        Optimized: Identifies invoices in DataFrame missing from staging directory.
        """
        logging.info("Checking for missing folders in staging...")

        # Obtenemos todos los nombres de carpetas en staging una sola vez
        existing_folders = [f.name for f in self.staging_base.iterdir() if f.is_dir()]

        # Filtramos el DataFrame original buscando cuáles NO están en staging
        # Usamos una función lambda para verificar si el invoice_id está contenido en algún nombre
        missing_mask = self.df.index.to_series().apply(
            lambda x: not any(str(x) in folder for folder in existing_folders)
        )

        df_missing = self.df[missing_mask].reset_index()

        self._save_report(df_missing, "facturas_no_encontradas.csv", output_path)
        return df_missing

    def list_dirs_with_extra_text(
        self, output_path: Optional[Path] = None
    ) -> pd.DataFrame:
        """
        Lists directories in staging that don't exactly match the invoice code.
        """
        records = []
        logging.info("Analyzing directory names for extra text...")

        # iterdir() es más rápido que rglob("*") si solo buscas en el primer nivel de staging
        for path in self.staging_base.iterdir():
            if not path.is_dir():
                continue

            code = self._extract_invoice_code(path.name)

            # Si el código existe pero el nombre de la carpeta tiene más texto (ej: "HSL123_ADICIONAL")
            if code and code in self.df.index:
                if path.name != str(code):
                    records.append(
                        {
                            "Factura": code,
                            "Nombre Actual": path.name,
                            "Nombre Esperado": code,
                            "Ruta": str(path),
                        }
                    )

        df_extra = pd.DataFrame(records)
        self._save_report(df_extra, "directorios_con_texto_extra.csv", output_path)
        return df_extra
