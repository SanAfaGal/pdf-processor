"""File and list persistence utilities."""
import logging
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


def save_report(
    df: pd.DataFrame,
    default_name: str,
    custom_path: Optional[Path] = None,
) -> None:
    """
    Save a DataFrame to Excel or CSV. Creates parent dirs if needed.
    Raises: None; logs on error.
    """
    if df.empty:
        logger.warning("Report '%s' is empty; not saving.", default_name)
        return
    save_path = Path(custom_path) if custom_path else Path(default_name)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if save_path.suffix.lower() == ".csv":
            df.to_csv(save_path, index=False, sep=";", encoding="utf-8-sig")
        else:
            save_path = save_path.with_suffix(".xlsx")
            df.to_excel(save_path, index=False, engine="openpyxl")
        logger.info("Report saved: %s (%s rows)", save_path.name, len(df))
    except Exception as e:
        logger.error("Failed to save report to %s: %s", save_path, e)


def safe_move(src: Path, dest: Path) -> bool:
    """Move src to dest. Returns True on success. Does not overwrite."""
    try:
        if dest.exists():
            logger.error("Destination already exists: %s", dest)
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return True
    except Exception as e:
        logger.error("Move failed %s -> %s: %s", src.name, dest, e)
        return False


def get_list_from_file(file_path: Union[str, Path]) -> List[str]:
    """Read a text file and return trimmed non-empty lines. Returns [] on error or missing file."""
    path = Path(file_path)
    if not path.exists():
        logger.error("File not found: %s", path)
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error("Error reading %s: %s", path, e)
        return []


def save_list_as_file(
    values: Optional[Iterable[str]] = None,
    file: Optional[Union[str, Path]] = None,
) -> None:
    """Write one value per line to file. Creates parent dirs. values=None treated as empty."""
    if values is None:
        values = []
    path = Path(file) if file else Path("list.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.writelines(f"{v}\n" for v in values)


def flatten_prefixes(prefixes_dict: Dict[str, Union[str, List[str]]]) -> List[str]:
    """Flatten a dict of prefix keys to a list of unique prefix strings."""
    flat: List[str] = []
    for value in prefixes_dict.values():
        if isinstance(value, list):
            flat.extend(value)
        else:
            flat.append(str(value))
    return list(set(flat))
