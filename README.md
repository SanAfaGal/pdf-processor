# PDF Processor 2.0

Advanced PDF batch processing, OCR, compression, and invoice organization system for healthcare records (EPS/Insurance companies).

## Overview

PDF Processor is a professional-grade application designed to handle large-scale PDF document processing workflows. It's specifically built for healthcare administration where invoice documents and medical records need to be:

- **Validated** and standardized by filename
- **Extracted** and organized into hierarchical folder structures
- **Enhanced** with OCR (Optical Character Recognition)
- **Optimized** through compression
- **Moved** through a multi-stage processing pipeline

## Key Features

✅ **Batch Processing**: Process hundreds or thousands of PDFs efficiently  
✅ **Intelligent Organization**: Automatic folder hierarchy creation based on invoice metadata  
✅ **OCR Automation**: Apply Spanish language OCR to text-less PDFs  
✅ **PDF Compression**: Intelligent compression with configurable quality levels  
✅ **Multi-Stage Pipeline**: Source → Staging → Final destination workflow  
✅ **Dry-Run Mode**: Preview changes before executing  
✅ **Comprehensive Logging**: Structured JSON logging for debugging  
✅ **Configuration Management**: Environment-based settings with validation  
✅ **Type Hints**: Full Python type hints for IDE support  
✅ **Cross-Platform**: Works on Windows, Linux, and macOS

## Project Structure

```
pdf-processor/
├── src/                          # Main application code
│   ├── __init__.py
│   ├── core/                     # Core processing modules
│   │   ├── __init__.py
│   │   ├── data_manager.py       # Excel data loading and normalization
│   │   └── pdf_processor.py      # OCR and compression operations
│   ├── services/                 # Service layer
│   │   ├── __init__.py
│   │   ├── file_service.py       # File operations and validation
│   │   └── invoice_folder_service.py  # Invoice organization and movement
│   └── config/                   # Configuration and utilities
│       ├── __init__.py
│       ├── logger.py             # Logging configuration
│       ├── patterns.py           # Regex patterns
│       ├── settings.py           # Pydantic settings model
│       ├── settings_data.py      # Lookup tables (administradoras, contracts)
│       └── exceptions.py         # Custom exception classes
├── config/                       # Configuration files
│   └── (future: logging.ini, etc.)
├── tests/                        # Test suite
├── docs/                         # Documentation
├── main.py                       # Application entry point
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project metadata (PEP 517/518)
└── README.md                    # This file
```

## Installation

### Prerequisites

- **Python**: 3.9 or higher
- **System Dependencies**:
  - **ocrmypdf**: For OCR functionality
  - **Ghostscript**: For PDF compression
  - **Pandas-compatible system**: (Usually just Python)

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/pdf-processor.git
   cd pdf-processor
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install system dependencies**:

   **Windows**:
   ```powershell
   # Using Chocolatey
   choco install ghostscript ocrmypdf
   
   # Or download manually
   # - Ghostscript: https://www.ghostscript.com/download/gsdnld.html
   # - ocrmypdf: pip install ocrmypdf (includes pre-built binaries)
   ```

   **Linux (Ubuntu/Debian)**:
   ```bash
   sudo apt-get install ghostscript ocrmypdf
   ```

   **macOS**:
   ```bash
   brew install ghostscript ocrmypdf
   ```

5. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your paths and settings
   ```

6. **Run**:
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables (.env)

Create a `.env` file in the project root (see `.env.example`):

```ini
# File Paths (use absolute paths or relative to project root)
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
DRY_RUN=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=./logs/pdf-processor.log
```

### Settings Validation

Settings are validated using Pydantic v2. Invalid values raise `ConfigurationError`. Examples:

```python
from src.config import Settings

settings = Settings()  # Loads from .env

# Access configuration
print(settings.source_path)      # Path object
print(settings.max_workers)      # Integer
print(settings.log_level)        # String (validated)
print(settings.compress_quality) # 0-100 (validated)
```

## Usage

### Basic Workflow

```python
from src.core import DataManager, PDFProcessor
from src.services import FileService, InvoiceFolderService
from src.config import Settings

# 1. Initialize settings
settings = Settings()
settings.create_directories()

# 2. Load invoice metadata
data_manager = DataManager(report_path=settings.report_path)
invoice_mapping = data_manager.load_excel()  # Returns DataFrame

# 3. Stage files
folder_service = InvoiceFolderService(
    source_path=settings.source_path,
    staging_path=settings.staging_path,
    final_path=settings.final_path,
)
folder_service.stage_files(dry_run=False)

# 4. Validate and organize
file_service = FileService(base_path=settings.staging_path)
pdfs = file_service.get_pdfs(settings.staging_path)

# 5. Apply OCR (optional)
pdf_processor = PDFProcessor(max_workers=settings.max_workers)
ocr_results = pdf_processor.process_ocr_batch(pdfs)

# 6. Compress PDFs (optional)
compress_results = pdf_processor.process_compression_batch(pdfs)

# 7. Finalize
folder_service.finalize_files()
```

### Dry-Run Mode

Test changes before executing:

```bash
# In .env
DRY_RUN=true

python main.py  # Preview changes
```

All operations will log "[DRY-RUN]" prefix without making actual changes.

### Processing Pipeline Phases

1. **Phase 1**: Load invoice metadata from Excel
2. **Phase 2**: Stage files from source to staging directory
3. **Phase 3**: Delete non-PDF files
4. **Phase 4**: Validate filename structure
5. **Phase 5**: Correct NIT identifiers
6. **Phase 6**: Apply prefix replacements
7. **Phase 7**: Apply OCR to text-less PDFs
8. **Phase 8**: Compress PDF files
9. **Phase 9**: Organize files by invoice hierarchy
10. **Phase 10**: Move files to final destination
11. **Phase 11**: Validate final structure
12. **Phase 12**: Cleanup staging directory

## Logging

Logging is configured via [src/config/logger.py](src/config/logger.py).

### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages
- `WARNING`: Warning messages (potential issues)
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

### Log Format

Default is JSON format (structured logging):

```json
{
  "timestamp": "2026-02-04 12:34:56,789",
  "level": "INFO",
  "module": "src.core.data_manager",
  "message": "Loaded 150 invoices",
  "exception": null
}
```

For human-readable format, set `LOG_FORMAT=text` in `.env`.

### Log Output

- **Console**: Always output to console
- **File**: Optional file logging to `LOG_FILE` path (rotating logs, 10MB per file, 5 backups)

## Development

### Setting Up Development Environment

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
black .
isort .
flake8 src/

# Type checking
mypy src/
```

### Code Style

- **Formatter**: Black (line length: 88)
- **Import sorter**: isort (profile: black)
- **Linter**: Flake8
- **Type hints**: MyPy
- **Docstring format**: Google style

### Project Principles (SOLID + DRY)

1. **Single Responsibility**: Each class has one reason to change
2. **Open/Closed**: Open for extension, closed for modification
3. **Liskov Substitution**: Subtypes interchangeable
4. **Interface Segregation**: Clients depend on specific interfaces
5. **Dependency Inversion**: Depend on abstractions, not concretions
6. **DRY**: Don't Repeat Yourself (no duplicate code)

## Troubleshooting

### Common Issues

#### "ocrmypdf not found"
```bash
pip install ocrmypdf
# Or install system package: apt-get install ocrmypdf (Linux)
```

#### "Ghostscript not found"
```bash
# Windows: choco install ghostscript
# Linux: apt-get install ghostscript
# macOS: brew install ghostscript
```

#### "Invalid configuration"
Check `.env` file:
- Verify all paths are valid
- Check log level is one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Ensure compress_quality is 0-100
- Verify max_workers >= 1

#### "Module not found: src.config"
Ensure you're running from project root:
```bash
cd /path/to/pdf-processor
python main.py
```

### Debug Mode

Enable debug logging:

```ini
# .env
LOG_LEVEL=DEBUG
DRY_RUN=true
```

Then check `logs/pdf-processor.log` for detailed output.

## API Reference

### DataManager

```python
class DataManager:
    def load_excel() -> pd.DataFrame
    def get_expected_files() -> Dict[str, Path]
    def get_invoice_metadata(invoice_id: str) -> Optional[Dict]
```

### FileService

```python
class FileService:
    def list_files(directory, extension, recursive) -> List[Path]
    def get_pdfs(directory, recursive) -> List[Path]
    def is_valid_pdf(file_path) -> bool
    def has_readable_text(file_path) -> bool
    def extract_nit_from_filename(filename) -> Optional[str]
    def validate_filename_format(filename) -> bool
    def rename_file(old_path, new_name, overwrite) -> Optional[Path]
    def delete_non_pdfs(directory, dry_run) -> dict
    def apply_nit_corrections(directory, corrections, dry_run) -> dict
    def apply_prefix_replacements(directory, replacements, dry_run) -> dict
```

### InvoiceFolderService

```python
class InvoiceFolderService:
    def stage_files(dry_run) -> dict
    def organize_by_hierarchy(invoice_mapping, dry_run) -> dict
    def finalize_files(dry_run) -> dict
    def validate_final_structure(expected_invoices) -> dict
    def cleanup_staging(dry_run) -> dict
```

### PDFProcessor

```python
class PDFProcessor:
    def run_ocr(file_path) -> bool
    def compress_pdf(file_path, quality, output_path) -> bool
    def process_ocr_batch(files, callback) -> dict
    def process_compression_batch(files, quality, callback) -> dict
```

## Performance Considerations

### Optimization Tips

1. **Adjust worker count**: 
   - CPU-bound (OCR): `MAX_WORKERS = CPU_COUNT - 1`
   - I/O-bound (moving files): `MAX_WORKERS = CPU_COUNT * 2`

2. **Compression quality**:
   - Faster: `COMPRESS_QUALITY=50`
   - Balanced: `COMPRESS_QUALITY=85` (default)
   - Maximum: `COMPRESS_QUALITY=95`

3. **Batch processing**: Process in chunks for large datasets

4. **Use SSD**: Place `STAGING_PATH` on fastest available storage

### Memory Management

The application uses:
- Generators for file listing (memory efficient)
- Streaming for PDF operations
- Connection pooling for subprocess management

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- 📖 **Documentation**: See docs/ folder
- 🐛 **Report Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📧 **Email**: dev@organization.com

## Changelog

### Version 2.0.0 (2026-02-04)
- ✨ Complete refactor for production standards
- ✨ Implemented full type hints and docstrings
- ✨ Consolidated FileManager + FileService
- ✨ Added Pydantic-based configuration management
- ✨ Implemented structured JSON logging
- ✨ Added dry-run mode for all operations
- ✨ Professional error handling with custom exceptions
- ✨ SOLID principles and DRY compliance

### Version 1.0.0 (2026-01-15)
- 🎉 Initial release
