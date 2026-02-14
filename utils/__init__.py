"""Shared utilities: text, persistence, prefixes."""
from utils.text import remove_accents
from utils.persistence import (
    save_report,
    safe_move,
    get_list_from_file,
    save_list_as_file,
    flatten_prefixes,
)

__all__ = [
    "remove_accents",
    "save_report",
    "safe_move",
    "get_list_from_file",
    "save_list_as_file",
    "flatten_prefixes",
]
