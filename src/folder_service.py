import shutil
import logging
from pathlib import Path
from typing import Dict, List, NamedTuple
import pandas as pd


class FolderConsolidator:
    """Encargada de la manipulación física de las carpetas."""

    def __init__(self, target_root: Path):
        self.target_root = Path(target_root)
        self.target_root.mkdir(parents=True, exist_ok=True)

    def copy_folders(self, folders: List[Path], use_prefix: bool = True):
        """Copia una lista de carpetas al destino."""
        for folder in folders:
            dest = self._build_destination(folder, use_prefix)
            shutil.copytree(folder, dest, dirs_exist_ok=True)
            print(f"✅ Copiada: {folder.name} -> {dest.name}")

    def _build_destination(self, folder: Path, use_prefix: bool) -> Path:
        """Evita colisiones de nombres usando el nombre del padre (ej: SURA_Factura1)."""
        folder_name = (
            f"{folder.parent.name}_{folder.name}" if use_prefix else folder.name
        )
        return self.target_root / folder_name


class FolderScanner:
    """Encargada exclusivamente de la exploración del sistema de archivos."""

    @staticmethod
    def is_leaf_with_files(path: Path) -> bool:
        """Determina si una carpeta contiene archivos directamente."""
        if not path.is_dir():
            return False
        # any() con generador es eficiente: para al primer archivo encontrado
        return any(item.is_file() for item in path.iterdir())

    def get_content_folders(self, source_root: Path) -> List[Path]:
        """Escanea recursivamente y retorna solo directorios con archivos."""
        return [
            folder
            for folder in Path(source_root).rglob("**/")
            if self.is_leaf_with_files(folder)
        ]


# Definimos una estructura para el reporte final de la operación
class OperationSummary(NamedTuple):
    moved: int
    failed: int
    not_found: int
    errors: List[str]


class InvoiceFolderService:
    """
    Servicio de orquestación de archivos para la organización de facturas.

    Optimizado para manejar grandes volúmenes de datos mediante indexación
    previa del sistema de archivos.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        staging_base: Path,
        final_base: Path,
    ):
        """
        Args:
            df: DataFrame con el índice como ID de factura y columna 'Ruta'.
            staging_base: Directorio donde están las carpetas descargadas.
            final_base: Directorio raíz donde se organizará la jerarquía.
        """
        self.df = df
        self.staging_base = Path(staging_base)
        self.final_base = Path(final_base)
        self._logger = logging.getLogger(__name__)

        # Cache de carpetas en staging para evitar múltiples accesos a disco
        self._staging_cache: Dict[str, Path] = {}

    def _index_staging_area(self) -> None:
        """
        Escanea la carpeta staging una sola vez y mapea los IDs de factura
        con sus rutas físicas. Mejora el rendimiento de O(N^2) a O(N).
        """
        self._logger.info(f"Indexando carpetas en {self.staging_base}...")
        for folder in self.staging_base.iterdir():
            if folder.is_dir():
                # Extraemos el ID de la factura del nombre de la carpeta
                # (Asume que el ID está contenido en el nombre)
                self._staging_cache[folder.name] = folder

    def _safe_move(self, src: Path, dest: Path) -> bool:
        """
        Realiza el movimiento físico con validaciones de seguridad.
        """
        try:
            if dest.exists():
                self._logger.error(f"⚠️ Colisión: El destino ya existe -> {dest}")
                return False

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            return True

        except Exception as e:
            self._logger.error(f"🔥 Error crítico moviendo {src.name}: {e}")
            return False

    def organize(self, dry_run: bool = False) -> OperationSummary:
        """
        Ejecuta la migración de carpetas hacia la estructura final.
        """
        # 1. Preparación
        self._index_staging_area()
        stats = {"moved": 0, "failed": 0, "not_found": 0, "errors": []}

        # 2. Procesamiento
        for invoice_id, row in self.df.iterrows():
            # Buscamos en el cache el ID de la factura
            # Nota: Esto busca coincidencia exacta o parcial dependiendo de tu lógica
            # Aquí buscaremos cualquier carpeta que contenga el invoice_id
            source_path = next(
                (
                    path
                    for name, path in self._staging_cache.items()
                    if str(invoice_id) in name
                ),
                None,
            )

            if not source_path:
                self._logger.warning(f"❓ No encontrada en staging: {invoice_id}")
                stats["not_found"] += 1
                continue

            destination_path = self.final_base / row["Ruta"]

            if dry_run:
                self._logger.info(
                    f"[SIMULACIÓN] {source_path.name} -> {destination_path}"
                )
                stats["moved"] += 1
                continue

            # 3. Movimiento real
            success = self._safe_move(source_path, destination_path)

            if success:
                stats["moved"] += 1
                self._logger.info(f"✅ OK: {invoice_id}")
            else:
                stats["failed"] += 1
                stats["errors"].append(f"Fallo al mover {invoice_id}")

        return OperationSummary(
            moved=stats["moved"],
            failed=stats["failed"],
            not_found=stats["not_found"],
            errors=stats["errors"],
        )
