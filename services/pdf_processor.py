"""PDF OCR and compression via ocrmypdf and Ghostscript."""
import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from tqdm import tqdm

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Run OCR and compression on PDFs with optional batch processing."""

    @staticmethod
    def check_dependencies() -> bool:
        """Return True if ocrmypdf and Ghostscript are available."""
        gs = "gswin64c" if os.name == "nt" else "gs"
        for cmd in ["ocrmypdf", gs]:
            if shutil.which(cmd) is None:
                print(f"Error: '{cmd}' not found.")
                return False
        return True

    @staticmethod
    def run_ocr(file_path: Path) -> bool:
        """Run OCRmyPDF on file (atomic: write to .ocr.tmp then replace). Returns True on success."""
        temp = file_path.with_suffix(".ocr.tmp")
        cmd = [
            "ocrmypdf", "--jobs", "1", "-l", "spa", "-q",
            str(file_path), str(temp),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if temp.exists():
                temp.replace(file_path)
                return True
            return False
        except Exception as e:
            logger.debug("OCR failed %s: %s", file_path.name, e)
            if temp.exists():
                try:
                    temp.unlink()
                except Exception:
                    pass
            return False

    @staticmethod
    def compress_gs(file_path: Path, quality: str = "ebook") -> bool:
        """Compress PDF with Ghostscript. Returns True on success."""
        temp = file_path.with_suffix(".opt.tmp")
        gs = "gswin64c" if os.name == "nt" else "gs"
        cmd = [
            gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={temp}", str(file_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if temp.exists():
                temp.replace(file_path)
                return True
            return False
        except Exception as e:
            logger.debug("Compress failed %s: %s", file_path.name, e)
            if temp.exists():
                try:
                    temp.unlink()
                except Exception:
                    pass
            return False

    @classmethod
    def process_ocr_batch(
        cls,
        files: List[Path],
        max_workers: int = 4,
    ) -> Dict[str, int]:
        """Run OCR on files in parallel. Returns dict with 'ok' and 'fail' counts."""
        if not cls.check_dependencies():
            return {"ok": 0, "fail": len(files)}
        ok = 0
        fail = 0
        with tqdm(total=len(files), desc="OCR", unit="doc") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(cls.run_ocr, f): f for f in files}
                for future in as_completed(futures):
                    if future.result():
                        ok += 1
                    else:
                        fail += 1
                    pbar.update(1)
        return {"ok": ok, "fail": fail}
