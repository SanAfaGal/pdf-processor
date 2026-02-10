from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import pandas as pd
import numpy as np
from .utils import Util


class DataManager:
    """
    Handles data ingestion and normalization with pre-processing audit capabilities.
    """

    def __init__(self, admin_map: Dict[str, str], contract_map: Dict[str, str]):
        self._df: Optional[pd.DataFrame] = None
        self._df_processed: Optional[pd.DataFrame] = None
        self.admin_map = admin_map
        self.contract_map = contract_map

    def load_excel(self, file_path: Path, use_cols: List[str]) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        # Cargamos todo como string para la auditoría inicial
        self._df = pd.read_excel(path, usecols=use_cols, dtype=str)
        print(f"✅ Archivo cargado: {len(self._df)} filas detectadas.")

    def run_pre_audit(self) -> bool:
        """
        Realiza una auditoría sobre los datos crudos antes de cualquier limpieza.
        Retorna True si todo está correctamente mapeado.
        """
        if self._df is None:
            raise ValueError("No hay datos para auditar.")

        # Extraemos valores únicos de la data cruda (limpiando solo espacios básicos)
        # para comparar contra las llaves de tus diccionarios
        raw_admins = set(self._df["Administradora"].dropna().unique())
        raw_contracts = set(self._df["Contrato"].dropna().unique())

        missing_admins = raw_admins - set(self.admin_map.keys())
        missing_contracts = raw_contracts - set(self.contract_map.keys())

        self._print_audit_report(missing_admins, missing_contracts)

        # Retorna True si no hay elementos faltantes
        return len(missing_admins) == 0 and len(missing_contracts) == 0

    def _print_audit_report(
        self, missing_admins: Set[str], missing_contracts: Set[str]
    ):
        print("\n" + "🔍 ANALISIS PREVIO DE MAPEOS " + "🔍")
        print("-" * 40)

        if not missing_admins and not missing_contracts:
            print("✨ EXCELENTE: Todos los valores existen en los diccionarios.")
        else:
            if missing_admins:
                print(f"❌ ADMINS FALTANTES ({len(missing_admins)}):")
                for item in missing_admins:
                    print(f"   - {item}")

            if missing_contracts:
                print(f"\n❌ CONTRATOS FALTANTES ({len(missing_contracts)}):")
                for item in missing_contracts:
                    print(f"   - {item}")
        print("-" * 40 + "\n")

    def export_to_excel(self, df: pd.DataFrame, report_path: Path):
        """Exporta el DataFrame a un archivo Excel."""
        try:
            Util.save_report(df, "audit.xlsx", report_path)
            print(f"✅ Excel guardado en: {report_path}")
        except Exception as e:
            print(f"❌ Error Excel: {e}")

    def export_invoice_list(self, df: pd.DataFrame, list_path: Path):
        """Exporta la lista de facturas a un archivo de texto."""
        try:
            # Extraemos las facturas desde el índice
            invoices = df.index.tolist()
            Util.save_list_as_file(invoices, list_path)
            print(f"✅ Lista guardada en: {list_path}")
        except Exception as e:
            print(f"❌ Error Lista: {e}")

    def _clean_and_format_data(self):
        """Toma el DF original y genera la base de trabajo."""
        df = self._df.dropna(subset=["Doc", "No Doc", "Administradora"]).copy()

        # Optimizamos la conversión numérica
        df["No Doc"] = (
            pd.to_numeric(df["No Doc"], errors="coerce").astype("Int64").astype(str)
        )
        df["Doc"] = df["Doc"].str.strip().str.upper()
        df["Factura"] = df["Doc"] + df["No Doc"]
        return df

    def _apply_normalizations(self, df: pd.DataFrame):
        """Mapea administradoras y contratos."""
        df["Administradora"] = df["Administradora"].map(self.admin_map)
        df["Contrato"] = df["Contrato"].map(self.contract_map)
        return df

    def _generate_file_paths(self, df: pd.DataFrame):
        """Calcula rutas usando lógica de Path directamente."""

        def build_path(row):
            # Usamos el operador / de pathlib, es más limpio
            path = Path(str(row["Administradora"]))
            if pd.notna(row["Contrato"]):
                path /= str(row["Contrato"])
            return str(path / str(row["Factura"]))

        df["Ruta"] = df.apply(build_path, axis=1)
        return df

    def process_data(self) -> pd.DataFrame:
        """Orquestador optimizado."""
        if self._df is None:
            raise ValueError("No hay datos cargados para procesar.")

        # Flujo lineal: Cada paso recibe el resultado del anterior
        df = self._clean_and_format_data()
        df = self._apply_normalizations(df)
        df = self._generate_file_paths(df)

        # Limpieza final
        df = df.dropna(subset=["Administradora", "Ruta"])
        df.set_index("Factura", inplace=True)

        self._df_processed = df
        return self._df_processed
