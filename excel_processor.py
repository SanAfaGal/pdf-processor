from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Optional

from utils import Util


class DataManager:
    """
    Handles data ingestion, cleaning, and transformation logic for invoice processing.
    """

    def __init__(self, admin_map: Dict[str, str], contract_map: Dict[str, str]):
        """
        Initialize with mapping dictionaries for normalization.
        """
        self.df: Optional[pd.DataFrame] = None
        self.admin_map = admin_map
        self.contract_map = contract_map

    def get_dataframe(self) -> pd.DataFrame:
        """
        Returns the current DataFrame.
        """
        if self.df is None:
            raise ValueError("DataFrame is not loaded. Call load_excel() first.")
        return self.df

    def load_excel(self, file_path: Path, use_cols: list) -> pd.DataFrame:
        """
        Reads the Excel file with specific columns and forces string types to avoid data loss.
        """
        # Ensure path is Path object
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Report not found at: {path}")

        # Loading with specific dtypes to handle leading zeros or large numbers
        self.df = pd.read_excel(path, usecols=use_cols, dtype=str)
        return self.df

    def audit_mappings(self):
        """
        Identifies and logs values that are not present in the mapping dictionaries.
        """
        if self.df is None:
            return

        # Administradoras no presentes en el diccionario
        admins_no_mapeadas = self.df.loc[
            ~self.df["Administradora"].isin(self.admin_map.keys()), "Administradora"
        ].unique()

        # Contratos no presentes en el diccionario
        contratos_no_mapeados = self.df.loc[
            ~self.df["Contrato"].isin(self.contract_map.keys()), "Contrato"
        ].unique()

        # Imprimir resultados
        print("\n--- AUDITORÍA DE MAPEOS ---")
        if len(admins_no_mapeadas) > 0:
            print(f"⚠️ Administradoras NO mapeadas: {admins_no_mapeadas}")
        else:
            print("✅ Todas las Administradoras están mapeadas.")

        if len(contratos_no_mapeados) > 0:
            print(f"⚠️ Contratos NO mapeados: {contratos_no_mapeados}")
        else:
            print("✅ Todos los Contratos están mapeados.")
        print("---------------------------\n")

    def prepare_data(self, export_report: bool = True) -> pd.DataFrame:
        """
        Normalizes columns, builds the Primary Key (Factura), and generates destination paths.
        """
        if self.df is None:
            raise ValueError("No data loaded. Call load_excel() first.")

        # 1. Basic Cleaning
        # Remove rows where essential ID columns are missing
        self.df.dropna(subset=["Doc", "No Doc", "Administradora"], inplace=True)

        # 2. Key Generation (Factura)
        # We ensure No Doc is treated as an integer-string to remove decimals like '123.0'
        self.df["No Doc"] = (
            pd.to_numeric(self.df["No Doc"], errors="coerce")
            .astype("Int64")
            .astype(str)
        )
        self.df["Doc"] = self.df["Doc"].str.strip().str.upper()

        # Build the unique identifier (e.g., HSL + 354753)
        self.df["Factura"] = self.df["Doc"] + self.df["No Doc"]

        self.audit_mappings()

        # 3. Normalization via Mappings
        # Transform long names into short folder-friendly names
        self.df["Administradora"] = self.df["Administradora"].map(self.admin_map)
        self.df["Contrato"] = self.df["Contrato"].map(self.contract_map)

        # 4. Path Construction
        # Logical hierarchy: Admin / [Contract if exists] / Invoice_ID
        self.df["Ruta"] = np.where(
            self.df["Contrato"].notna(),
            self.df["Administradora"]
            + "/"
            + self.df["Contrato"]
            + "/"
            + self.df["Factura"],
            self.df["Administradora"] + "/" + self.df["Factura"],
        )

        # 5. Final Filtering
        # Remove any row that couldn't be mapped to a destination
        self.df.dropna(subset=["Administradora", "Ruta"], inplace=True)

        self.df.set_index("Factura", inplace=True)

        print(self.df.head())
        # 6. Export Prepared Data
        if export_report:
            Util.save_report(df=self.df, default_name="data_preparada.xlsx")

        return self.df
