import re
import logging
from pathlib import Path
from typing import List, Union
import fitz


class FileManager:
    # Regex para extraer NIT (9 dígitos) entre guiones
    NIT_REGEX = re.compile(r"_(\d*)_")

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def _is_valid(file_path: Path) -> bool:
        """Verifica si el PDF abre correctamente."""
        try:
            with fitz.open(file_path) as doc:
                return doc.page_count > 0
        except:
            return False

    def _has_text(file_path: Path) -> bool:
        """Verifica si tiene texto legible (si no, necesita OCR)."""
        try:
            with fitz.open(file_path) as doc:
                return any(page.get_text().strip() for page in doc)
        except:
            return False

    def get_files_by_extension(self, ext: str = "pdf") -> List[Path]:
        """Retorna una lista de rutas con la extensión deseada."""
        return list(self.base_path.rglob(f"*.{ext}"))

    def list_non_compliant_files(self, allowed_ext: str = "pdf") -> List[Path]:
        """Identifica archivos que no deberían estar en las carpetas."""
        return [
            f
            for f in self.base_path.rglob("*")
            if f.is_file() and f.suffix.lower() != f".{allowed_ext}"
        ]

    """Retornar archivos cuyo contenido no contenga el numero de factura que indica su sufijo HSLXXXXXX"""

    def list_files_with_missing_invoice_number(self, files: List[Path]) -> List[Path]:
        """Retorna una lista de archivos cuyo contenido no contiene el número de factura en su nombre."""
        files_missing_invoice = []
        for f in files:
            invoice_code = re.search(r"(HSL\d{4,})", f.stem.upper())
            if invoice_code:
                code = invoice_code.group(1)
                try:
                    with fitz.open(f) as doc:
                        content = ""
                        for page in doc:
                            content += page.get_text()
                        if code not in content.upper():
                            files_missing_invoice.append(f)
                except Exception as e:
                    logging.error(f"Error leyendo {f}: {e}")
        return files_missing_invoice

    def list_files_by_prefixes(self, prefixes: Union[str, List[str]]) -> List[Path]:
        """
        Retorna archivos que comienzan con uno o varios prefijos.
        Ejemplo de uso: fm.list_files_by_prefixes(["HSL", "FVE"])
        """
        # startswith() requiere una tupla si son múltiples valores
        search_criteria = tuple(prefixes) if isinstance(prefixes, list) else prefixes

        return [
            f
            for f in self.base_path.rglob("*")
            if f.is_file() and f.name.upper().startswith(search_criteria)
        ]

    """retornar archivos que necesiten aplicar OCR"""

    def list_files_needing_ocr(self, files: List[Path]) -> List[Path]:
        """Retorna una lista de archivos que necesitan OCR."""
        return [
            f
            for f in files
            if FileManager._is_valid(f) and not FileManager._has_text(f)
        ]

    def delete_files(self, files_to_delete: List[Path]) -> int:
        """Borra una lista específica de archivos y retorna cuántos borró."""
        count = 0
        for f in files_to_delete:
            try:
                f.unlink()
                count += 1
            except Exception as e:
                logging.error(f"No se pudo borrar {f}: {e}")
        return count

    @staticmethod
    def extract_nit_from_name(filename: str) -> str | None:
        match = FileManager.NIT_REGEX.search(filename)
        return match.group(1) if match else None

    def verify_file_in_dirs(self, prefixes: Union[str, List[str]]) -> List[Path]:
        """
        Verifica que cada directorio tenga al menos un archivo que comience 
        con alguno de los prefijos proporcionados.
        
        Retorna la lista de carpetas a las que les falta dicho archivo.
        """
        missing_invoice_dirs = []
        
        # Normalizamos a tupla para que startswith funcione con múltiples valores
        if isinstance(prefixes, list):
            search_criteria = tuple(p.upper() for p in prefixes)
        else:
            search_criteria = prefixes.upper()

        # Recorremos todos los subdirectorios
        for dir_path in self.base_path.rglob("*"):
            if dir_path.is_dir():
                # Verificamos si existe al menos UN archivo que cumpla el criterio
                has_invoice = any(
                    f.is_file() and f.name.upper().startswith(search_criteria)
                    for f in dir_path.iterdir()
                )
                
                # Si la carpeta está vacía de esos prefijos, la guardamos
                if not has_invoice:
                    missing_invoice_dirs.append(dir_path)
                    
        return missing_invoice_dirs

    def validate_file_naming_structure(
        self, 
        files: List[Path], 
        valid_prefixes: List[str], 
        suffix: str,
        nit: str
    ) -> List[Path]:
        """
        Valida archivos siguiendo el patrón
        """
        invalid_files = []
        
        # 1. Creamos los grupos para el regex (ej: "FEV|OPF|CRC")
        prefixes_group = "|".join(re.escape(p) for p in valid_prefixes)
        
        # 2. Construimos el patrón dinámico
        # ^(FEV|OPF|...)_890701078_HSL\d{6}\.pdf$
        pattern_str = rf"^({prefixes_group})_{nit}_{suffix}\d{{6}}\.pdf$"
        pattern = re.compile(pattern_str, re.IGNORECASE)

        for f in files:
            if not pattern.match(f.name):
                invalid_files.append(f)
                
        return invalid_files

    def rename_files_by_prefix_map(self, prefix_replacements: dict) -> int:
        """Renombra archivos basándose en un mapa de prefijos y retorna cuántos renombró."""
        count = 0
        for f in self.base_path.rglob("*"):
            if f.is_file():
                parts = f.name.split("_", 1)
                if len(parts) > 1:
                    current_prefix = parts[0].upper()
                    if current_prefix in prefix_replacements:
                        new_prefix = prefix_replacements[current_prefix]
                        new_name = f"{new_prefix}_{parts[1]}"
                        new_path = f.with_name(new_name)
                        try:
                            f.rename(new_path)
                            count += 1
                        except Exception as e:
                            logging.error(f"No se pudo renombrar {f}: {e}")
        return count

    def rename_files_by_correct_nit(self, files: List[Path], correct_nit: str) -> int:
        count = 0
        for f in files:
            try:
                current_nit = self.extract_nit_from_name(f.name)
                if current_nit and current_nit != correct_nit:
                    parts = f.name.split("_", 2)
                    if len(parts) == 3:
                        new_name = f"{parts[0]}_{correct_nit}_{parts[2]}"
                        new_path = f.with_name(new_name)
                        f.rename(new_path)
                        count += 1
            except Exception as e:
                logging.error(f"No se pudo renombrar {f}: {e}")
        return count

