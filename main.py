from itertools import count
from config import (
    NIT_DEFAULT,
    STAGING_PATH,
    REPORT_PATH,
    COLUMNS_TO_USE,
    FINAL_PATH,
    FILE_PREFIXES,
    SUFFIX,
    PREFIX_REPLACEMENTS,
)
from invoce_folder_service import InvoiceFolderService
from settings import ADMINISTRADORAS, CONTRATOS
from excel_processor import DataManager
from file_manager import FileManager
from pdf_processor import PDFProcessor
from utils import Util


def main():
    xl_manager = DataManager(ADMINISTRADORAS, CONTRATOS)
    xl_manager.load_excel(REPORT_PATH, COLUMNS_TO_USE)
    xl_manager.prepare_data(export_report=False)

    # file_manager = FileManager(STAGING_PATH)
    # non_compliant_files = file_manager.list_non_compliant_files()
    # print("Archivos diferentes eliminiados:", file_manager.delete_files(non_compliant_files))

    # Extraemos todos los prefijos, manejando tanto strings como listas
    # invalid_files = file_manager.validate_file_naming_structure(
    #     valid_prefixes=Util.extract_valid_prefixes(FILE_PREFIXES),
    #     suffix=SUFFIX,
    #     nit=NIT_DEFAULT,
    # )
    # print("Cantidad de archivos con estructura incorrecta:", len(invalid_files))
    # print(*invalid_files, sep="\n")

    # all_dirs = file_manager.list_dirs()

    # print(file_manager.rename_files_by_prefix_map(prefix_replacements=PREFIX_REPLACEMENTS))

    # invoices = file_manager.list_files_by_prefixes(FILE_PREFIXES["FACTURA"])
    # histories = file_manager.list_files_by_prefixes(FILE_PREFIXES["HISTORIA"])
    # signatures = file_manager.list_files_by_prefixes(FILE_PREFIXES["FIRMA"])
    # validations = file_manager.list_files_by_prefixes(FILE_PREFIXES["VALIDACION"])
    # results = file_manager.list_files_by_prefixes(FILE_PREFIXES["RESULTADOS"])
    # auths = file_manager.list_files_by_prefixes(FILE_PREFIXES["AUTORIZACION"])

    # dir_electro = file_manager.list_paths_containing_text(invoices, txt_to_find="ELECTROCARDIOGRAMA", return_parent=True)
    # dirs_lab = file_manager.list_paths_containing_text(invoices, txt_to_find="LABORATORIO CLINICO", return_parent=True)
    # dirs_radiografias = file_manager.list_paths_containing_text(invoices, txt_to_find="RADIOGRAFIA", return_parent=True)
    # dirs_p909000 = file_manager.list_paths_containing_text(invoices, txt_to_find="P909000", return_parent=True)
    # dirs_urgencias = file_manager.list_paths_containing_text(invoices, txt_to_find="URGENCIA", return_parent=True)

    # dir_resultados = list(set(dirs_lab + dirs_radiografias + dir_electro) - set(dirs_p909000))
    # dirs_historias = list(set(all_dirs) - set(dirs_p909000) - set(dir_resultados))
    # dirs_soat = Util.get_list_from_file("SOAT.txt")
    # print("soats", dirs_soat)

    # files_missing_invoice_in_content = file_manager.list_files_with_missing_invoice_number(invoices)
    # print("Cantidad de facturas sin codigo en el contenido:", len(files_missing_invoice_in_content))
    # print(*files_missing_invoice_in_content, sep="\n")

    # dirs_with_anular = file_manager.list_dirs_with_anular()
    # print("Cantidad de directorios con 'ANULAR':", len(dirs_with_anular))
    # print(*dirs_with_anular, sep="\n")

    # skip_dirs = dirs_with_anular + dirs_soat

    # missing_invoices_in_dirs = file_manager.verify_file_in_dirs(FILE_PREFIXES["FACTURA"], skip=skip_dirs)
    # print("Cantidad de directorios sin facturas:", len(missing_invoices_in_dirs))
    # print(*missing_invoices_in_dirs, sep="\n")

    # missing_histories_in_dirs = file_manager.verify_file_in_dirs(FILE_PREFIXES["HISTORIA"], skip=skip_dirs, target_dirs=dirs_historias)
    # print("Cantidad de directorios sin historias:", len(missing_histories_in_dirs))
    # print(*missing_histories_in_dirs, sep="\n")

    # missing_results_in_dirs = file_manager.verify_file_in_dirs(FILE_PREFIXES["RESULTADOS"], skip=skip_dirs + dirs_urgencias, target_dirs=dir_resultados)
    # print("Cantidad de directorios sin resultados:", len(missing_results_in_dirs))
    # print(*missing_results_in_dirs, sep="\n")

    # missing_signatures_in_dirs = file_manager.verify_file_in_dirs(FILE_PREFIXES["FIRMA"], skip=skip_dirs)
    # print("Cantidad de directorios sin firmas:", len(missing_signatures_in_dirs))
    # print(*missing_signatures_in_dirs, sep="\n")

    # missing_validations_in_dirs = file_manager.verify_file_in_dirs(FILE_PREFIXES["VALIDACION"], skip=skip_dirs + dirs_urgencias)
    # print("Cantidad de directorios sin validaciones:", len(missing_validations_in_dirs))
    # print(*missing_validations_in_dirs, sep="\n")

    # missing_auth_in_dirs = file_manager.verify_file_in_dirs(FILE_PREFIXES["AUTORIZACION"], skip=skip_dirs, target_dirs=dirs_urgencias)
    # print("Cantidad de directorios sin autorizaciones:", len(missing_auth_in_dirs))
    # print(*missing_auth_in_dirs, sep="\n")

    # files_missing_cufe = file_manager.get_invoices_missing_cufe(invoices)
    # print("Cantidad de facturas sin CUFE:", len(files_missing_cufe))
    # print(*files_missing_cufe, sep="\n")

    # dirs_with_extra_text = file_manager.list_dirs_with_extra_text()
    # print("Cantidad de directorios con texto extra:", len(dirs_with_extra_text))
    # print(*dirs_with_extra_text, sep="\n")

    # print(file_manager.rename_files_by_correct_nit(
    #     files=invalid_files,
    #     correct_nit=NIT_DEFAULT
    # ))

    # invoices_needing_ocr = file_manager.list_files_needing_ocr(invoices)
    # resultproc = PDFProcessor.process_ocr_batch(files=invoices_needing_ocr, max_workers=8)
    # print(f"✅ OCR completado facturas: {resultproc}")

    # validations_needing_ocr = file_manager.list_files_needing_ocr(validations)
    # resultproc = PDFProcessor.process_ocr_batch(files=validations_needing_ocr, max_workers=8)
    # print(f"✅ OCR completado validaciones: {resultproc}")

    # auths_needing_ocr = file_manager.list_files_needing_ocr(auths)
    # resultproc = PDFProcessor.process_ocr_batch(files=auths_needing_ocr, max_workers=8)
    # print(f"✅ OCR completado autorizaciones: {resultproc}")

    # results_needing_ocr = file_manager.list_files_needing_ocr(results)
    # resultproc = PDFProcessor.process_ocr_batch(files=results_needing_ocr, max_workers=8)
    # print(f"✅ OCR completado resultados: {resultproc}")

    # signatures_needing_ocr = file_manager.list_files_needing_ocr(signatures)
    # resultproc = PDFProcessor.process_ocr_batch(files=signatures_needing_ocr, max_workers=8)
    # print(f"✅ OCR completado firmas: {resultproc}")

    # files_with_auth_in = file_manager.list_paths_containing_text(files=results + validations, txt_to_find="AUTORIZACION", return_parent=False)
    # print("Cantidad de directorios que deberian contener PDE:", len(files_with_auth_in))
    # print(*files_with_auth_in, sep="\n")

    # # print(file_manager.rename_files_by_prefix_map(prefix_replacements={"PDX": "PDE",}, target_files=files_with_auth_in))

    # files_with_adres_in = file_manager.list_paths_containing_text(files=results, txt_to_find="ADRES", return_parent=False)

    # print("Cantidad de directorios que deberian contener OPF:", len(files_with_adres_in))
    # print(*files_with_adres_in, sep="\n")

    # files_with_sign_in = file_manager.list_paths_containing_text(files=signatures, txt_to_find="COMPROBANTE", return_parent=False)
    # print("Comprobando que CRC si es una firma:", len(files_with_sign_in))
    # print(*files_with_sign_in, sep="\n")

    # print(file_manager.rename_files_by_prefix_map(prefix_replacements={"PDX": "OPF",}, target_files=files_with_adres_in))

    # files = file_manager.get_files_by_extension("pdf")

    invoice_service = InvoiceFolderService(
        df=xl_manager.get_dataframe(), 
        staging_base=STAGING_PATH, 
        final_base=FINAL_PATH
    )

    invoice_service.organize_to_destination(dry_run=False)


if __name__ == "__main__":
    main()
