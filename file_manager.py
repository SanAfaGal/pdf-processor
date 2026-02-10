import re
import logging
import shutil
from pathlib import Path
from typing import List, Union, Literal
import fitz
from src.utils import Util

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


    def get_files_by_folders(self, folder_names: List[str], ext: str = "pdf") -> List[Path]:
        """
        Retorna una lista de rutas de archivos con la extensión deseada,
        buscando únicamente dentro de las carpetas especificadas.
        """
        files_found = []
        
        for folder_name in folder_names:
            # Construimos la ruta de la carpeta objetivo
            folder_dir = self.base_path / folder_name
            
            # Verificamos si la carpeta existe para evitar errores
            if folder_dir.is_dir():
                # Buscamos archivos con la extensión en esa carpeta (y subcarpetas)
                files_found.extend(list(folder_dir.rglob(f"*.{ext}")))
            else:
                logging.warning(f"La carpeta no existe o no es válida: {folder_dir}")
                
        return files_found

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

    def list_dirs(self) -> List[Path]:
        """Retorna una lista de todos los directorios bajo la ruta base."""
        return [d for d in self.base_path.rglob("*") if d.is_dir()]

    def list_dirs_with_extra_text(self, skip: List[Path] = None) -> List[Path]:
        """Retorna una lista de directorios que no siguen el patrón esperado (ej: HSL123456)."""
        records = []

        for path in self.base_path.iterdir():
            if path.is_dir() and path.name not in skip:
                # Verificamos si el nombre del directorio sigue el patrón HSL seguido de 6 dígitos
                if not re.match(r"HSL\d{6}$", path.name.upper()):
                    records.append(path)
        return records

    def get_path_of_folders_names(self, folders : List[str]) -> List[Path]:
        
        records = []
        for path in self.base_path.iterdir():
            if path.is_dir() and path.name in folders:
                records.append(path)
        return records

    def get_folders_missing_on_disk(self, folders: List[str]) -> List[str]:
        """
        Extrae el ID (HSL+6 dígitos) de las carpetas en disco y 
        compara contra la lista de Stream.
        """
        # Expresión regular: HSL + 1 caracter cualquiera + 6 dígitos
        pattern = re.compile(r"HSL.\d+")
        
        # 1. Obtenemos solo los IDs que cumplen el patrón de las carpetas reales
        carpetas_en_disco = set()
        for p in self.base_path.iterdir():
            if p.is_dir():
                match = pattern.search(p.name)
                if match:
                    # Guardamos el ID encontrado (ej. "HSL_123456")
                    carpetas_en_disco.add(match.group())
        
        # 2. Comparamos contra la lista de Stream
        # Nota: Asegúrate que los strings en 'folders' tengan el mismo formato (ej. "HSL_123456")
        faltantes = [name for name in folders if name not in carpetas_en_disco]
        
        return faltantes
        




    
    def list_paths_containing_text(
        self, 
        files: List[Path], 
        txt_to_find: str = None, 
        return_parent: bool = True
    ) -> List[Path]:
        """
        Retorna una lista de rutas (directorios o archivos) que contienen el texto buscado.
        
        :param files: Lista de rutas Path a revisar.
        :param txt_to_find: Texto a buscar.
        :param return_parent: Si es True, devuelve la carpeta. Si es False, devuelve el archivo.
        """
        results = set()
        # Aseguramos que el texto a buscar esté en el mismo formato que el contenido limpio
        search_term = Util.remove_accents(txt_to_find).upper()

        for f in files:
            try:
                with fitz.open(f) as doc:
                    content = ""
                    for page in doc:
                        content += page.get_text()

                    content_clean = Util.remove_accents(content).upper()

                    if search_term in content_clean:
                        # Aquí aplicamos la lógica del parámetro
                        target = f.parent if return_parent else f
                        results.add(target)
                        
            except Exception as e:
                logging.error(f"Error leyendo {f}: {e}")

        return list(results)

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

    def verify_file_in_dirs(
        self,
        prefixes: Union[str, List[str]],
        skip: List[Path] = None,
        target_dirs: List[Path] = None,
    ) -> List[Path]:
        """
        Verifica la existencia de archivos con ciertos prefijos.

        :param prefixes: Prefijo o lista de prefijos a buscar.
        :param skip: Lista de objetos Path que deben ignorarse.
        :param target_dirs: Lista de directorios específicos a revisar.
                            Si es None, busca en todos los subdirectorios de base_path.
        """
        missing_invoice_dirs = []
        skip_set = set(skip) if skip is not None else set()

        # 1. Definimos sobre qué vamos a iterar
        # Si no hay target_dirs, usamos rglob("*") sobre el base_path
        if target_dirs is not None:
            dirs_to_scan = target_dirs
        else:
            # Filtramos para que rglob solo nos de directorios inicialmente
            dirs_to_scan = [p for p in self.base_path.rglob("*") if p.is_dir()]

        # 2. Normalizamos criterios de búsqueda
        if isinstance(prefixes, list):
            search_criteria = tuple(p.upper() for p in prefixes)
        else:
            search_criteria = prefixes.upper()

        # 3. Procesamos los directorios
        for dir_path in dirs_to_scan:
            # Solo procesamos si es directorio y no está en la lista de ignorados
            if dir_path.is_dir() and dir_path not in skip_set:

                has_invoice = any(
                    f.is_file() and f.name.upper().startswith(search_criteria)
                    for f in dir_path.iterdir()
                )

                if not has_invoice:
                    missing_invoice_dirs.append(dir_path)

        return missing_invoice_dirs

    def validate_file_naming_structure(
        self, valid_prefixes: List[str], suffix: str, nit: str
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

        files = self.get_files_by_extension("pdf")
        for f in files:
            if not pattern.match(f.name):
                invalid_files.append(f)

        return invalid_files

    def rename_files_by_prefix_map(self, prefix_replacements: dict, target_files: List[Path] = None) -> int:
        """
        Renombra archivos basados en un mapa de prefijos, procesando directamente
        una lista de objetos Path proporcionada.
        """
        count = 0
        
        # Si no hay archivos, terminamos temprano
        if not target_files:
            return count

        for f in target_files:
            # Verificamos que sea un archivo y que exista
            if f.is_file():
                # Separamos el prefijo (ej: 'PDX' de 'PDX_890701078...')
                parts = f.name.split("_", 1)
                
                if len(parts) > 1:
                    current_prefix = parts[0].upper()
                    
                    # Si el prefijo está en nuestro diccionario de reemplazos
                    if current_prefix in prefix_replacements:
                        new_prefix = prefix_replacements[current_prefix]
                        new_name = f"{new_prefix}_{parts[1]}"
                        new_path = f.with_name(new_name)
                        
                        try:
                            f.rename(new_path)
                            # logging.info(f"Renombrado: {f.name} -> {new_name}")
                            count += 1
                        except Exception as e:
                            logging.error(f"No se pudo renombrar {f}: {e}")
            else:
                logging.warning(f"La ruta no es un archivo válido: {f}")
                
        return count

    def list_dirs_with_anular(self) -> List[Path]:
        """Retorna una lista de directorios que contienen 'ANULAR' en su nombre."""
        return [
            d
            for d in self.base_path.iterdir()
            if d.is_dir() and "ANULAR" in d.name.upper()
        ]
    

    def has_cufe(self, file_path: Path) -> bool:
        """
        Valida la existencia de un código CUFE válido dentro del PDF.
        Retorna True si encuentra un patrón de +64 caracteres hexadecimales.
        """
        try:
            with fitz.open(file_path) as doc:
                # Extraemos el texto de todas las páginas
                content = ""
                for page in doc:
                    content += page.get_text()

            # 1. Limpiamos espacios y saltos de línea por si el CUFE está cortado
            # El CUFE son +64 caracteres hexadecimales seguidos.
            clean_content = re.sub(r"\s+", "", content)

            # 2. Definimos el patrón: +64 caracteres de [0-9a-fA-F]
            cufe_pattern = r"[0-9a-fA-F]{64,}"

            # Buscamos el patrón en el contenido limpio
            match = re.search(cufe_pattern, clean_content)

            if match:
                # logging.info(f"CUFE encontrado en {file_path.name}")
                return True

            # logging.warning(f"No se encontró un CUFE válido en {file_path.name}")
            return False

        except Exception as e:
            logging.error(f"Error procesando {file_path}: {e}")
            return False

    def get_invoices_missing_cufe(self, file_paths: list[Path]) -> list[Path]:
        # Retorna la lista filtrada: "Dame el archivo si NO tiene cufe"
        return [path for path in file_paths if not self.has_cufe(path)]

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

    def copy_or_move_folders(
        self, 
        folder_names: List[str], 
        source_path: Union[str, Path], 
        destination_path: Union[str, Path], 
        action: Literal["copy", "move"] = "copy"
    ) -> dict:
        """
        Copia o mueve carpetas desde la carpeta origen a la carpeta destino.
        
        :param folder_names: Lista de nombres de carpetas a copiar/mover.
        :param source_path: Ruta de origen donde se encuentran las carpetas.
        :param destination_path: Ruta donde se copiarán/moverán las carpetas.
        :param action: Acción a realizar: "copy" para copiar o "move" para mover.
        :return: Diccionario con estadísticas: {'success': cantidad, 'failed': cantidad, 'not_found': cantidad}
        """
        source_path = Path(source_path)
        destination_path = Path(destination_path)
        
        results = {
            'success': 0,
            'failed': 0,
            'not_found': 0,
            'errors': []
        }
        
        # Validar que la carpeta origen existe
        if not source_path.is_dir():
            logging.error(f"La ruta de origen no existe o no es una carpeta: {source_path}")
            results['errors'].append(f"Ruta de origen inválida: {source_path}")
            return results
        
        # Crear la carpeta destino si no existe
        try:
            destination_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"No se pudo crear la carpeta destino {destination_path}: {e}")
            results['errors'].append(f"No se pudo crear carpeta destino: {e}")
            return results
        
        # Procesar cada carpeta de la lista
        for folder_name in folder_names:
            source_folder = source_path / folder_name
            destination_folder = destination_path / folder_name
            
            # Verificar si la carpeta origen existe
            if not source_folder.is_dir():
                logging.warning(f"La carpeta no existe: {source_folder}")
                results['not_found'] += 1
                results['errors'].append(f"Carpeta no encontrada: {folder_name}")
                continue
            
            try:
                if action.lower() == "copy":
                    # Copiar la carpeta completa
                    if destination_folder.exists():
                        logging.warning(f"La carpeta destino ya existe, se omite: {destination_folder}")
                        results['failed'] += 1
                        results['errors'].append(f"Carpeta destino ya existe: {folder_name}")
                    else:
                        shutil.copytree(source_folder, destination_folder)
                        logging.info(f"Carpeta copiada: {source_folder} -> {destination_folder}")
                        results['success'] += 1
                        
                elif action.lower() == "move":
                    # Mover la carpeta completa
                    if destination_folder.exists():
                        logging.warning(f"La carpeta destino ya existe, se omite: {destination_folder}")
                        results['failed'] += 1
                        results['errors'].append(f"Carpeta destino ya existe: {folder_name}")
                    else:
                        shutil.move(str(source_folder), str(destination_folder))
                        logging.info(f"Carpeta movida: {source_folder} -> {destination_folder}")
                        results['success'] += 1
                else:
                    raise ValueError(f"Acción no válida: {action}. Use 'copy' o 'move'")
                    
            except Exception as e:
                logging.error(f"Error al procesar {folder_name}: {e}")
                results['failed'] += 1
                results['errors'].append(f"Error en {folder_name}: {str(e)}")
        
        return results
