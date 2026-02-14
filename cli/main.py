"""
Interactive CLI for PDF processor: run actions from a menu in a loop.
Run from project root: python -m cli.main
"""
import logging
import sys
from pathlib import Path

# Ensure project root is on path when running as python -m cli.main
if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from config.settings import Settings
from config.mappings import ADMINISTRADORAS, CONTRATOS
from core.data_manager import DataManager
from core.file_normalizer import FileNormalizer
from services.file_manager import FileManager
from services.folder_service import FolderConsolidator, FolderScanner, InvoiceFolderService
from services.pdf_processor import PDFProcessor
from services.drive_service import GoogleDriveService
from utils.persistence import get_list_from_file, flatten_prefixes


def _say(msg: str) -> None:
    """Print a single progress line (visually distinct from raw data)."""
    print(f"  > {msg}")


def _action_start(title: str) -> None:
    """Print when an action begins."""
    print()
    print(f"--- Acción: {title} ---")


def _action_done(summary: str) -> None:
    """Print when an action finishes."""
    print(f"  Listo. {summary}")


def _staging_zone() -> Path:
    return Settings.STAGING_ZONE


def _hospital() -> dict:
    return Settings.HOSPITAL


def action_show_config() -> None:
    """Print config summary and optionally confirm."""
    _action_start("Mostrar configuración")
    _say("Mostrando parámetros del sistema...")
    Settings.show_summary()
    _action_done("Configuración mostrada.")


def action_load_and_process() -> None:
    """Load Excel, run pre-audit, process data; optionally organize folders."""
    _action_start("Cargar Excel y procesar (auditoría + organizar opcional)")
    manager = DataManager(ADMINISTRADORAS, CONTRATOS)
    _say(f"Leyendo Excel: {Settings.SIHOS_REPORT_PATH}...")
    try:
        manager.load_excel(Settings.SIHOS_REPORT_PATH, Settings.DATA_SCHEMA_COLUMNS)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        _action_done("Falló: archivo no encontrado.")
        return
    _say("Ejecutando auditoría previa de mapeos...")
    if not manager.run_pre_audit():
        print("Detenido por auditoría.")
        _action_done("Detenido por auditoría (valores sin mapear).")
        return
    _say("Procesando datos (limpieza, rutas)...")
    df = manager.process_data()
    _say(f"Datos procesados: {len(df)} filas.")
    export = input("  Exportar Excel y lista de facturas? (s/n): ").strip().lower()
    if export == "s":
        _say("Exportando Excel y lista de facturas...")
        manager.export_to_excel(df, Settings.AUDIT_REPORT_PATH)
        manager.export_invoice_list(df, Settings.INVOICE_TARGET_LIST)
    organize = input("  Organizar carpetas (dry-run)? (s/n): ").strip().lower()
    if organize == "s":
        _say("Organizando carpetas (simulación)...")
        fs = InvoiceFolderService(df, _staging_zone(), _staging_zone())
        result = fs.organize(dry_run=True)
        print(f"  Resultado: {result}")
    _action_done(f"Procesamiento completado ({len(df)} facturas).")


def action_move_missing_files() -> None:
    """Move files from MISSING_FILES path into staging by folder name."""
    _action_start("Mover archivos faltantes a carpeta correcta")
    _say(f"Carpeta de archivos faltantes: {Settings.MISSING_FILES}")
    _say("Buscando archivos y moviendo a staging...")
    fm = FileManager(_staging_zone())
    n = fm.move_files_to_right_folder(Settings.MISSING_FILES)
    _action_done(f"Archivos movidos: {n}")


def action_run_staging() -> None:
    """Scan ROOT_DIR for content folders and copy to STAGING_ZONE."""
    _action_start("Ejecutar staging (copiar carpetas a zona de staging)")
    _say(f"Escaneando directorio raíz: {Settings.ROOT_DIR}...")
    scanner = FolderScanner()
    folders = scanner.get_content_folders(Settings.ROOT_DIR)
    if not folders:
        _say("No se encontraron carpetas con archivos.")
        _action_done("Nada que consolidar.")
        return
    _say(f"Encontradas {len(folders)} carpetas. Copiando a {_staging_zone()}...")
    consolidator = FolderConsolidator(_staging_zone())
    n = consolidator.copy_folders(folders, use_prefix=False)
    _action_done(f"Carpetas copiadas: {n}")


def action_download_drive() -> None:
    """Sync missing folders or specific files from Google Drive."""
    _action_start("Descargar desde Google Drive")
    _say("Conectando con Google Drive...")
    drive = GoogleDriveService(
        credentials_path=Settings.DRIVE_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    choice = input("  1 = carpetas faltantes, 2 = archivos específicos: ").strip()
    if choice == "1":
        _say("Leyendo lista de carpetas (files/missing_folders.txt)...")
        missing_folders = get_list_from_file(Path("files/missing_folders.txt"))
        if not missing_folders:
            _say("files/missing_folders.txt vacío o no existe.")
            _action_done("Nada que descargar.")
            return
        _say(f"Descargando {len(missing_folders)} carpetas en {Settings.MISSING_FOLDERS}...")
        drive.sync_missing_folders(missing_folders, Settings.MISSING_FOLDERS)
        _action_done(f"Carpetas solicitadas: {len(missing_folders)}.")
    else:
        _say("Leyendo lista de archivos (files/missing_files.txt)...")
        missing_files = get_list_from_file(Path("files/missing_files.txt"))
        if not missing_files:
            _say("files/missing_files.txt vacío o no existe.")
            _action_done("Nada que descargar.")
            return
        _say(f"Buscando y descargando {len(missing_files)} archivos...")
        not_found = drive.sync_specific_files(missing_files, Settings.MISSING_FILES)
        if not_found:
            print("  No encontrados:")
            for x in not_found:
                print(f"    {x}")
        _action_done(f"Descargados: {len(missing_files) - len(not_found)}; no encontrados: {len(not_found)}.")


def action_normalize_files() -> None:
    """Delete non-PDF, validate naming, run normalizer on invalid names."""
    _action_start("Normalizar nombres de archivos")
    fm = FileManager(_staging_zone())
    hospital = _hospital()
    _say("Listando archivos que no son PDF...")
    non_compliant = fm.list_non_compliant_files()
    deleted = fm.delete_files(non_compliant)
    _say(f"Archivos no-PDF eliminados: {deleted}")
    _say("Validando estructura de nombres (PREFIJO_NIT_SUFFIX...)...")
    prefixes = flatten_prefixes(hospital["DOCUMENT_STANDARDS"])
    invalid = fm.validate_file_naming_structure(
        valid_prefixes=prefixes,
        suffix=hospital["INVOICE_IDENTIFIER_PREFIX"],
        nit=hospital["NIT"],
    )
    _say(f"Archivos con estructura incorrecta: {len(invalid)}")
    for p in invalid:
        print(p)
    _say("Aplicando normalizador (renombrar según reglas)...")
    normalizer = FileNormalizer(
        nit=hospital["NIT"],
        valid_prefixes=prefixes,
        suffix_const=hospital["INVOICE_IDENTIFIER_PREFIX"],
        prefix_map=hospital["MISNAMED_FIXER_MAP"],
    )
    reports = normalizer.run(invalid)
    print(f"  {'ESTADO':<10} | {'ORIGINAL':<40} | {'NUEVO NOMBRE'}")
    print("  " + "-" * 76)
    for r in reports:
        orig = Path(r.original_path).name
        short = (orig[:37] + "...") if len(orig) > 40 else orig
        print(f"  {r.status:<10} | {short:<40} | {r.new_name}")
    success = sum(1 for r in reports if r.status == "SUCCESS")
    _action_done(f"Eliminados no-PDF: {deleted}; renombrados: {success}; rechazados/errores: {len(reports) - success}.")


def action_check_invoice_number() -> None:
    """List files whose HSL suffix does not match folder name."""
    _action_start("Verificar número factura vs carpeta")
    _say("Cargando carpetas a omitir (skip_soat_cancellations.txt)...")
    fm = FileManager(_staging_zone())
    skip = get_list_from_file(Path("files/skip_soat_cancellations.txt"))
    skip_dirs = fm.get_path_of_folders_names(skip)
    _say("Comprobando que el sufijo HSL del archivo coincida con el nombre de la carpeta...")
    mismatched = fm.list_files_with_mismatched_folder_names(skip_folders=skip_dirs)
    if mismatched:
        print("  Mostrando archivos con nombre no coincidente:")
        for p in mismatched:
            print(f"    {p}")
    _action_done(f"Total con nombre no coincidente: {len(mismatched)}")


def action_check_folders_extra_text() -> None:
    """List directories that do not match HSL + 6 digits."""
    _action_start("Verificar carpetas con texto extra")
    _say("Cargando carpetas a omitir...")
    fm = FileManager(_staging_zone())
    skip = get_list_from_file(Path("files/skip_soat_cancellations.txt"))
    skip_dirs = fm.get_path_of_folders_names(skip)
    _say("Buscando directorios que no siguen el patrón HSL + 6 dígitos...")
    dirs = fm.list_dirs_with_extra_text(skip=skip_dirs)
    if dirs:
        print("  Directorios con texto extra:")
        for d in dirs:
            print(f"    {d}")
    _action_done(f"Directorios con texto extra: {len(dirs)}")


def action_check_invoices() -> None:
    """OCR batch, missing invoice in content, missing CUFE, dirs without invoice."""
    _action_start("Verificar facturas (OCR, contenido, CUFE, dirs)")
    fm = FileManager(_staging_zone())
    hospital = _hospital()
    prefixes = hospital["DOCUMENT_STANDARDS"]["FACTURA"]
    if isinstance(prefixes, list):
        prefixes = prefixes[0] if prefixes else ""
    _say("Listando facturas por prefijo...")
    invoices = fm.list_files_by_prefixes(prefixes)
    _say(f"Encontradas {len(invoices)} facturas.")
    skip = get_list_from_file(Path("files/skip_soat_cancellations.txt"))
    skip_dirs = fm.get_path_of_folders_names(skip)
    _say("Comprobando cuáles necesitan OCR...")
    need_ocr = fm.list_files_needing_ocr(invoices)
    if need_ocr:
        _say(f"Ejecutando OCR en {len(need_ocr)} archivos...")
        result = PDFProcessor.process_ocr_batch(need_ocr, max_workers=8)
        _say(f"OCR: ok={result['ok']}, fail={result['fail']}")
    _say("Comprobando facturas sin código en el contenido...")
    missing_in_content = fm.list_files_with_missing_invoice_number(invoices)
    if missing_in_content:
        print("  Facturas sin código en contenido:")
        for p in missing_in_content:
            print(f"    {p}")
    _say("Comprobando facturas sin CUFE...")
    missing_cufe = fm.get_invoices_missing_cufe(invoices)
    if missing_cufe:
        print("  Facturas sin CUFE:")
        for p in missing_cufe:
            print(f"    {p}")
    _say("Comprobando directorios sin factura...")
    missing_dirs = fm.verify_file_in_dirs(prefixes, skip=skip_dirs)
    if missing_dirs:
        print("  Directorios sin factura:")
        for d in missing_dirs:
            print(f"    {d}")
    _action_done(
        f"Facturas: {len(invoices)}; sin código en contenido: {len(missing_in_content)}; "
        f"sin CUFE: {len(missing_cufe)}; dirs sin factura: {len(missing_dirs)}."
    )


def action_check_dirs() -> None:
    """List folder IDs from INVOICE_TARGET_LIST that are missing on disk."""
    _action_start("Verificar directorios faltantes en disco")
    _say(f"Leyendo lista de directorios: {Settings.INVOICE_TARGET_LIST}...")
    all_folders = get_list_from_file(Settings.INVOICE_TARGET_LIST)
    _say(f"Lista tiene {len(all_folders)} entradas. Comparando con disco...")
    fm = FileManager(_staging_zone())
    missing = fm.get_folders_missing_on_disk(all_folders)
    if missing:
        print("  Directorios faltantes:")
        for m in missing:
            print(f"    {m}")
    _action_done(f"Directorios faltantes: {len(missing)}")


def action_check_invalid_files() -> None:
    """List PDFs that cannot be opened."""
    _action_start("Verificar archivos PDF inválidos")
    _say("Listando todos los PDF en la zona de staging...")
    fm = FileManager(_staging_zone())
    all_files = fm.get_files_by_extension()
    _say(f"Encontrados {len(all_files)} PDF. Comprobando cuáles no se pueden abrir...")
    invalid = fm.check_invalid_files(all_files)
    if invalid:
        print("  Archivos inválidos:")
        for p in invalid:
            print(f"    {p}")
    _action_done(f"Archivos inválidos: {len(invalid)}")


def menu() -> None:
    """Print menu and return choice string (or '0' for exit)."""
    print()
    print("  PDF Processor - Acciones")
    print("  " + "-" * 40)
    print("  1  Mostrar configuración")
    print("  2  Cargar Excel y procesar (auditoría + organizar opcional)")
    print("  3  Mover archivos faltantes a carpeta correcta")
    print("  4  Ejecutar staging (copiar carpetas a zona de staging)")
    print("  5  Descargar desde Google Drive")
    print("  6  Normalizar nombres de archivos")
    print("  7  Verificar número factura vs carpeta")
    print("  8  Verificar carpetas con texto extra")
    print("  9  Verificar facturas (OCR, contenido, CUFE, dirs)")
    print("  10 Verificar directorios faltantes en disco")
    print("  11 Verificar archivos PDF inválidos")
    print("  0  Salir")
    print("  " + "-" * 40)


def main() -> None:
    # Show INFO and above from our packages in the terminal
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    # Reduce noise from third-party libs
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    actions = {
        "1": action_show_config,
        "2": action_load_and_process,
        "3": action_move_missing_files,
        "4": action_run_staging,
        "5": action_download_drive,
        "6": action_normalize_files,
        "7": action_check_invoice_number,
        "8": action_check_folders_extra_text,
        "9": action_check_invoices,
        "10": action_check_dirs,
        "11": action_check_invalid_files,
    }
    while True:
        menu()
        choice = input("Elija opción: ").strip()
        if choice == "0":
            print("Hasta luego.")
            break
        if choice in actions:
            try:
                actions[choice]()
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    main()
