"""Excel data processing and normalization module."""

import logging
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd

from ..config.settings import settings
from ..config.exceptions import DataValidationError
from ..config.logger import setup_logger

logger = setup_logger(__name__)


class DataManager:
    """
    Manages Excel file loading, data normalization, and invoice metadata generation.

    This class handles:
    - Excel report ingestion
    - Data cleaning and validation
    - Invoice hierarchy path generation
    - Administrative and contract mapping
    """

    def __init__(
        self,
        report_path: Optional[Path] = None,
        administradoras: Optional[Dict[str, str]] = None,
        contracts: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize DataManager.

        Args:
            report_path: Path to Excel report file. Defaults to settings.report_path
            administradoras: Mapping of administradoras names to standardized names
            contracts: Mapping of contract types to standardized names

        Raises:
            DataValidationError: If administradoras or contracts mappings are invalid
        """
        self.report_path = report_path or settings.report_path
        self._df: Optional[pd.DataFrame] = None

        # Import lookup tables from settings module
        if administradoras is None or contracts is None:
            from ..config import settings as settings_module

            administradoras = administradoras or settings_module.ADMINISTRADORAS
            contracts = contracts or settings_module.CONTRATOS

        self.administradoras = administradoras
        self.contracts = contracts
        logger.info(f"DataManager initialized with report: {self.report_path}")

    def load_excel(self) -> pd.DataFrame:
        """
        Load and normalize Excel report.

        The Excel file should contain columns: Doc, No Doc, Administradora,
        Contrato, and other invoice metadata.

        Returns:
            Normalized DataFrame with columns: Doc, No Doc, Administradora,
            Contrato, Factura, folder_path

        Raises:
            DataValidationError: If file not found or sheet structure invalid
        """
        if not self.report_path.exists():
            msg = f"Report file not found: {self.report_path}"
            logger.error(msg)
            raise DataValidationError(msg)

        try:
            logger.info(f"Loading Excel report: {self.report_path}")
            self._df = pd.read_excel(
                self.report_path,
                usecols=settings.COLUMNS_TO_USE,
                dtype={"Doc": str},
            )
            logger.info(f"Loaded {len(self._df)} rows from Excel")

            return self._normalize_data()
        except Exception as e:
            msg = f"Error loading Excel file: {str(e)}"
            logger.error(msg)
            raise DataValidationError(msg) from e

    def _normalize_data(self) -> pd.DataFrame:
        """
        Normalize loaded DataFrame.

        Operations:
        - Drop rows with missing required fields
        - Convert "No Doc" to integer-string format (remove .0 decimals)
        - Normalize "Doc" to uppercase
        - Generate "Factura" ID
        - Map administradoras and contracts
        - Generate folder hierarchy paths
        - Set "Factura" as index

        Returns:
            Normalized DataFrame

        Raises:
            DataValidationError: If critical normalization fails
        """
        if self._df is None:
            msg = "No data loaded. Call load_excel() first."
            logger.error(msg)
            raise DataValidationError(msg)

        df = self._df.copy()

        # Drop rows with missing required fields
        initial_count = len(df)
        df = df.dropna(subset=["Doc", "No Doc", "Administradora"])
        dropped = initial_count - len(df)
        if dropped > 0:
            logger.warning(f"Dropped {dropped} rows with missing required fields")

        # Convert "No Doc" to integer-string (remove decimal notation)
        try:
            df["No Doc"] = df["No Doc"].astype(int).astype(str)
        except Exception as e:
            logger.warning(f"Error converting 'No Doc' to integer: {e}")

        # Normalize Doc to uppercase
        df["Doc"] = df["Doc"].str.upper()

        # Generate Factura ID (e.g., "HSL354753")
        df["Factura"] = settings.document_suffix + df["No Doc"]

        # Map administradoras
        df["Administradora"] = df["Administradora"].map(
            self.administradoras
        ).fillna(df["Administradora"])

        # Map contracts
        df["Contrato"] = df["Contrato"].map(self.contracts).fillna(df["Contrato"])

        # Generate folder paths: "Administradora/Contrato/Factura"
        df["folder_path"] = df.apply(
            lambda row: Path(row["Administradora"]) / row["Contrato"] / row["Factura"],
            axis=1,
        )

        # Drop rows with unmapped administradoras (all NaN values)
        before_drop = len(df)
        df = df.dropna(subset=["Administradora"])
        unmapped = before_drop - len(df)
        if unmapped > 0:
            logger.warning(f"Dropped {unmapped} rows with unmapped administradoras")

        # Set Factura as index for fast lookups
        df.set_index("Factura", inplace=True)

        logger.info(
            f"Normalized {len(df)} invoices with {len(df.columns)} metadata columns"
        )
        return df

    def get_expected_files(self) -> Dict[str, Path]:
        """
        Get mapping of invoice IDs to expected folder paths.

        Returns:
            Dictionary where key is invoice ID (e.g., "HSL354753")
            and value is Path object for expected location
        """
        if self._df is None:
            self.load_excel()

        if self._df is None:
            msg = "Failed to load Excel data"
            logger.error(msg)
            raise DataValidationError(msg)

        return {idx: row["folder_path"] for idx, row in self._df.iterrows()}

    def get_invoice_metadata(self, invoice_id: str) -> Optional[Dict[str, str]]:
        """
        Get metadata for a specific invoice.

        Args:
            invoice_id: Invoice identifier (e.g., "HSL354753")

        Returns:
            Dictionary with invoice metadata or None if not found
        """
        if self._df is None:
            self.load_excel()

        if self._df is None or invoice_id not in self._df.index:
            return None

        return self._df.loc[invoice_id].to_dict()
