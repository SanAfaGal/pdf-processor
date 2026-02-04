"""
GUÍA RÁPIDA DE USO - PDF Processor v2.0
======================================

Esta guía muestra ejemplos prácticos de cómo usar los módulos refactorizados.
"""

# ============================================================================
# 1. CONFIGURACIÓN INICIAL
# ============================================================================

# Opción A: Automática (desde .env)
from src.config import Settings

settings = Settings()  # Lee .env automáticamente
settings.create_directories()  # Crea carpetas necesarias

print(f"Source: {settings.source_path}")
print(f"Staging: {settings.staging_path}")
print(f"Final: {settings.final_path}")


# Opción B: Manual (para testing)
from src.config import Settings
from pathlib import Path

settings = Settings(
    source_path=Path("./test_data/source"),
    staging_path=Path("./test_data/staging"),
    final_path=Path("./test_data/final"),
    dry_run=True,  # Modo preview
)


# ============================================================================
# 2. CARGA DE DATOS (EXCEL)
# ============================================================================

from src.core import DataManager
from src.config.settings_data import ADMINISTRADORAS, CONTRATOS

# Crear DataManager
data_manager = DataManager(
    report_path=settings.report_path,
    administradoras=ADMINISTRADORAS,
    contracts=CONTRATOS,
)

# Cargar y normalizar Excel
invoice_df = data_manager.load_excel()
# Retorna: DataFrame con columnas:
# Index: 'Factura' (HSL123456)
# Columns: Doc, No Doc, Administradora, Contrato, folder_path

# Obtener mapeo de invoices esperados
invoice_mapping = data_manager.get_expected_files()
# Retorna: Dict[str, Path]
# Ej: {"HSL123456": Path("Compensar/Contributivo/HSL123456")}

# Consultar metadatos de una invoice específica
metadata = data_manager.get_invoice_metadata("HSL123456")
# Retorna: Dict con todos los metadatos de esa invoice


# ============================================================================
# 3. OPERACIONES DE ARCHIVOS
# ============================================================================

from src.services import FileService

file_service = FileService(base_path=settings.staging_path)

# Listar archivos
all_files = file_service.list_files(
    directory=settings.staging_path,
    extension="*",
    recursive=True
)

pdfs = file_service.get_pdfs(settings.staging_path)

# Validar PDFs
for pdf_path in pdfs:
    if file_service.is_valid_pdf(pdf_path):
        print(f"✓ PDF válido: {pdf_path.name}")
        
        if file_service.has_readable_text(pdf_path):
            print(f"  - Tiene texto OCR")
        else:
            print(f"  - Necesita OCR")

# Extraer NIT de filename
nit = file_service.extract_nit_from_filename("Document_890701078_Invoice.pdf")
# Retorna: "890701078"

# Validar formato de filename
if file_service.validate_filename_format("MyDocument_123456789_Final.pdf"):
    print("✓ Nombre válido")
else:
    print("✗ Nombre inválido")

# Renombrar archivo (con collision detection)
new_path = file_service.rename_file(
    old_path=Path("./staging/old_name.pdf"),
    new_name="new_name.pdf",
    overwrite=False
)

# Copiar archivo
file_service.copy_file(
    source=Path("./staging/source.pdf"),
    destination=Path("./final/destination.pdf")
)

# Mover archivo
file_service.move_file(
    source=Path("./staging/file.pdf"),
    destination=Path("./final/file.pdf")
)

# Eliminar archivos no-PDF
cleanup_results = file_service.delete_non_pdfs(
    directory=settings.staging_path,
    dry_run=True  # Preview
)
print(f"Se eliminarían: {cleanup_results['deleted']} archivos")

# Aplicar correcciones de NIT
nit_corrections = {
    "123456789": "890701078",  # old_nit → new_nit
    "987654321": "890701079",
}
correction_results = file_service.apply_nit_corrections(
    directory=settings.staging_path,
    corrections=nit_corrections,
    dry_run=True
)

# Aplicar reemplazos de prefijo
prefix_replacements = {
    "OLD_PREFIX_": "NEW_PREFIX_",
    "WRONG_CODE_": "RIGHT_CODE_",
}
prefix_results = file_service.apply_prefix_replacements(
    directory=settings.staging_path,
    replacements=prefix_replacements,
    dry_run=False  # Ejecutar
)


# ============================================================================
# 4. PROCESAMIENTO DE PDFs (OCR + COMPRESIÓN)
# ============================================================================

from src.core import PDFProcessor

pdf_processor = PDFProcessor(
    max_workers=settings.max_workers,
    ocr_timeout=settings.ocr_timeout,
)

# Obtener PDFs que necesitan OCR
pdfs_needing_ocr = [
    p for p in pdfs
    if not file_service.has_readable_text(p)
]

# Aplicar OCR a batch
if pdfs_needing_ocr:
    def ocr_callback(file_path: Path, success: bool):
        if success:
            print(f"✓ OCR: {file_path.name}")
        else:
            print(f"✗ OCR failed: {file_path.name}")

    ocr_results = pdf_processor.process_ocr_batch(
        files=pdfs_needing_ocr,
        callback=ocr_callback
    )
    print(f"OCR: {ocr_results['success']} success, {ocr_results['failed']} failed")

# Comprimir PDFs
compression_results = pdf_processor.process_compression_batch(
    files=pdfs,
    quality=settings.compress_quality,  # 85 por defecto
    callback=lambda f, s: print(f"Compressed: {f.name}" if s else f"Compression failed: {f.name}")
)


# ============================================================================
# 5. ORQUESTACIÓN DE CARPETAS
# ============================================================================

from src.services import InvoiceFolderService

folder_service = InvoiceFolderService(
    source_path=settings.source_path,
    staging_path=settings.staging_path,
    final_path=settings.final_path,
)

# Phase 1: Mover archivos a staging
staging_results = folder_service.stage_files(dry_run=True)
print(f"Staging: {staging_results['moved']} moved")

# Phase 2: Organizar por jerarquía
org_results = folder_service.organize_by_hierarchy(
    invoice_mapping=invoice_mapping,  # Del DataManager
    dry_run=True
)
print(f"Organized: {org_results['organized']} files")

# Phase 3: Mover a destino final
final_results = folder_service.finalize_files(dry_run=False)
print(f"Finalized: {final_results['finalized']} files")

# Phase 4: Validar estructura final
validation_results = folder_service.validate_final_structure(
    expected_invoices=list(invoice_mapping.keys())
)
print(f"Found: {validation_results['found']}, Missing: {validation_results['missing']}")

# Phase 5: Limpiar staging
cleanup_results = folder_service.cleanup_staging(dry_run=False)
print(f"Cleanup: {cleanup_results['deleted']} files deleted")


# ============================================================================
# 6. LOGGING (ESTRUCTURA JSON)
# ============================================================================

from src.config.logger import setup_logger

# Obtener logger
logger = setup_logger(
    name=__name__,
    log_file=settings.log_file,
    level=settings.log_level,
    format_type=settings.log_format,
)

# Usar logger
logger.info("Iniciando procesamiento")
logger.warning("Verificar configuración")
logger.error("Error durante procesamiento")
logger.debug("Debug: variables internas")

# Salida JSON structured:
# {
#   "timestamp": "2026-02-04 12:34:56,789",
#   "level": "INFO",
#   "module": "__main__",
#   "message": "Iniciando procesamiento",
#   "exception": null
# }


# ============================================================================
# 7. MANEJO DE ERRORES
# ============================================================================

from src.config.exceptions import (
    PDFProcessorError,
    DataValidationError,
    PDFProcessingError,
    FileOperationError,
    InvoiceProcessingError,
)

try:
    invoice_df = data_manager.load_excel()
except DataValidationError as e:
    logger.error(f"Error en datos: {str(e)}")
except PDFProcessorError as e:
    logger.error(f"Error en procesamiento: {str(e)}")
except Exception as e:
    logger.error(f"Error inesperado: {str(e)}", exc_info=True)


# ============================================================================
# 8. PIPELINE COMPLETO (COMO EN main.py)
# ============================================================================

def full_pipeline_example():
    """Ejemplo de pipeline completo."""
    
    # Cargar configuración
    settings = Settings()
    settings.create_directories()
    logger = setup_logger(__name__, log_file=settings.log_file)
    
    try:
        logger.info("=== Iniciando Pipeline ===")
        
        # 1. Cargar datos
        data_manager = DataManager(
            report_path=settings.report_path,
            administradoras=ADMINISTRADORAS,
            contracts=CONTRATOS,
        )
        invoice_df = data_manager.load_excel()
        invoice_mapping = data_manager.get_expected_files()
        logger.info(f"Loaded {len(invoice_mapping)} invoices")
        
        # 2. Crear servicios
        folder_service = InvoiceFolderService(
            source_path=settings.source_path,
            staging_path=settings.staging_path,
            final_path=settings.final_path,
        )
        file_service = FileService(base_path=settings.staging_path)
        pdf_processor = PDFProcessor()
        
        # 3. Staging
        folder_service.stage_files(dry_run=settings.dry_run)
        
        # 4. Limpieza
        file_service.delete_non_pdfs(settings.staging_path, dry_run=settings.dry_run)
        
        # 5. OCR
        pdfs = file_service.get_pdfs(settings.staging_path)
        pdfs_needing_ocr = [p for p in pdfs if not file_service.has_readable_text(p)]
        if pdfs_needing_ocr:
            pdf_processor.process_ocr_batch(pdfs_needing_ocr)
        
        # 6. Compresión
        pdf_processor.process_compression_batch(pdfs)
        
        # 7. Organización
        folder_service.organize_by_hierarchy(invoice_mapping, dry_run=settings.dry_run)
        
        # 8. Finalización
        folder_service.finalize_files(dry_run=settings.dry_run)
        
        # 9. Validación
        validation = folder_service.validate_final_structure(
            list(invoice_mapping.keys())
        )
        
        logger.info(f"=== Pipeline Completado ===")
        logger.info(f"Success: {validation['found']}/{len(invoice_mapping)} invoices")
        return 0
        
    except PDFProcessorError as e:
        logger.error(f"Error fatal: {str(e)}")
        return 1
    except KeyboardInterrupt:
        logger.info("Cancelado por usuario")
        return 130


# ============================================================================
# 9. CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ============================================================================

"""
Variables de entorno (.env):

# File Paths
SOURCE_PATH=./data/source
STAGING_PATH=./data/staging
FINAL_PATH=./data/final
REPORT_PATH=./data/reports/Informe_Sihos.xlsx

# Document Configuration
DOCUMENT_SUFFIX=HSL
NIT_DEFAULT=890701078

# Processing
MAX_WORKERS=4
OCR_TIMEOUT=300
COMPRESS_QUALITY=85
DRY_RUN=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=./logs/pdf-processor.log

# External Tools
GHOSTSCRIPT_PATH=
OCRMYPDF_PATH=
"""


# ============================================================================
# 10. EJEMPLOS DE USO EN TESTING
# ============================================================================

import pytest
from pathlib import Path

def test_data_manager_load_excel():
    """Test example: Load Excel data."""
    data_manager = DataManager(
        report_path=Path("./test_fixtures/sample_invoice.xlsx"),
        administradoras=ADMINISTRADORAS,
        contracts=CONTRATOS,
    )
    df = data_manager.load_excel()
    assert len(df) > 0
    assert "Factura" in df.index.name


def test_file_service_nit_extraction():
    """Test example: Extract NIT from filename."""
    file_service = FileService()
    nit = file_service.extract_nit_from_filename("Document_890701078_Final.pdf")
    assert nit == "890701078"


def test_file_service_validate_filename():
    """Test example: Validate filename format."""
    file_service = FileService()
    assert file_service.validate_filename_format("Valid_Name_123.pdf") == True
    assert file_service.validate_filename_format("") == False
    assert file_service.validate_filename_format("file.xyz") == False


def test_pdf_processor_ocr_single():
    """Test example: OCR single PDF."""
    pdf_processor = PDFProcessor()
    # Asumir que existe test.pdf sin texto
    result = pdf_processor.run_ocr(Path("./test_fixtures/test_no_text.pdf"))
    # Verificar que el resultado es booleano
    assert isinstance(result, bool)


# ============================================================================
# CONCLUSIÓN
# ============================================================================

"""
Con estos ejemplos puedes:

1. Cargar configuración de .env
2. Procesar datos de Excel
3. Operar sobre archivos
4. Procesar PDFs (OCR, compresión)
5. Orquestar movimiento de carpetas
6. Usar logging estructurado
7. Manejar errores robustamente
8. Crear un pipeline completo
9. Configurar variables de entorno
10. Escribir tests

Para ejemplos más completos, revisar:
- main.py (pipeline production)
- README.md (documentación completa)
- docs/ARCHITECTURE.md (guía detallada)
"""
