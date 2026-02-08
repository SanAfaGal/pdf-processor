import os, sys
from pathlib import Path
from dotenv import load_dotenv
from .hospitals import HOSPITALS

# Cargar el archivo .env apenas inicia el programa
load_dotenv()


class Config:
    # --- LLAVE DE ACCESO A DRIVE ---
    DRIVE_CREDENTIALS = Path(
        os.getenv("DRIVE_CREDENTIALS", "config/keys/secret_key.json")
    )

    # --- INFRAESTRUCTURA (Paths) ---
    STORAGE_ROOT = Path(os.getenv("FINAL_PATH", "./data/final"))
    STAGING_ZONE = Path(os.getenv("STAGING_PATH", "./data/staging"))

    # --- ENTRADAS (Inputs) ---
    RAW_REPORT_PATH = Path(os.getenv("SIHOS_REPORT_PATH", "config/report.xlsx"))
    INVOICE_TARGET_LIST = Path(
        os.getenv("INVOICES_LIST_FILE_PATH", "config/invoices.txt")
    )

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
        print(
            f"🔍 AUDITORÍA DE CONFIGURACIÓN - {os.getenv('ACTIVE_HOSPITAL', 'GENERAL')}"
        )
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

        # 2. Listar variables del Hospital seleccionado
        if HOSPITAL:
            print(
                f"\n🏥 ESPECIFICACIONES DEL HOSPITAL ({os.getenv('ACTIVE_HOSPITAL')}):"
            )
            for key, value in HOSPITAL.items():
                # Si el valor es un diccionario (como DOCUMENT_STANDARDS), lo mostramos bonito
                if isinstance(value, dict):
                    print(f"   🔸 {key}:")
                    for subkey, subval in value.items():
                        print(f"      - {subkey:<15} : {subval}")
                else:
                    print(f"   🔸 {key:<25} : {value}")
        else:
            print("\n⚠️  ADVERTENCIA: No hay datos específicos de Hospital cargados.")

        print("\n" + "═" * 60)
        confirm = (
            input("⚠️  ¿Desea continuar con estos parámetros? (S/N): ").strip().upper()
        )

        if confirm != "S":
            print("\n🛑 Ejecución detenida por el usuario.")
            sys.exit()

        print("🚀 Arrancando motores...\n")


HOSPITAL = HOSPITALS.get(os.getenv("ACTIVE_HOSPITAL"))
