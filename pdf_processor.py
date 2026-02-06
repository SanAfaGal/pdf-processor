from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List
from pathlib import Path
import subprocess
import os

class PDFProcessor:
    """Orquestador de procesos masivos (Batch Processing)."""

    @staticmethod
    def run_ocr(file_path: Path) -> bool:
        """Aplica OCRmyPDF de forma atómica."""
        temp = file_path.with_suffix(".ocr.tmp")
        cmd = [
            "ocrmypdf",
            "--deskew",
            "--skip-text",
            "-l",
            "spa",
            str(file_path),
            str(temp),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            temp.replace(file_path)
            return True
        except:
            if temp.exists():
                temp.unlink()
            return False

    @staticmethod
    def compress_gs(file_path: Path, quality: str = "ebook") -> bool:
        """Comprime usando Ghostscript."""
        temp = file_path.with_suffix(".opt.tmp")
        gs = "gswin64c" if os.name == "nt" else "gs"
        cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={temp}",
            str(file_path),
        ]
        try:
            subprocess.run(cmd, check=True)
            temp.replace(file_path)
            return True
        except:
            if temp.exists():
                temp.unlink()
            return False

    @staticmethod
    def process_ocr_batch(files: List[Path], max_workers: int = 4):
        """Ejecuta OCR en paralelo sobre una lista externa de archivos."""
        results = {"✅": 0, "❌": 0}
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(PDFProcessor.run_ocr, f): f for f in files}
            for future in as_completed(futures):
                f = futures[future]
                if future.result():
                    results["✅"] += 1
                    print(f"✅ OCR: {f.name}")
                else:
                    results["❌"] += 1
                    print(f"❌ Error: {f.name}")
        return results

    def rename_by_nit(self, files: List[Path], correct_nit: str, extractor_func):
        """Corrige nombres de archivos basándose en una función extractora."""
        count = 0
        for f in files:
            current_nit = extractor_func(f.name)
            if current_nit and current_nit != correct_nit:
                new_path = f.with_name(f.name.replace(current_nit, correct_nit))
                f.rename(new_path)
                print(f"🔄 Renombrado: {f.name} → {new_path.name}")
                count += 1
        return count
