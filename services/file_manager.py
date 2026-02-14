"""
File system operations for PDF discovery, validation, and listing.
Handles scan/list/validate; mutations (move, delete, rename) are explicit.
"""
import re
import logging
import shutil
from pathlib import Path
from typing import List, Optional, Set, Union

import fitz

from utils.text import remove_accents

logger = logging.getLogger(__name__)

# Regex for NIT (digits between underscores) in filename
NIT_REGEX = re.compile(r"_(\d+)_")


def _normalize_skip_to_names(
    skip: Optional[Union[List[str], List[Path]]]
) -> Set[str]:
    """Convert skip list (names or Paths) to a set of folder names for comparison."""
    if not skip:
        return set()
    names: Set[str] = set()
    for item in skip:
        if isinstance(item, Path):
            names.add(item.name)
        else:
            names.add(str(item))
    return names


def _is_valid_pdf(file_path: Path) -> bool:
    """Return True if the PDF opens and has at least one page."""
    try:
        with fitz.open(file_path) as doc:
            return doc.page_count > 0
    except Exception:
        return False


def _has_text(file_path: Path) -> bool:
    """Return True if the PDF has extractable text (no OCR needed)."""
    try:
        with fitz.open(file_path) as doc:
            return any(page.get_text().strip() for page in doc)
    except Exception:
        return False


class FileManager:
    """Scan and list PDFs under a base path; validate naming and content."""

    NIT_REGEX = NIT_REGEX

    def __init__(self, base_path: Union[str, Path]) -> None:
        self.base_path = Path(base_path)

    def get_files_by_extension(self, ext: str = "pdf") -> List[Path]:
        """Return all files with the given extension under base_path."""
        return list(self.base_path.rglob(f"*.{ext}"))

    def get_files_by_folders(
        self,
        folder_names: List[str],
        ext: str = "pdf",
    ) -> List[Path]:
        """Return files with ext inside the given folder names (under base_path)."""
        files_found: List[Path] = []
        for folder_name in folder_names:
            folder_dir = self.base_path / folder_name
            if folder_dir.is_dir():
                files_found.extend(list(folder_dir.rglob(f"*.{ext}")))
            else:
                logger.warning("Folder missing or invalid: %s", folder_dir)
        return files_found

    def list_non_compliant_files(self, allowed_ext: str = "pdf") -> List[Path]:
        """Return files that do not have the allowed extension."""
        return [
            f
            for f in self.base_path.rglob("*")
            if f.is_file() and f.suffix.lower() != f".{allowed_ext}"
        ]

    def list_files_with_missing_invoice_number(
        self,
        files: List[Path],
    ) -> List[Path]:
        """Return files whose content does not contain the HSL invoice code from their name."""
        files_missing: List[Path] = []
        for f in files:
            invoice_code = re.search(r"(HSL\d{4,})", f.stem.upper())
            if not invoice_code:
                continue
            code = invoice_code.group(1)
            try:
                with fitz.open(f) as doc:
                    content = "".join(page.get_text() for page in doc)
                if code not in content.upper():
                    files_missing.append(f)
            except Exception as e:
                logger.error("Error reading %s: %s", f, e)
        return files_missing

    def list_dirs(self) -> List[Path]:
        """Return all directories under base_path."""
        return [d for d in self.base_path.rglob("*") if d.is_dir()]

    def list_dirs_with_extra_text(
        self,
        skip: Optional[Union[List[str], List[Path]]] = None,
    ) -> List[Path]:
        """Return directories that do not match pattern HSL + 6 digits. skip: folder names or Paths to ignore."""
        skip_names = _normalize_skip_to_names(skip)
        records: List[Path] = []
        for path in self.base_path.iterdir():
            if not path.is_dir():
                continue
            if path.name in skip_names:
                continue
            if not re.match(r"HSL\d{6}$", path.name.upper()):
                records.append(path)
        return records

    def get_path_of_folders_names(self, folders: List[str]) -> List[Path]:
        """Return Paths of direct children of base_path whose name is in folders."""
        return [
            p
            for p in self.base_path.iterdir()
            if p.is_dir() and p.name in folders
        ]

    def _normalize_folder_id(self, name: str) -> str:
        """Normalize folder name to comparable ID (e.g. HSL123456)."""
        m = re.search(r"HSL[_\-]?(\d+)", name, re.IGNORECASE)
        if m:
            return "HSL" + m.group(1).zfill(6)[:6]
        return name

    def get_folders_missing_on_disk(self, folders: List[str]) -> List[str]:
        """Return folder IDs from the list that are not present under base_path (by normalized ID)."""
        on_disk: Set[str] = set()
        for p in self.base_path.iterdir():
            if p.is_dir():
                on_disk.add(self._normalize_folder_id(p.name))
        wanted = {self._normalize_folder_id(name) for name in folders}
        return list(wanted - on_disk)

    def move_files_to_right_folder(
        self,
        missing_files_path: Path,
    ) -> int:
        """
        Move each file under missing_files_path into base_path / folder_name.
        Folder name is taken from the third part of file stem (split by '_').
        Returns number of files moved. Logs and skips invalid names or missing destination.
        """
        count = 0
        for f in missing_files_path.rglob("*"):
            if not f.is_file():
                continue
            parts = f.stem.split("_")
            if len(parts) < 3:
                logger.warning("Skip (invalid name): %s", f.name)
                continue
            folder_name = parts[2]
            destination = self.base_path / folder_name
            if not destination.exists():
                logger.warning("Destination folder does not exist: %s (file: %s)", destination, f.name)
                continue
            try:
                shutil.move(str(f), str(destination / f.name))
                count += 1
            except Exception as e:
                logger.error("Move failed %s: %s", f, e)
        return count

    def list_paths_containing_text(
        self,
        files: List[Path],
        txt_to_find: Optional[str] = None,
        return_parent: bool = True,
    ) -> List[Path]:
        """Return paths (parent dir or file) where PDF content contains txt_to_find. Returns [] if txt_to_find is None."""
        if not txt_to_find:
            return []
        results: Set[Path] = set()
        search_term = remove_accents(txt_to_find).upper()
        for f in files:
            try:
                with fitz.open(f) as doc:
                    content = "".join(page.get_text() for page in doc)
                content_clean = remove_accents(content).upper()
                if search_term in content_clean:
                    results.add(f.parent if return_parent else f)
            except Exception as e:
                logger.error("Error reading %s: %s", f, e)
        return list(results)

    def list_files_by_prefixes(
        self,
        prefixes: Union[str, List[str]],
    ) -> List[Path]:
        """Return files under base_path whose name starts with one of the prefixes."""
        criteria = tuple(prefixes) if isinstance(prefixes, list) else (prefixes,)
        return [
            f
            for f in self.base_path.rglob("*")
            if f.is_file() and f.name.upper().startswith(criteria)
        ]

    def list_files_needing_ocr(self, files: List[Path]) -> List[Path]:
        """Return files that are valid PDFs but have no extractable text."""
        return [
            f
            for f in files
            if _is_valid_pdf(f) and not _has_text(f)
        ]

    def check_invalid_files(self, files: List[Path]) -> List[Path]:
        """Return files that cannot be opened as valid PDFs."""
        return [f for f in files if not _is_valid_pdf(f)]

    def delete_files(self, files_to_delete: List[Path]) -> int:
        """Delete the given files. Returns number deleted. Logs errors."""
        count = 0
        for f in files_to_delete:
            try:
                f.unlink()
                count += 1
            except Exception as e:
                logger.error("Could not delete %s: %s", f, e)
        return count

    @staticmethod
    def extract_nit_from_name(filename: str) -> Optional[str]:
        """Extract NIT (digits between first underscores) from filename."""
        m = NIT_REGEX.search(filename)
        return m.group(1) if m else None

    def verify_file_in_dirs(
        self,
        prefixes: Union[str, List[str]],
        skip: Optional[Union[List[str], List[Path]]] = None,
        target_dirs: Optional[List[Path]] = None,
    ) -> List[Path]:
        """Return directories that do not contain any file whose name starts with the given prefix(es)."""
        skip_names = _normalize_skip_to_names(skip)
        if isinstance(prefixes, list):
            search_criteria = tuple(p.upper() for p in prefixes)
        else:
            search_criteria = (prefixes.upper(),)
        if target_dirs is not None:
            dirs_to_scan = target_dirs
        else:
            dirs_to_scan = [p for p in self.base_path.rglob("*") if p.is_dir()]
        missing: List[Path] = []
        for dir_path in dirs_to_scan:
            if not dir_path.is_dir() or dir_path.name in skip_names:
                continue
            has_match = any(
                f.is_file() and f.name.upper().startswith(search_criteria)
                for f in dir_path.iterdir()
            )
            if not has_match:
                missing.append(dir_path)
        return missing

    def validate_file_naming_structure(
        self,
        valid_prefixes: List[str],
        suffix: str,
        nit: str,
    ) -> List[Path]:
        """Return PDFs whose name does not match PREFIX_NIT_SUFFIX{6}.pdf."""
        prefixes_group = "|".join(re.escape(p) for p in valid_prefixes)
        pattern = re.compile(
            rf"^({prefixes_group})_{nit}_{suffix}\d{{6}}\.pdf$",
            re.IGNORECASE,
        )
        return [
            f
            for f in self.get_files_by_extension("pdf")
            if not pattern.match(f.name)
        ]

    def rename_files_by_prefix_map(
        self,
        prefix_replacements: dict,
        target_files: Optional[List[Path]] = None,
    ) -> int:
        """Rename files by replacing leading prefix per map. Returns count renamed."""
        if not target_files:
            return 0
        count = 0
        for f in target_files:
            if not f.is_file():
                continue
            parts = f.name.split("_", 1)
            if len(parts) < 2:
                continue
            current = parts[0].upper()
            if current not in prefix_replacements:
                continue
            new_name = prefix_replacements[current] + "_" + parts[1]
            new_path = f.with_name(new_name)
            try:
                f.rename(new_path)
                count += 1
            except Exception as e:
                logger.error("Rename failed %s: %s", f, e)
        return count

    def list_dirs_with_anular(self) -> List[Path]:
        """Return direct child dirs whose name contains 'ANULAR'."""
        return [
            d
            for d in self.base_path.iterdir()
            if d.is_dir() and "ANULAR" in d.name.upper()
        ]

    def has_cufe(self, file_path: Path) -> bool:
        """Return True if PDF content contains a CUFE (64+ hex chars)."""
        try:
            with fitz.open(file_path) as doc:
                content = "".join(page.get_text() for page in doc)
            clean = re.sub(r"\s+", "", content)
            return bool(re.search(r"[0-9a-fA-F]{64,}", clean))
        except Exception as e:
            logger.error("Error processing %s: %s", file_path, e)
            return False

    def get_invoices_missing_cufe(self, file_paths: List[Path]) -> List[Path]:
        """Return files that do not contain a valid CUFE."""
        return [p for p in file_paths if not self.has_cufe(p)]

    def rename_files_by_correct_nit(
        self,
        files: List[Path],
        correct_nit: str,
    ) -> int:
        """Replace NIT in filename with correct_nit. Returns count renamed."""
        count = 0
        for f in files:
            try:
                current = self.extract_nit_from_name(f.name)
                if not current or current == correct_nit:
                    continue
                parts = f.name.split("_", 2)
                if len(parts) != 3:
                    continue
                new_name = f"{parts[0]}_{correct_nit}_{parts[2]}"
                f.rename(f.with_name(new_name))
                count += 1
            except Exception as e:
                logger.error("Rename failed %s: %s", f, e)
        return count

    def list_files_with_mismatched_folder_names(
        self,
        skip_folders: Optional[Union[List[str], List[Path]]] = None,
    ) -> List[Path]:
        """
        Return files whose stem ends with HSL+digits that do not match their parent folder name.
        skip_folders: folder names or Paths to exclude from check.
        """
        skip_names = _normalize_skip_to_names(skip_folders)
        pattern = re.compile(r"(HSL\d+)$", re.IGNORECASE)
        mismatched: List[Path] = []
        for folder_path in self.base_path.iterdir():
            if not folder_path.is_dir() or folder_path.name in skip_names:
                continue
            for file_path in folder_path.iterdir():
                if not file_path.is_file():
                    continue
                m = pattern.search(file_path.stem)
                if not m:
                    continue
                file_suffix = m.group(1).upper()
                if file_suffix != folder_path.name.upper():
                    mismatched.append(file_path)
        return mismatched

    def copy_or_move_folders(
        self,
        folder_names: List[str],
        source_path: Union[str, Path],
        destination_path: Union[str, Path],
        action: str = "copy",
    ) -> dict:
        """Copy or move folders from source to destination. Returns dict with success, failed, not_found, errors."""
        src = Path(source_path)
        dst = Path(destination_path)
        results: dict = {"success": 0, "failed": 0, "not_found": 0, "errors": []}
        if not src.is_dir():
            logger.error("Source is not a directory: %s", src)
            results["errors"].append(f"Invalid source: {src}")
            return results
        try:
            dst.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("Could not create destination %s: %s", dst, e)
            results["errors"].append(str(e))
            return results
        act = action.lower()
        if act not in ("copy", "move"):
            results["errors"].append(f"Invalid action: {action}")
            return results
        for folder_name in folder_names:
            src_folder = src / folder_name
            dst_folder = dst / folder_name
            if not src_folder.is_dir():
                results["not_found"] += 1
                results["errors"].append(f"Not found: {folder_name}")
                continue
            if dst_folder.exists():
                results["failed"] += 1
                results["errors"].append(f"Destination exists: {folder_name}")
                continue
            try:
                if act == "copy":
                    shutil.copytree(src_folder, dst_folder)
                else:
                    shutil.move(str(src_folder), str(dst_folder))
                results["success"] += 1
            except Exception as e:
                logger.error("Error processing %s: %s", folder_name, e)
                results["failed"] += 1
                results["errors"].append(f"{folder_name}: {e}")
        return results
