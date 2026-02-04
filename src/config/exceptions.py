"""Custom exceptions for PDF Processor."""


class PDFProcessorError(Exception):
    """Base exception for PDF Processor."""

    pass


class InvoiceProcessingError(PDFProcessorError):
    """Exception raised during invoice processing."""

    pass


class PDFProcessingError(PDFProcessorError):
    """Exception raised during PDF-specific operations."""

    pass


class DataValidationError(PDFProcessorError):
    """Exception raised during data validation."""

    pass


class FileOperationError(PDFProcessorError):
    """Exception raised during file operations."""

    pass


class ConfigurationError(PDFProcessorError):
    """Exception raised during configuration."""

    pass
