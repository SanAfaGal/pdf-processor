# file_service.py
from pathlib import Path
import re
import fitz
from typing import List, Optional, Union
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed


class FileService:
    """Servicio para operaciones con archivos"""

    NIT_REGEX = re.compile(r"_(\d{9})_")

    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        self.base_path = Path(base_path)

    def count_files(
        self, directory: Optional[Path] = None, extension: str = "pdf"
    ) -> int:
        """Cuenta archivos con la extensión especificada"""
        dir_path = directory or self.base_path
        if not dir_path:
            raise ValueError("Se requiere un directorio")
        return sum(1 for _ in dir_path.rglob(f"*.{extension}"))

    def delete_files(
        self, directory: Optional[Path] = None, extension: str = "pdf"
    ) -> int:
        """Elimina archivos con la extensión especificada. Retorna cantidad eliminada"""
        dir_path = directory or self.base_path
        if not dir_path:
            raise ValueError("Se requiere un directorio")

        deleted = 0
        for file in dir_path.rglob(f"*.{extension}"):
            file.unlink()
            deleted += 1
        return deleted

    def list_files(
        self, directory: Optional[Path] = None, extension: str = "pdf"
    ) -> List[Path]:
        """Lista archivos con la extensión especificada"""
        dir_path = directory or self.base_path
        if not dir_path:
            raise ValueError("Se requiere un directorio")
        return [file for file in dir_path.rglob(f"*.{extension}")]

    @staticmethod
    def extract_nit_from_filename(file_path: Path) -> Optional[str]:
        """Extrae el NIT del nombre del archivo"""
        match = FileService.NIT_REGEX.search(file_path.name)
        return match.group(1) if match else None

    def validate_nits_in_directory(
        self, nit_expected: str, directory: Optional[Path] = None
    ) -> List[str]:
        """Valida que los archivos PDF contengan el NIT esperado"""
        dir_path = directory or self.base_path
        if not dir_path:
            raise ValueError("Se requiere un directorio")

        invalid_files = []

        for pdf in dir_path.rglob("*.pdf"):
            nit_found = self.extract_nit_from_filename(pdf)

            if nit_found is None or nit_found != nit_expected:
                invalid_files.append(pdf.name)

        return invalid_files

    def is_valid_pdf(self, file_path: Path) -> bool:
        """Verifica si un archivo PDF es válido (no corrupto)"""
        try:

            with fitz.open(file_path) as doc:
                return doc.page_count > 0
        except Exception:
            return False

    def has_readable_text(self, file_path: Path) -> bool:
        """Verifica si un archivo PDF tiene texto extraíble"""
        try:
            with fitz.open(file_path) as doc:
                for page_num in range(doc.page_count):
                    text = doc.load_page(page_num).get_text()
                    if text.strip():
                        return True
            return False
        except Exception:
            return False

    def extract_text_from_pdf(self, file_path: Path) -> str:
        """Extrae texto de un archivo PDF usando PyMuPDF"""
        try:
            text_content = []
            with fitz.open(file_path) as doc:
                for page_num in range(doc.page_count):
                    text = doc.load_page(page_num).get_text()
                    text_content.append(text)
            return "\n".join(text_content)
        except Exception as e:
            print(f"Error al extraer texto de {file_path.name}: {e}")
            return ""


    def apply_ocr_to_pdf(self, file_path: Path) -> bool:
        """Aplica OCR y reemplaza el original si tiene éxito"""
        temp_path = file_path.with_stem(f"{file_path.stem}_tmp")
        
        command = [
            "ocrmypdf",
            "--deskew",
            "--skip-text",
            "-l", "spa",
            str(file_path),  # Convertimos a string para mayor compatibilidad
            str(temp_path),
        ]

        try:
            # Ejecución del subproceso
            subprocess.run(command, check=True, capture_output=True, text=True)
            
            # Reemplazo atómico: si el comando falló, no llegamos aquí
            temp_path.replace(file_path)
            return True

        except subprocess.CalledProcessError as e:
            if temp_path.exists(): temp_path.unlink()
            if e.returncode == 6: return True # Ya tenía texto
            return False
        except Exception:
            if temp_path.exists(): temp_path.unlink()
            return False

    def compress_pdf(self, file_path: Path, quality: str = "printer") -> bool:
        """
        quality opciones: 
        - 'screen': mínima calidad (72 dpi), máximo ahorro.
        - 'ebook': calidad media (150 dpi).
        - 'printer' o 'prepress': alta calidad (300 dpi), ideal para no perder detalle.
        """
        output_path = file_path.with_stem(f"{file_path.stem}_optimized")
        
        # Usamos 'gswin64c' en Windows o 'gs' en Linux
        gs_cmd = "gswin64c" if os.name == "nt" else "gs"
        
        command = [
            gs_cmd, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_path}",
            str(file_path)
        ]

        try:
            # Timeout para evitar que procesos se queden colgados eternamente
            subprocess.run(command, check=True, capture_output=True, timeout=60)
            return True
        except subprocess.TimeoutExpired:
            print(f"Archivo demasiado pesado o complejo: {file_path.name}")
            return False
        except Exception as e:
            print(f"Error en compresión: {e}")
            return False
    
    def process_directory_parallel(self, max_workers: int = 8):
        """
        Ejecuta el OCR en paralelo para todos los PDFs que no tengan texto.
        """
        pdf_files = self.list_files()
        # Filtramos primero: solo aplicamos OCR a los que NO tienen texto legible
        to_process = [f for f in pdf_files if not self.has_readable_text(f)]
        
        print(f"Iniciando procesamiento paralelo de {len(to_process)} archivos...")

        results = {"success": 0, "error": 0}
        
        # El corazón de la escalabilidad: ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Mapeamos la función a la lista de archivos
            future_to_pdf = {executor.submit(self.apply_ocr_to_pdf, pdf): pdf for pdf in to_process}
            
            for future in as_completed(future_to_pdf):
                pdf_name = future_to_pdf[future].name
                try:
                    if future.result():
                        results["success"] += 1
                    else:   
                        results["error"] += 1
                        print(f"Falló OCR en: {pdf_name}")
                except Exception as e:
                    print(f"Error procesando {pdf_name}: {e}")
        
        print(f"Fin del proceso. Exitosos: {results['success']}, Errores: {results['error']}")

    def validate_pdf_readability(
        self,
        directory: Optional[Union[str, Path]] = None,
        verbose: bool = False,
        show_progress: bool = False,
    ) -> List[str]:
        """
        Valida la legibilidad de archivos PDF.

        Returns:
            lista de nombres de archivos PDF no legibles
        """
        dir_path = directory or self.base_path

        # Obtener lista de PDFs primero para saber el total
        pdf_files = list(dir_path.rglob("*.pdf"))
        total = len(pdf_files)
        print(f"Total de archivos PDF a procesar: {total}")

        unreadable_files = []

        for index, pdf_file in enumerate(pdf_files, start=1):
            if show_progress:
                print(f"Procesando {index}/{total}: {pdf_file.name}")

            if not self.is_valid_pdf(pdf_file) or not self.has_readable_text(pdf_file):
                unreadable_files.append(pdf_file.name)
                if verbose:
                    print(f"Archivo no legible: {pdf_file.name}")

        return unreadable_files
