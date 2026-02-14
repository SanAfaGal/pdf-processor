import io
import logging
from pathlib import Path
from typing import List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Configuración de Logging
logger = logging.getLogger(__name__)


class GoogleDriveService:
    """
    Servicio para interactuar con Google Drive API.
    Permite búsquedas globales y descargas recursivas de directorios.
    """

    DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"

    def __init__(self, credentials_path: Path, scopes: List[str]):
        self.creds = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=scopes
        )
        self.service = build("drive", "v3", credentials=self.creds)

    def find_folders_by_name(self, folder_name: str) -> List[dict]:
        """Busca carpetas que coincidan con el nombre en cualquier nivel."""
        query = (
            f"name contains '{folder_name}' "
            f"and mimeType = '{self.DRIVE_FOLDER_MIME}' "
            f"and trashed = false"
        )

        results = (
            self.service.files()
            .list(q=query, fields="files(id, name, parents)", pageSize=10)
            .execute()
        )

        return results.get("files", [])

    def download_file(self, file_id: str, file_name: str, local_dir: Path) -> None:
        """Descarga un archivo individual de Drive al sistema local."""
        try:
            request = self.service.files().get_media(fileId=file_id)
            local_dir.mkdir(parents=True, exist_ok=True)
            file_path = local_dir / file_name

            with io.FileIO(str(file_path), "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            logger.info(f"✅ Descargado: {file_name}")
        except Exception as e:
            logger.error(f"❌ Error descargando {file_name}: {e}")

    def download_recursive(
        self, folder_id: str, local_path: Path, depth: int = 0
    ) -> None:
        """Descarga el contenido de una carpeta de Drive con reporte visual de progreso."""
        # Creamos un prefijo visual basado en la profundidad (subcarpetas)
        indent = "  " * depth

        # 1. Reportar qué carpeta estamos procesando actualmente
        print(f"{indent}📂 PROCESANDO CARPETA: {local_path.name}")

        query = f"'{folder_id}' in parents and trashed = false"
        results = (
            self.service.files()
            .list(q=query, fields="files(id, name, mimeType)")
            .execute()
        )

        items = results.get("files", [])

        if not items and depth == 0:
            print(f"{indent}  ⚠️ Esta carpeta parece estar vacía en Drive.")

        for item in items:
            item_name = item["name"]
            item_id = item["id"]

            if item["mimeType"] == self.DRIVE_FOLDER_MIME:
                # Reportar que entramos a una subcarpeta
                new_local_path = local_path / item_name
                # Pasamos depth + 1 para que el print de la subcarpeta salga más a la derecha
                self.download_recursive(item_id, new_local_path, depth + 1)
            else:
                # Es un archivo
                if "google-apps" not in item["mimeType"]:
                    print(f"{indent}  📥 Descargando archivo: {item_name}")
                    self.download_file(item_id, item_name, local_path)
                else:
                    print(f"{indent}  ⏩ Omitiendo (Google Doc/Sheet): {item_name}")

    def sync_missing_folders(self, folder_names: List[str], local_root: Path) -> None:
        """Orquestador: Busca nombres en Drive y descarga los encontrados."""
        for target in folder_names:
            logger.info(f"🔍 Buscando en Drive: {target}")
            found = self.find_folders_by_name(target)

            if not found:
                logger.warning(f"⚠️ No se encontró la carpeta: {target}")
                continue

            for folder in found:
                dest = local_root / folder["name"]
                self.download_recursive(folder["id"], dest)

    def sync_specific_files(self, file_names: List[str], local_root: Path) -> None:
        """Busca archivos específicos y reporta el progreso detallado por consola."""
        print(f"\n🔍 INICIANDO BÚSQUEDA DE {len(file_names)} ARCHIVOS ESPECÍFICOS...")
        
        files_not_found = set()

        for name in file_names:
            query = (
                f"name = '{name}' "
                f"and mimeType != '{self.DRIVE_FOLDER_MIME}' "
                f"and trashed = false"
            )
            
            results = self.service.files().list(
                q=query, 
                fields="files(id, name)", 
                pageSize=1
            ).execute()
            
            files = results.get("files", [])
            
            
            if not files:
                print(f"  ⚠️  No se encontró: {name} (Omitiendo)")
                files_not_found.add(name)
                continue
            
            file_info = files[0]
            print(f"  ✨ Archivo encontrado: {file_info['name']}")
            
            # Reutiliza tu función original que ya tiene el logger.info interno
            self.download_file(file_info['id'], file_info['name'], local_root)
        
        print("\n❌ ARCHIVOS NO ENCONTRADOS")
        print(*files_not_found, sep="\n")