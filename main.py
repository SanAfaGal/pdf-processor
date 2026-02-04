from itertools import count
from config import (
    NIT_DEFAULT,
    SOURCE_PATH,
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


def main():
    xl_manager = DataManager(ADMINISTRADORAS, CONTRATOS)
    xl_manager.load_excel(REPORT_PATH, COLUMNS_TO_USE)
    xl_manager.prepare_data()

    invoice_service = InvoiceFolderService(
        df=xl_manager.get_dataframe(),
        source_base=SOURCE_PATH,
        staging_base=STAGING_PATH,
        final_base=FINAL_PATH,
    )

    # invoice_service.collect_to_staging()
    # invoice_service.delete_empty_source_dirs()
    # invoice_service.list_dirs_with_extra_text()
    # invoice_service.export_missing_invoices()

    file_manager = FileManager(STAGING_PATH)
    # non_compliant_files = file_manager.list_non_compliant_files()
    # file_manager.delete_files(non_compliant_files)

    # Extraemos todos los prefijos, manejando tanto strings como listas
    valid_prefixes_list = []
    for val in FILE_PREFIXES.values():
        if isinstance(val, list):
            valid_prefixes_list.extend(val)
        else:
            valid_prefixes_list.append(val)

    # Convertimos a mayúsculas para asegurar coincidencia
    valid_prefixes_list = [p.upper() for p in valid_prefixes_list]

    invalid_files = file_manager.validate_file_naming_structure(
        files=file_manager.get_files_by_extension("pdf"),
        valid_prefixes=valid_prefixes_list,
        suffix=SUFFIX,
        nit=NIT_DEFAULT,
    )
    for f in invalid_files:
        print(f"❌ Nombre inválido: {f}")


    # print(file_manager.rename_files_by_correct_nit(
    #     files=invalid_files,
    #     correct_nit=NIT_DEFAULT
    # ))

    # print(file_manager.rename_files_by_prefix_map(prefix_replacements=PREFIX_REPLACEMENTS))

    # files = file_manager.list_files_by_prefixes(FILE_PREFIXES["HISTORIA"])
    # for f in files:
    #     print(f"📄 Archivo de historia clínica: {f}")

    # files_needing_ocr = file_manager.list_files_needing_ocr(files)
    # for f in files_needing_ocr:
    #     print(f"📝 Necesita OCR: {f}")

    missing_dirs = file_manager.verify_file_in_dirs(FILE_PREFIXES["HISTORIA"])
    for d in missing_dirs:
        print(f"❌ Directorio sin archivo con prefijo: {d}")

    # resultproc = PDFProcessor.process_ocr_batch(files_needing_ocr, max_workers=8)
    # print(f"✅ OCR completado: {resultproc}")

    # files_missing_invoice = file_manager.list_files_with_missing_invoice_number(files)

    # for f in files_missing_invoice:
    #     print(f"❌ Archivo sin número de factura: {f}")

    # todos_los_pdfs = file_manager.get_files_by_extension("pdf")
    # files_renamed = proc.rename_by_nit(todos_los_pdfs, NIT_DEFAULT, file_manager.extract_nit_from_name)
    # print(f"✅ Renombrados {files_renamed} archivos.")

    # invoice_service.organize_to_destination(dry_run=True)


if __name__ == "__main__":
    main()
