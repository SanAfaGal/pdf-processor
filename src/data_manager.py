from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import pandas as pd
import numpy as np


class DataManager:
    """
    Handles data ingestion and normalization with pre-processing audit capabilities.
    """

    def __init__(self, admin_map: Dict[str, str], contract_map: Dict[str, str]):
        self._df: Optional[pd.DataFrame] = None
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

    def process_data(self):
        """
        Realiza la transformación una vez que la auditoría es satisfactoria.
        """
        df = self._df

        # 1. Limpieza de Identificadores
        df.dropna(subset=["Doc", "No Doc", "Administradora"], inplace=True)
        df["No Doc"] = (
            pd.to_numeric(df["No Doc"], errors="coerce").astype("Int64").astype(str)
        )
        df["Doc"] = df["Doc"].str.strip().str.upper()
        df["Factura"] = df["Doc"] + df["No Doc"]

        # 2. Mapeo (Normalización)
        df["Administradora"] = df["Administradora"].map(self.admin_map)
        df["Contrato"] = df["Contrato"].map(self.contract_map)

        # 3. Construcción de Rutas (Uso de Path para mayor seguridad)
        def build_path(row):
            base = Path(str(row["Administradora"]))
            if pd.notna(row["Contrato"]):
                return str(base / str(row["Contrato"]) / str(row["Factura"]))
            return str(base / str(row["Factura"]))

        df["Ruta"] = df.apply(build_path, axis=1)

        # 4. Finalización
        df.dropna(subset=["Administradora", "Ruta"], inplace=True)
        df.set_index("Factura", inplace=True)

        return df
