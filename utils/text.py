"""Text normalization utilities."""
import unicodedata
from typing import Any


def remove_accents(text: Any) -> str:
    """
    Remove accents and normalize text. Safe for non-string values (NaN, None, int).
    Example: 'Campaña' -> 'Campana'
    """
    if not isinstance(text, str):
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")
