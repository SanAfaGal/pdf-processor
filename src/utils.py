import logging
import unicodedata
from pathlib import Path
from typing import Optional, List, Any, Dict, Union, Iterable
import shutil

import pandas as pd

# Configuración de Logging centralizada
logger = logging.getLogger(__name__)


class Util:
    """
    Provee utilidades transversales para manipulación de archivos,
    limpieza de texto y persistencia de datos.
    """

    @staticmethod
    def save_report(
        df: pd.DataFrame, default_name: str, custom_path: Optional[Path] = None
    ) -> None:
        """
        Guarda un DataFrame en formato Excel o CSV de forma segura.

        Args:
            df: El DataFrame a exportar.
            default_name: Nombre base del archivo si no se provee ruta.
            custom_path: Ruta completa (incluyendo nombre) donde se guardará.
        """
        if df.empty:
            logger.warning(
                f"⚠️ El reporte '{default_name}' está vacío. No se guardará nada."
            )
            return

        # Determinamos la ruta final
        save_path = Path(custom_path) if custom_path else Path(default_name)

        # Aseguramos que la carpeta de destino exista
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if save_path.suffix.lower() == ".csv":
                # utf-8-sig es esencial para que Excel abra el CSV con tildes correctamente
                df.to_csv(save_path, index=False, sep=";", encoding="utf-8-sig")
            else:
                # Forzamos extensión .xlsx si no tiene o es diferente a .csv
                save_path = save_path.with_suffix(".xlsx")
                df.to_excel(save_path, index=False, engine="openpyxl")

            logger.info(f"✅ Reporte generado: {save_path.name} ({len(df)} filas)")
        except Exception as e:
            logger.error(f"🔥 Error fatal guardando el reporte en {save_path}: {e}")

    @staticmethod
    def remove_accents(text: Any) -> str:
        """
        Elimina tildes y normaliza texto. Seguro para valores no-string (NaN, None, int).

        Ejemplo: 'Campaña' -> 'Campana'
        """
        if not isinstance(text, str):
            return ""

        # Normalización NFD separa el carácter de la tilde
        normalized = unicodedata.normalize("NFD", text)
        # Filtramos solo los caracteres que no sean marcas de acento
        return "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    @staticmethod
    def safe_move(src: Path, dest: Path) -> bool:
        """
        Realiza el movimiento físico con validaciones de seguridad.
        """
        try:
            if dest.exists():
                logger.error(f"⚠️ Colisión: El destino ya existe -> {dest}")
                return False

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            return True

        except Exception as e:
            logger.error(f"🔥 Error crítico moviendo {src.name}: {e}")
            return False
        
    @staticmethod
    def get_list_from_file(file_path: Union[str, Path]) -> List[str]:
        """
        Lee un archivo de texto y retorna una lista de líneas limpias.

        Args:
            file_path: Ruta al archivo .txt
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"❌ El archivo de lista no existe: {path}")
            return []

        try:
            with path.open("r", encoding="UTF-8") as file:
                # strip() elimina saltos de línea y espacios en blanco innecesarios
                # if line.strip() evita agregar líneas vacías
                return [line.strip() for line in file if line.strip()]
        except Exception as e:
            logger.error(f"❌ Error leyendo {path}: {e}")
            return []

    @staticmethod
    def flatten_prefixes(prefixes_dict: Dict[str, Union[str, List[str]]]) -> List[str]:
        """
        Aplana un diccionario de prefijos en una lista simple.
        Útil para validaciones rápidas de tipos de documentos.
        """
        flat_list = []
        for value in prefixes_dict.values():
            if isinstance(value, list):
                flat_list.extend(value)
            else:
                flat_list.append(str(value))
        return list(set(flat_list))  # Retorna valores únicos

    @staticmethod
    def save_list_as_file(values: Iterable = None, file: Path = None):
        if values is None:
            values = []

        # Aseguramos que el directorio exista
        file = Path(file)
        file.parent.mkdir(parents=True, exist_ok=True)

        with open(file, "w", encoding="UTF-8") as f:
            # La clave está en el f-string: {v}\n
            # Esto añade el salto de línea a cada elemento automáticamente
            f.writelines(f"{v}\n" for v in values)
