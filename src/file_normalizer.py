import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class NormalizationReport:
    original_path: str
    new_name: str
    status: str  # SUCCESS, REJECTED, ERROR
    reason: str

class FileNormalizer:
    """
    Normaliza archivos PDF bajo el estándar: {PREFIX}_{NIT}_{SUFFIX}{6_DIGITS}.pdf
    Aplica principios de limpieza profunda y validación cruzada con el directorio.
    """

    def __init__(self, nit: str, valid_prefixes: List[str], suffix_const: str, prefix_map : dict):
        self.nit = nit
        self.valid_prefixes = valid_prefixes
        self.suffix_const = suffix_const
        self.prefix_map = prefix_map

    def _extract_id_from_path(self, file_path: Path) -> str:
        """
        Extrae los 6 dígitos buscando en el nombre del archivo y en la carpeta padre.
        Prioriza el nombre de la carpeta si el archivo tiene errores (ej. 5 o 7 dígitos).
        """
        # Buscar en el nombre de la carpeta (Fuente de verdad)
        folder_match = re.search(r"HSL_?(\d{6})", file_path.parent.name, re.IGNORECASE)
        if folder_match:
            return folder_match.group(1)
            
        # Si no está en la carpeta, buscar en el archivo
        file_match = re.search(r"HSL[-_ ]?(\d{5,7})", file_path.name, re.IGNORECASE)
        if file_match:
            digits = file_match.group(1)
            return digits.zfill(6)[:6] # Normalizar a 6 dígitos
            
        return ""

    def _sanitize_prefix(self, raw_name: str) -> str:
        """Limpia y mapea el prefijo inicial."""
        # Extraer las letras iniciales antes del primer separador
        match = re.match(r"^([a-zA-Z]+)", raw_name)
        if not match:
            return ""
            
        prefix = match.group(1).upper()
        # Aplicar mapeo si existe, si no, retornar el original si es válido
        return self.prefix_map.get(prefix, prefix)

    def normalize_name(self, file_path: Path) -> Tuple[Optional[str], str]:
        """
        Intenta construir el nombre correcto. 
        Retorna (nuevo_nombre, razon).
        """
        raw_name = file_path.name
        
        # 1. Extraer ID (6 dígitos)
        file_id = self._extract_id_from_path(file_path)
        if not file_id:
            return None, "No se pudo encontrar un ID HSL de 6 dígitos válido."

        # 2. Extraer y Normalizar Prefijo
        prefix = self._sanitize_prefix(raw_name)
        if prefix not in self.valid_prefixes:
            return None, f"Prefijo '{prefix}' no reconocido o inválido."

        # 3. Construir nombre final
        clean_name = f"{prefix}_{self.nit}_{self.suffix_const}{file_id}.pdf"
        return clean_name, "Ok"

    def run(self, files: List[Path]) -> List[NormalizationReport]:
        reports = []
        for f in files:
            if not f.is_file(): continue
            
            try:
                new_name, reason = self.normalize_name(f)
                
                if new_name:
                    # Evitar renombrar si ya está bien (Case sensitive check)
                    if f.name == new_name:
                        continue
                        
                    target_path = f.with_name(new_name)
                    
                    # Manejo de colisiones (ej. archivo (2).pdf -> archivo.pdf)
                    if target_path.exists():
                        reports.append(NormalizationReport(str(f), new_name, "REJECTED", "El destino ya existe"))
                    else:
                        f.rename(target_path)
                        reports.append(NormalizationReport(str(f), new_name, "SUCCESS", "Renombrado exitoso"))
                else:
                    reports.append(NormalizationReport(str(f), "N/A", "REJECTED", reason))
                    
            except Exception as e:
                reports.append(NormalizationReport(str(f), "N/A", "ERROR", str(e)))
                
        return reports