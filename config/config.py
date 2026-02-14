import os, sys
from pathlib import Path
from dotenv import load_dotenv
from .hospitals import HOSPITALS

# Cargar el archivo .env apenas inicia el programa
load_dotenv()


class Config:
    
    # --- Logging ---
    LOG_LEVEL = Path(os.getenv("LOG_LEVEL"))
    
    # --- DATOS DEL HOSPITAL ---
    ACTIVE_HOSPITAL = os.getenv("ACTIVE_HOSPITAL")
    HOSPITAL = HOSPITALS.get(ACTIVE_HOSPITAL)

    # --- LLAVE DE ACCESO A DRIVE ---
    DRIVE_CREDENTIALS = Path(os.getenv("DRIVE_CREDENTIALS"))

    # --- INFRAESTRUCTURA (Paths) ---
    ROOT_DIR = Path(os.getenv("ROOT_PATH"))
    STORAGE_ROOT = Path(os.getenv("STORAGE_PATH"))
    STAGING_ZONE = Path(os.getenv("STAGING_PATH"))
    MISSING_FOLDERS = Path(os.getenv("MISSING_FOLDERS_PATH"))
    MISSING_FILES = Path(os.getenv("MISSING_FILES_PATH"))

    # --- ENTRADAS (Inputs) ---
    SIHOS_REPORT_PATH = Path(os.getenv("SIHOS_REPORT_PATH"))
    AUDIT_REPORT_PATH = Path(os.getenv("AUDIT_REPORT_PATH"))
    INVOICE_TARGET_LIST = Path(os.getenv("INVOICES_LIST_FILE_PATH"))

    # Columnas requeridas para el procesamiento de datos
    DATA_SCHEMA_COLUMNS = [
        "Doc",
        "No Doc",
        "Documento",
        "Numero",
        "Paciente",
        "Administradora",
        "Contrato",
        "Operario",
    ]

    @classmethod
    def show_summary(cls):
        """Lista dinámicamente toda la configuración sin conocer las llaves de antemano."""
        print("\n" + "═" * 60)
        print(f"🔍 AUDITORÍA DE CONFIGURACIÓN")
        print("═" * 60)

        # 1. Listar variables de la Clase Config
        print("\n⚙️  PARÁMETROS DEL SISTEMA (Config):")
        # vars(cls) nos da un diccionario con todo lo que hay en la clase
        for key, value in vars(cls).items():
            if not key.startswith("__") and not callable(value):
                # Formateamos el nombre para que se vea limpio
                if isinstance(value, dict):
                    print(f"   🔹 {key}:")
                    for subkey, subval in value.items():
                        print(f"      - {subkey:<15} : {subval}")
                else:
                    print(f"   🔹 {key:<25} : {value}")

        print("\n" + "═" * 60)
        confirm = (
            input("⚠️  ¿Desea continuar con estos parámetros? (S/N): ").strip().upper()
        )

        if confirm != "S":
            print("\n🛑 Ejecución detenida por el usuario.")
            sys.exit()

        print("🚀 Arrancando motores...\n")
