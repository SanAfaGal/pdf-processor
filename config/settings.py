"""
Application settings loaded from environment variables.
Validates required keys and hospital config at import.
"""
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Required env keys (paths and critical config)
_REQUIRED_KEYS = [
    "ACTIVE_HOSPITAL",
    "ROOT_PATH",
    "STORAGE_PATH",
    "STAGING_PATH",
    "MISSING_FOLDERS_PATH",
    "MISSING_FILES_PATH",
    "SIHOS_REPORT_PATH",
    "AUDIT_REPORT_PATH",
    "INVOICES_LIST_FILE_PATH",
    "DRIVE_CREDENTIALS",
]


def _get_path(key: str) -> Path:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return Path()
    return Path(value.strip())


def _get_str(key: str, default: str = "") -> str:
    value = os.getenv(key)
    return value.strip() if value else default


def _validate() -> None:
    """Ensure required env vars are set and HOSPITAL is valid. Exits on failure."""
    missing = [k for k in _REQUIRED_KEYS if not (os.getenv(k) or "").strip()]
    if missing:
        print(f"Error: missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    from config.hospitals import HOSPITALS

    active = _get_str("ACTIVE_HOSPITAL")
    if not active or active not in HOSPITALS:
        print(
            f"Error: ACTIVE_HOSPITAL must be one of {list(HOSPITALS.keys())}, got: {repr(active)}",
            file=sys.stderr,
        )
        sys.exit(1)


# Validate on load so rest of app can assume config is valid
_validate()

from config.hospitals import HOSPITALS

ACTIVE_HOSPITAL = _get_str("ACTIVE_HOSPITAL")
HOSPITAL: dict[str, Any] = HOSPITALS[ACTIVE_HOSPITAL]

# Logging: keep as string (e.g. "INFO", "DEBUG")
LOG_LEVEL = _get_str("LOG_LEVEL", "INFO")

# Paths
DRIVE_CREDENTIALS = _get_path("DRIVE_CREDENTIALS")
ROOT_DIR = _get_path("ROOT_PATH")
STORAGE_ROOT = _get_path("STORAGE_PATH")
STAGING_ZONE = _get_path("STAGING_PATH")
MISSING_FOLDERS = _get_path("MISSING_FOLDERS_PATH")
MISSING_FILES = _get_path("MISSING_FILES_PATH")
SIHOS_REPORT_PATH = _get_path("SIHOS_REPORT_PATH")
AUDIT_REPORT_PATH = _get_path("AUDIT_REPORT_PATH")
INVOICE_TARGET_LIST = _get_path("INVOICES_LIST_FILE_PATH")

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


class Settings:
    """Central access to validated settings. Use for CLI and tests."""

    LOG_LEVEL = LOG_LEVEL
    ACTIVE_HOSPITAL = ACTIVE_HOSPITAL
    HOSPITAL = HOSPITAL
    DRIVE_CREDENTIALS = DRIVE_CREDENTIALS
    ROOT_DIR = ROOT_DIR
    STORAGE_ROOT = STORAGE_ROOT
    STAGING_ZONE = STAGING_ZONE
    MISSING_FOLDERS = MISSING_FOLDERS
    MISSING_FILES = MISSING_FILES
    SIHOS_REPORT_PATH = SIHOS_REPORT_PATH
    AUDIT_REPORT_PATH = AUDIT_REPORT_PATH
    INVOICE_TARGET_LIST = INVOICE_TARGET_LIST
    DATA_SCHEMA_COLUMNS = DATA_SCHEMA_COLUMNS

    @classmethod
    def show_summary(cls) -> bool:
        """
        Print config summary and ask user to continue.
        Returns True if user confirms, False otherwise.
        """
        print("\n" + "=" * 60)
        print("AUDITORÍA DE CONFIGURACIÓN")
        print("=" * 60)
        print("\nPARÁMETROS DEL SISTEMA:")
        for key in [
            "LOG_LEVEL", "ACTIVE_HOSPITAL", "ROOT_DIR", "STAGING_ZONE",
            "MISSING_FOLDERS", "MISSING_FILES", "SIHOS_REPORT_PATH",
            "AUDIT_REPORT_PATH", "INVOICE_TARGET_LIST", "DRIVE_CREDENTIALS",
        ]:
            val = getattr(cls, key, None)
            if isinstance(val, dict):
                print(f"   {key}:")
                for k, v in val.items():
                    print(f"      - {k}: {v}")
            else:
                print(f"   {key}: {val}")
        print("=" * 60)
        confirm = input("¿Desea continuar con estos parámetros? (S/N): ").strip().upper()
        if confirm != "S":
            print("Ejecución detenida por el usuario.")
            return False
        print("Arrancando...\n")
        return True
