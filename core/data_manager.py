"""
Data ingestion, normalization, and pre-processing audit.
Loads Excel, validates mappings, and produces processed DataFrame with paths.
"""
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd

from utils.persistence import save_report, save_list_as_file


class DataManager:
    """
    Handles Excel load, pre-audit (admin/contract mapping check), and processing.
    Raises FileNotFoundError if Excel missing; ValueError if no data loaded for audit/process.
    """

    def __init__(
        self,
        admin_map: Dict[str, object],
        contract_map: Dict[str, object],
    ) -> None:
        self._df: Optional[pd.DataFrame] = None
        self._df_processed: Optional[pd.DataFrame] = None
        self.admin_map = admin_map
        self.contract_map = contract_map

    def load_excel(self, file_path: Path, use_cols: List[str]) -> None:
        """
        Load Excel with given columns (all as string).
        Raises: FileNotFoundError if path does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")
        self._df = pd.read_excel(path, usecols=use_cols, dtype=str)
        print(f"Archivo cargado: {len(self._df)} filas.")

    def run_pre_audit(self) -> bool:
        """
        Audit raw data against admin and contract maps.
        Returns True if all values are mapped; False otherwise.
        Raises: ValueError if no data loaded.
        """
        if self._df is None:
            raise ValueError("No hay datos para auditar.")
        raw_admins = set(self._df["Administradora"].dropna().unique())
        raw_contracts = set(self._df["Contrato"].dropna().unique())
        missing_admins = raw_admins - set(self.admin_map.keys())
        missing_contracts = raw_contracts - set(self.contract_map.keys())
        self._print_audit_report(missing_admins, missing_contracts)
        return len(missing_admins) == 0 and len(missing_contracts) == 0

    def _print_audit_report(
        self,
        missing_admins: Set[str],
        missing_contracts: Set[str],
    ) -> None:
        print("\nANALISIS PREVIO DE MAPEOS")
        print("-" * 40)
        if not missing_admins and not missing_contracts:
            print("Todos los valores existen en los diccionarios.")
        else:
            if missing_admins:
                print(f"ADMINS FALTANTES ({len(missing_admins)}):")
                for item in missing_admins:
                    print(f"   - {item}")
            if missing_contracts:
                print(f"CONTRATOS FALTANTES ({len(missing_contracts)}):")
                for item in missing_contracts:
                    print(f"   - {item}")
        print("-" * 40 + "\n")

    def export_to_excel(self, df: pd.DataFrame, report_path: Path) -> None:
        """Export DataFrame to Excel. Logs errors; does not raise."""
        try:
            save_report(df, "audit.xlsx", report_path)
            print(f"Excel guardado en: {report_path}")
        except Exception as e:
            print(f"Error Excel: {e}")

    def export_invoice_list(self, df: pd.DataFrame, list_path: Path) -> None:
        """Export invoice list (index) to text file. Logs errors; does not raise."""
        try:
            invoices = df.index.tolist()
            save_list_as_file(invoices, list_path)
            print(f"Lista guardada en: {list_path}")
        except Exception as e:
            print(f"Error lista: {e}")

    def _clean_and_format_data(self) -> pd.DataFrame:
        df = self._df.dropna(subset=["Doc", "No Doc", "Administradora"]).copy()
        df["No Doc"] = (
            pd.to_numeric(df["No Doc"], errors="coerce").astype("Int64").astype(str)
        )
        df["Doc"] = df["Doc"].str.strip().str.upper()
        df["Factura"] = df["Doc"] + df["No Doc"]
        return df

    def _apply_normalizations(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Administradora"] = df["Administradora"].map(self.admin_map)
        df["Contrato"] = df["Contrato"].map(self.contract_map)
        return df

    def _generate_file_paths(self, df: pd.DataFrame) -> pd.DataFrame:
        def build_path(row: pd.Series) -> str:
            path = Path(str(row["Administradora"]))
            if pd.notna(row["Contrato"]):
                path /= str(row["Contrato"])
            return str(path / str(row["Factura"]))

        df["Ruta"] = df.apply(build_path, axis=1)
        return df

    def process_data(self) -> pd.DataFrame:
        """
        Clean, normalize, and build paths. Sets index to Factura.
        Raises: ValueError if no data loaded.
        """
        if self._df is None:
            raise ValueError("No hay datos cargados para procesar.")
        df = self._clean_and_format_data()
        df = self._apply_normalizations(df)
        df = self._generate_file_paths(df)
        df = df.dropna(subset=["Administradora", "Ruta"])
        df.set_index("Factura", inplace=True)
        self._df_processed = df
        return self._df_processed
