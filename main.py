from src.folder_service import InvoiceFolderService, FolderConsolidator, FolderScanner
from config.mappings import ADMINISTRADORAS, CONTRATOS
from src.data_manager import DataManager
from file_manager import FileManager
from pdf_processor import PDFProcessor
from src.utils import Util
from config.config import Config
from src.drive_service import GoogleDriveService
from src.file_normalizer import FileNormalizer
from pathlib import Path
import os

# PDFProcessor.run_ocr_cmd(Path(r"C:\Users\sanaf\Dev\pdf-processor\data\staging\HSL355601\CRC_890701078_HSL355601.pdf"))

LOAD_AND_PROCESS = False
RUN_STAGING = False
DOWNLOAD_DRIVE = False
NORMALIZE_FILES = False
CHECK_FOLDERS_WITH_EXTRA_TEXT = False
CHECK_INVOICES = False
CHECK_DIRS = False

# Config.show_summary()
fm = FileManager(Config.STAGING_ZONE)
missing_folders = Util.get_list_from_file("files/missing_invoices.txt")

if LOAD_AND_PROCESS:
    manager = DataManager(ADMINISTRADORAS, CONTRATOS)
    manager.load_excel(Config.SIHOS_REPORT_PATH, Config.DATA_SCHEMA_COLUMNS)
    if manager.run_pre_audit():
        df = manager.process_data()
        manager.export_to_excel(df, Config.AUDIT_REPORT_PATH)
        manager.export_invoice_list(df, Config.INVOICE_TARGET_LIST)
    else:
        print("🛑 Detenido por auditoría.")
        exit()

if RUN_STAGING:
    scanner = FolderScanner()
    folders_to_stage = scanner.get_content_folders(Config.ROOT_DIR)

    if folders_to_stage:
        consolidator = FolderConsolidator(Config.STAGING_ZONE)
        consolidator.copy_folders(folders_to_stage, use_prefix=False)


if DOWNLOAD_DRIVE:
    drive = GoogleDriveService(
        credentials_path=Config.DRIVE_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    drive.sync_missing_folders(missing_folders, Config.MISSING_INVOICES)

if NORMALIZE_FILES:
    # Eliminar archivos que no sean PDF
    non_compliant_files = fm.list_non_compliant_files()
    print("Archivos diferentes eliminados:", fm.delete_files(non_compliant_files))

    # Extraemos todos los prefijos, manejando tanto strings como listas
    prefixes_accepted = Util.flatten_prefixes(Config.HOSPITAL["DOCUMENT_STANDARDS"])

    invalid_files = fm.validate_file_naming_structure(
        valid_prefixes=prefixes_accepted,
        suffix=Config.HOSPITAL["INVOICE_IDENTIFIER_PREFIX"],
        nit=Config.HOSPITAL["NIT"],
    )
    print("Cantidad de archivos con estructura incorrecta:", len(invalid_files))
    print(*invalid_files, sep="\n")

    normalizer = FileNormalizer(
        nit=Config.HOSPITAL["NIT"],
        valid_prefixes=prefixes_accepted,
        suffix_const=Config.HOSPITAL["INVOICE_IDENTIFIER_PREFIX"],
        prefix_map=Config.HOSPITAL["MISNAMED_FIXER_MAP"],
    )
    reporte_final = normalizer.run(invalid_files)

    # Imprimir reporte scaneable
    print(f"{'ESTADO':<10} | {'ORIGINAL':<40} | {'NUEVO NOMBRE'}")
    print("-" * 80)
    for r in reporte_final:
        orig = Path(r.original_path).name
        print(f"{r.status:<10} | {orig[:37]+'...':<40} | {r.new_name}")

skip = Util.get_list_from_file("files/skip_soat_cancellations.txt")
skip_dirs = fm.get_path_of_folders_names(skip)

if CHECK_FOLDERS_WITH_EXTRA_TEXT:
    dirs_with_extra_text = fm.list_dirs_with_extra_text(skip=skip_dirs)
    print("Cantidad de directorios con texto extra:", len(dirs_with_extra_text))
    print(*dirs_with_extra_text, sep="\n")

invoices = fm.list_files_by_prefixes(Config.HOSPITAL["DOCUMENT_STANDARDS"]["FACTURA"])

if CHECK_INVOICES:

    invoices_needing_ocr = fm.list_files_needing_ocr(invoices)
    resultproc = PDFProcessor.process_ocr_batch(
        files=invoices_needing_ocr, max_workers=8
    )

    files_missing_invoice_in_content = fm.list_files_with_missing_invoice_number(
        invoices
    )
    print(
        "Cantidad de facturas sin codigo en el contenido:",
        len(files_missing_invoice_in_content),
    )
    print(*files_missing_invoice_in_content, sep="\n")

    print(f"✅ OCR completado facturas: {resultproc}")

    files_missing_cufe = fm.get_invoices_missing_cufe(invoices)
    print("Cantidad de facturas sin CUFE:", len(files_missing_cufe))
    print(*files_missing_cufe, sep="\n")

    missing_invoices_in_dirs = fm.verify_file_in_dirs(
        Config.HOSPITAL["DOCUMENT_STANDARDS"]["FACTURA"], skip=skip_dirs
    )
    print("Cantidad de directorios sin facturas:", len(missing_invoices_in_dirs))
    print(*missing_invoices_in_dirs, sep="\n")

if CHECK_DIRS:
    all_folders = Util.get_list_from_file(Config.INVOICE_TARGET_LIST)
    missing_dirs = fm.get_folders_missing_on_disk(folders=all_folders)
    print(*missing_dirs, sep="\n")
    print("Cantidad de directorios faltantes:", len(missing_dirs))

# result = fm.copy_or_move_folders(
#     folder_names=missing_folders,
#     source_path=Config.MISSING_INVOICES,
#     destination_path=Config.STAGING_ZONE,
#     action="copy"
# )

# print(result)

# all_dirs = fm.list_dirs()

histories = fm.list_files_by_prefixes(Config.HOSPITAL["DOCUMENT_STANDARDS"]["HISTORIA"])
signatures = fm.list_files_by_prefixes(Config.HOSPITAL["DOCUMENT_STANDARDS"]["FIRMA"])
validations = fm.list_files_by_prefixes(
    Config.HOSPITAL["DOCUMENT_STANDARDS"]["VALIDACION"]
)
results = fm.list_files_by_prefixes(Config.HOSPITAL["DOCUMENT_STANDARDS"]["RESULTADOS"])
auths = fm.list_files_by_prefixes(Config.HOSPITAL["DOCUMENT_STANDARDS"]["AUTORIZACION"])

# dir_electro = fm.list_paths_containing_text(invoices, txt_to_find="ELECTROCARDIOGRAMA", return_parent=True)
# dirs_lab = fm.list_paths_containing_text(invoices, txt_to_find="LABORATORIO CLINICO", return_parent=True)
# dirs_radiografias = fm.list_paths_containing_text(invoices, txt_to_find="RADIOGRAFIA", return_parent=True)
# dirs_p909000 = fm.list_paths_containing_text(invoices, txt_to_find="P909000", return_parent=True)
# dirs_urgencias = fm.list_paths_containing_text(invoices, txt_to_find="URGENCIA", return_parent=True)

# dir_resultados = list(set(dirs_lab + dirs_radiografias + dir_electro) - set(dirs_p909000))
# dirs_historias = list(set(all_dirs) - set(dirs_p909000) - set(dir_resultados))

# tests = Util.get_list_from_file("files/lab.txt")
# dirs_tests = fm.get_path_of_folders_names(tests)

# missing_histories_in_dirs = fm.verify_file_in_dirs(Config.HOSPITAL["DOCUMENT_STANDARDS"]["HISTORIA"], skip=skip_dirs + dirs_tests, target_dirs=dirs_historias)
# print("Cantidad de directorios sin historias:", len(missing_histories_in_dirs))
# print(*missing_histories_in_dirs, sep="\n")

# missing_results_in_dirs = fm.verify_file_in_dirs(Config.HOSPITAL["DOCUMENT_STANDARDS"]["RESULTADOS"], skip=skip_dirs + dirs_urgencias, target_dirs=dir_resultados)
# print("Cantidad de directorios sin resultados:", len(missing_results_in_dirs))
# print(*missing_results_in_dirs, sep="\n")

# missing_signatures_in_dirs = fm.verify_file_in_dirs(Config.HOSPITAL["DOCUMENT_STANDARDS"]["FIRMA"], skip=skip_dirs)
# print("Cantidad de directorios sin firmas:", len(missing_signatures_in_dirs))
# print(*missing_signatures_in_dirs, sep="\n")

# missing_validations_in_dirs = fm.verify_file_in_dirs(Config.HOSPITAL["DOCUMENT_STANDARDS"]["VALIDACION"], skip=skip_dirs + dirs_urgencias)
# print("Cantidad de directorios sin validaciones:", len(missing_validations_in_dirs))
# print(*missing_validations_in_dirs, sep="\n")

# missing_auth_in_dirs = fm.verify_file_in_dirs(Config.HOSPITAL["DOCUMENT_STANDARDS"]["AUTORIZACION"], skip=skip_dirs, target_dirs=dirs_urgencias)
# print("Cantidad de directorios sin autorizaciones:", len(missing_auth_in_dirs))
# print(*missing_auth_in_dirs, sep="\n")

# validations_needing_ocr = fm.list_files_needing_ocr(validations)
# resultproc = PDFProcessor.process_ocr_batch(files=validations_needing_ocr, max_workers=10)
# print(f"✅ OCR completado validaciones: {resultproc}")
# print(*validations_needing_ocr, sep="\n")

# auths_needing_ocr = fm.list_files_needing_ocr(auths)
# resultproc = PDFProcessor.process_ocr_batch(files=auths_needing_ocr, max_workers=10)
# print(f"✅ OCR completado autorizaciones: {resultproc}")

# results_needing_ocr = fm.list_files_needing_ocr(results)
# resultproc = PDFProcessor.process_ocr_batch(files=results_needing_ocr, max_workers=10)
# print(f"✅ OCR completado resultados: {resultproc}")

# signatures_needing_ocr = fm.list_files_needing_ocr(signatures)
# resultproc = PDFProcessor.process_ocr_batch(files=signatures_needing_ocr, max_workers=10)
# print(f"✅ OCR completado firmas: {resultproc}")

# files_with_auth_in = fm.list_paths_containing_text(files=results + validations, txt_to_find="AUTORIZACION", return_parent=False)
# print("Cantidad de directorios que deberian contener PDE:", len(files_with_auth_in))
# print(*files_with_auth_in, sep="\n")

# # print(fm.rename_files_by_prefix_map(prefix_replacements={"PDX": "PDE",}, target_files=files_with_auth_in))

# files_with_adres_in = fm.list_paths_containing_text(files=results, txt_to_find="ADRES", return_parent=False)

# print("Cantidad de directorios que deberian contener OPF:", len(files_with_adres_in))
# print(*files_with_adres_in, sep="\n")

# files_with_sign_in = fm.list_paths_containing_text(files=signatures, txt_to_find="COMPROBANTE", return_parent=False)
# print("Comprobando que CRC si es una firma:", len(files_with_sign_in))
# print(*files_with_sign_in, sep="\n")

# print(fm.rename_files_by_prefix_map(prefix_replacements={"PDX": "OPF",}, target_files=files_with_adres_in))

# files = fm.get_files_by_extension("pdf")
