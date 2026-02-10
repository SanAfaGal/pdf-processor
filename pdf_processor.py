from typing import List, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess
import os
import shutil
import logging
import ocrmypdf
from tqdm import tqdm # Necesitas: pip install tqdm

class PDFProcessor:
    """Orquestador de procesos masivos con feedback visual."""

    @staticmethod
    def check_dependencies():
        """Verifica herramientas antes de empezar."""
        gs = "gswin64c" if os.name == "nt" else "gs"
        deps = ["ocrmypdf", gs]
        for d in deps:
            if shutil.which(d) is None:
                print(f"❌ Error: No se encuentra '{d}' en el sistema.")
                return False
        return True

    @staticmethod
    def run_ocr_api(file_path: Path) -> str:
        """
        Usa la librería ocrmypdf directamente. 
        Retorna un código de estado para la estadística.
        """
        try:
            # ocrmypdf.ocr es la función core
            ocrmypdf.ocr(
                input_file_or_options=file_path,
                output_file=file_path,  # Sobrescribe directamente
                language=["spa"],
            )
            return "✅"
        except ocrmypdf.exceptions.PriorOcrFoundError:
            return "⏩"  # Saltado porque ya tiene texto
        except ocrmypdf.exceptions.EncryptedPdfError:
            return "🔐"  # Encriptado
        except Exception as e:
            logging.error(f"Error en {file_path.name}: {e}")
            return "❌"
        
    @staticmethod
    def run_ocr(file_path: Path) -> bool:
        """Aplica OCRmyPDF de forma atómica limitando recursos internos."""
        temp = file_path.with_suffix(".ocr.tmp")
        
        # EXPLICACIÓN DE LOS FLAGS:
        # --jobs 1: Indica a ESTA instancia de ocrmypdf que use solo 1 núcleo.
        #           Esto permite que podamos lanzar varias instancias sin colgar la PC.
        cmd = [
            "ocrmypdf",
            "--jobs", "1",         # Evita colapsar la CPU en paralelo
            "-l", "spa",
            "-q",
            str(file_path),
            str(temp)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if temp.exists():
                temp.replace(file_path)
                return True
            return False
        except Exception:
            if temp.exists(): temp.unlink()
            return False

    @staticmethod
    def compress_gs(file_path: Path, quality: str = "ebook") -> bool:
        """Comprime usando Ghostscript."""
        temp = file_path.with_suffix(".opt.tmp")
        gs = "gswin64c" if os.name == "nt" else "gs"
        cmd = [
            gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={temp}", str(file_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            temp.replace(file_path)
            return True
        except Exception:
            if temp.exists(): temp.unlink()
            return False

    @classmethod
    def process_ocr_batch(cls, files: List[Path], max_workers: int = 4):
        """Ejecuta OCR en paralelo usando Hilos (más seguro en Windows)."""
        if not cls.check_dependencies(): return
        
        results = {"✅": 0, "❌": 0}
        
        # Usamos ThreadPoolExecutor para evitar el RuntimeError de Windows
        with tqdm(total=len(files), desc="🚀 OCR en Paralelo", unit="doc", colour="cyan") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Enviamos las tareas
                futures = {executor.submit(cls.run_ocr, f): f for f in files}
                
                for future in as_completed(futures):
                    f = futures[future]
                    if future.result():
                        results["✅"] += 1
                    else:
                        results["❌"] += 1
                    
                    pbar.set_postfix_str(f"Último: {f.name[:15]}")
                    pbar.update(1)
        return results