"""Regular expression patterns used throughout the application."""

import re
from typing import Pattern

# NIT extraction from filename (e.g., "filename_890701078_other.pdf")
NIT_PATTERN: Pattern[str] = re.compile(r"_(\d{9})_")

# File naming validation pattern
FILENAME_VALIDATION: Pattern[str] = re.compile(
    r"^[A-Z0-9][\w\-]*\.[a-z]{2,4}$"
)

# Invoice code extraction pattern (e.g., "HSL354753" from path)
INVOICE_CODE_PATTERN: Pattern[str] = re.compile(r"([A-Z]+\d+)")

# Contract type standardization
CONTRACT_CLEANUP: Pattern[str] = re.compile(r"[\s\-_]+")

PATTERNS = {
    "nit": NIT_PATTERN,
    "filename": FILENAME_VALIDATION,
    "invoice_code": INVOICE_CODE_PATTERN,
    "contract": CONTRACT_CLEANUP,
}
