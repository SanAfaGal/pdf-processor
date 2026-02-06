import io
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from utils import Util

# Configuraciones iniciales
SERVICE_ACCOUNT_FILE = "auditoria-486600-13cc49b82b71.json"  # Tu archivo descargado
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def authenticate():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def download_file(service, file_id, file_name, local_path):
    print(f"Descargando archivo: {file_name}")
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(os.path.join(local_path, file_name), "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        # print(f"Progreso: {int(status.progress() * 100)}%")


def download_folder_recursive(service, folder_id, local_path):
    # 1. Listar archivos y carpetas dentro de la carpeta actual de Drive
    query = f"'{folder_id}' in parents and trashed = false"
    results = (
        service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    )
    items = results.get("files", [])

    # Si la carpeta de Drive está totalmente vacía, salimos de inmediato
    if not items:
        return

    for item in items:
        if item["mimeType"] == "application/vnd.google-apps.folder":
            # Es una subcarpeta: llamar recursivamente
            subfolder_path = os.path.join(local_path, item["name"])
            download_folder_recursive(service, item["id"], subfolder_path)
        else:
            # Es un archivo:
            # Solo intentamos descargar si NO es un archivo nativo de Google (Docs, Sheets, etc.)
            # o si decides implementar el export_media más adelante.
            if "google-apps" not in item["mimeType"]:
                # --- CAMBIO CLAVE ---
                # Solo creamos la carpeta local en el momento exacto en que vamos a bajar un archivo
                if not os.path.exists(local_path):
                    os.makedirs(local_path)

                download_file(service, item["id"], item["name"], local_path)
            else:
                print(f"ℹ️ Omitiendo archivo de Google Workspace: {item['name']}")


def find_folder_anywhere(service, folder_name):
    """
    Busca carpetas que coincidan con el nombre en CUALQUIER nivel de profundidad.
    """
    # Usamos 'contains' por si el nombre tiene espacios o variaciones como AMULAR
    query = (
        f"name contains '{folder_name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    results = (
        service.files()
        .list(
            q=query,
            fields="files(id, name, parents)",  # 'parents' nos sirve para verificar si queremos
            pageSize=10,
        )
        .execute()
    )

    return results.get("files", [])


def download_missing_folders(service, dirs_missing, local_root):
    """
    Itera la lista de faltantes y busca cada una en profundidad.
    """
    for target_name in dirs_missing:
        print(f"🔍 Buscando '{target_name}' en todas las subcarpetas...")

        folders_found = find_folder_anywhere(service, target_name)

        if not folders_found:
            print(f"❌ No se encontró nada para: {target_name}")
            continue

        for folder in folders_found:
            print(f"✅ Encontrada: {folder['name']} (ID: {folder['id']})")

            # Creamos la ruta local
            local_path = os.path.join(local_root, folder["name"])

            # Descargamos el contenido (usando la función recursiva de antes)
            download_folder_recursive(service, folder["id"], local_path)


if __name__ == "__main__":
    drive_service = authenticate()
    # BASE_FOLDER_ID = (
    #     "15n1gZAxUZhKpNgb8nmIjrSYhanQHAYWU"  # El ID está en la URL de la carpeta
    # )
    LOCAL_DESTINATION = r"C:\Users\sanaf\Desktop\Carpeta compartida\SEPTIEMBRE"

    dirs_to_download = Util.get_list_from_file("Facturas.txt")

    # Buscar el nombre de las carpetas en toda la ruta partiendo desde la base
    download_missing_folders(drive_service, dirs_to_download, LOCAL_DESTINATION)

    # Descargar una carpeta completa con todo su contenido, ya sean carpetas o archivos
    # download_folder_recursive(drive_service, BASE_FOLDER_ID, LOCAL_DESTINATION)
    print("¡Descarga completada!")
