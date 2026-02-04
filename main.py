"""
PDF Processor - Main entry point for invoice batch processing.

Orchestrates the complete workflow:
1. Load invoice metadata from Excel report
2. Stage source files to processing directory
3. Validate and organize files
4. Apply OCR to text-less PDFs
5. Compress PDF files
6. Move to final destination with proper hierarchy
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from src.config import setup_logger, Settings
from src.config.settings_data import ADMINISTRADORAS, CONTRATOS
from src.config.exceptions import PDFProcessorError
from src.core import DataManager, PDFProcessor
from src.services import FileService, InvoiceFolderService

# Initialize logging
logger = setup_logger(__name__)


def load_configuration() -> Settings:
    """
    Load and validate application configuration.

    Returns:
        Settings object with validated configuration

    Raises:
        ConfigurationError: If critical configuration is invalid
    """
    try:
        settings = Settings()
        settings.create_directories()
        logger.info(f"Configuration loaded successfully")
        logger.debug(f"Source: {settings.source_path}")
        logger.debug(f"Staging: {settings.staging_path}")
        logger.debug(f"Final: {settings.final_path}")
        return settings
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}")
        raise


def process_invoices(
    dry_run: bool = False,
) -> dict:
    """
    Main invoice processing orchestration.

    Pipeline:
    - Load Excel invoice metadata
    - Move files to staging directory
    - Delete non-PDF files
    - Validate file naming structure
    - Correct NIT identifiers
    - Apply prefix standardization
    - Apply OCR to text-less PDFs
    - Compress PDF files
    - Validate missing invoices
    - Move to final destination

    Args:
        dry_run: If True, only report what would be changed

    Returns:
        Dictionary with processing statistics

    Raises:
        PDFProcessorError: If critical processing steps fail
    """
    settings = load_configuration()
    stats = {
        "total_files": 0,
        "staged": 0,
        "organized": 0,
        "ocr_success": 0,
        "ocr_failed": 0,
        "compression_success": 0,
        "compression_failed": 0,
        "finalized": 0,
        "errors": [],
    }

    try:
        # ========== PHASE 1: LOAD DATA ==========
        logger.info("=" * 60)
        logger.info("PHASE 1: Loading invoice metadata from Excel")
        logger.info("=" * 60)

        data_manager = DataManager(
            report_path=settings.report_path,
            administradoras=ADMINISTRADORAS,
            contracts=CONTRATOS,
        )
        invoice_df = data_manager.load_excel()
        invoice_mapping = data_manager.get_expected_files()

        logger.info(f"✅ Loaded {len(invoice_mapping)} invoices")
        stats["total_files"] = len(invoice_mapping)

        # ========== PHASE 2: STAGING ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2: Staging files from source directory")
        logger.info("=" * 60)

        folder_service = InvoiceFolderService(
            source_path=settings.source_path,
            staging_path=settings.staging_path,
            final_path=settings.final_path,
        )

        staging_results = folder_service.stage_files(dry_run=dry_run)
        stats["staged"] = staging_results["moved"]
        logger.info(
            f"✅ Staged {staging_results['moved']} files "
            f"({staging_results['failed']} failures)"
        )

        # ========== PHASE 3: CLEANUP ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 3: Deleting non-PDF files")
        logger.info("=" * 60)

        file_service = FileService(base_path=settings.staging_path)
        cleanup_results = file_service.delete_non_pdfs(
            directory=settings.staging_path,
            dry_run=dry_run,
        )
        logger.info(
            f"✅ Non-PDF cleanup: {cleanup_results['deleted']} files removed"
        )

        # ========== PHASE 4: FILENAME VALIDATION ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 4: Validating file naming structure")
        logger.info("=" * 60)

        pdfs = file_service.get_pdfs(settings.staging_path)
        invalid_files = [
            f
            for f in pdfs
            if not file_service.validate_filename_format(f.name)
        ]

        if invalid_files:
            logger.warning(f"⚠️  Found {len(invalid_files)} files with invalid names")
            for f in invalid_files[:5]:  # Show first 5
                logger.debug(f"Invalid: {f.name}")
        else:
            logger.info(f"✅ All {len(pdfs)} files have valid names")

        # ========== PHASE 5: NIT CORRECTIONS ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 5: Correcting NIT identifiers")
        logger.info("=" * 60)

        nit_corrections = {
            # Add corrections from settings if needed
        }

        if nit_corrections:
            nit_results = file_service.apply_nit_corrections(
                directory=settings.staging_path,
                corrections=nit_corrections,
                dry_run=dry_run,
            )
            logger.info(f"✅ NIT corrections: {nit_results['renamed']} files renamed")
        else:
            logger.info("✅ No NIT corrections needed")

        # ========== PHASE 6: PREFIX REPLACEMENTS ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 6: Applying prefix replacements")
        logger.info("=" * 60)

        prefix_replacements = {
            # Example: "OLD_PREFIX": "NEW_PREFIX"
        }

        if prefix_replacements:
            prefix_results = file_service.apply_prefix_replacements(
                directory=settings.staging_path,
                replacements=prefix_replacements,
                dry_run=dry_run,
            )
            logger.info(
                f"✅ Prefix replacements: {prefix_results['renamed']} files renamed"
            )
        else:
            logger.info("✅ No prefix replacements needed")

        # ========== PHASE 7: OCR PROCESSING ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 7: Applying OCR to text-less PDFs")
        logger.info("=" * 60)

        pdfs = file_service.get_pdfs(settings.staging_path)
        text_less_pdfs = [
            f for f in pdfs if not file_service.has_readable_text(f)
        ]

        if text_less_pdfs:
            logger.info(f"Found {len(text_less_pdfs)} text-less PDFs")

            if not dry_run:
                pdf_processor = PDFProcessor(
                    max_workers=settings.max_workers,
                    ocr_timeout=settings.ocr_timeout,
                )
                ocr_results = pdf_processor.process_ocr_batch(text_less_pdfs)
                stats["ocr_success"] = ocr_results["success"]
                stats["ocr_failed"] = ocr_results["failed"]
                logger.info(
                    f"✅ OCR complete: {ocr_results['success']} succeeded, "
                    f"{ocr_results['failed']} failed"
                )
            else:
                logger.info(
                    f"[DRY-RUN] Would apply OCR to {len(text_less_pdfs)} PDFs"
                )
        else:
            logger.info("✅ All PDFs already have readable text")

        # ========== PHASE 8: COMPRESSION ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 8: Compressing PDF files")
        logger.info("=" * 60)

        if not dry_run:
            pdf_processor = PDFProcessor(
                max_workers=settings.max_workers,
            )
            compress_results = pdf_processor.process_compression_batch(
                files=pdfs,
                quality=settings.compress_quality,
            )
            stats["compression_success"] = compress_results["success"]
            stats["compression_failed"] = compress_results["failed"]
            logger.info(
                f"✅ Compression complete: {compress_results['success']} succeeded, "
                f"{compress_results['failed']} failed"
            )
        else:
            logger.info(f"[DRY-RUN] Would compress {len(pdfs)} PDFs")

        # ========== PHASE 9: ORGANIZATION ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 9: Organizing files by invoice hierarchy")
        logger.info("=" * 60)

        org_results = folder_service.organize_by_hierarchy(
            invoice_mapping=invoice_mapping,
            dry_run=dry_run,
        )
        stats["organized"] = org_results["organized"]
        logger.info(
            f"✅ Organization: {org_results['organized']} organized, "
            f"{org_results['unmatched']} unmatched"
        )

        # ========== PHASE 10: FINALIZATION ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 10: Moving files to final destination")
        logger.info("=" * 60)

        final_results = folder_service.finalize_files(dry_run=dry_run)
        stats["finalized"] = final_results["finalized"]
        logger.info(
            f"✅ Finalization: {final_results['finalized']} files moved"
        )

        # ========== PHASE 11: VALIDATION ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 11: Validating final structure")
        logger.info("=" * 60)

        validation_results = folder_service.validate_final_structure(
            expected_invoices=list(invoice_mapping.keys())
        )

        if validation_results["missing"] == 0:
            logger.info(f"✅ All {validation_results['found']} invoices verified")
        else:
            logger.warning(
                f"⚠️  {validation_results['missing']} invoices missing in final destination"
            )
            for invoice_id in validation_results["missing_invoices"][:10]:
                logger.debug(f"Missing: {invoice_id}")

        # ========== CLEANUP ==========
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 12: Cleaning up staging directory")
        logger.info("=" * 60)

        cleanup_final = folder_service.cleanup_staging(dry_run=dry_run)
        logger.info(f"✅ Staging cleanup: {cleanup_final['deleted']} files removed")

    except PDFProcessorError as e:
        logger.error(f"Processing error: {str(e)}")
        stats["errors"].append(str(e))
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        stats["errors"].append(str(e))
        raise

    return stats


def print_summary(stats: dict) -> None:
    """
    Print processing summary statistics.

    Args:
        stats: Dictionary with processing statistics
    """
    logger.info("\n" + "=" * 60)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total invoices: {stats['total_files']}")
    logger.info(f"Files staged: {stats['staged']}")
    logger.info(f"Files organized: {stats['organized']}")
    logger.info(f"Files finalized: {stats['finalized']}")
    logger.info(f"OCR succeeded: {stats['ocr_success']}")
    logger.info(f"OCR failed: {stats['ocr_failed']}")
    logger.info(f"Compression succeeded: {stats['compression_success']}")
    logger.info(f"Compression failed: {stats['compression_failed']}")

    if stats["errors"]:
        logger.error(f"Errors: {len(stats['errors'])}")
        for error in stats["errors"]:
            logger.error(f"  - {error}")


def main() -> int:
    """
    Main entry point.

    Returns:
        0 if successful, 1 if errors occurred
    """
    try:
        # For now, run in dry-run mode
        dry_run = True
        logger.info(f"Starting PDF Processor (dry_run={dry_run})")

        stats = process_invoices(dry_run=dry_run)
        print_summary(stats)

        if stats["errors"]:
            logger.error("Processing completed with errors")
            return 1
        else:
            logger.info("Processing completed successfully")
            return 0

    except PDFProcessorError as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1
    except KeyboardInterrupt:
        logger.info("Processing cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
