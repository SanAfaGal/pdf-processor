"""
Normalize PDF filenames to standard: PREFIX_NIT_SUFFIX{6_DIGITS}.pdf.
Uses folder/file name to extract HSL id and prefix map for corrections.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.models import NormalizationReport


class FileNormalizer:
    """
    Normalizes PDF names to {PREFIX}_{NIT}_{SUFFIX}{6_DIGITS}.pdf.
    Validates prefix against allowed list and applies MISNAMED_FIXER_MAP.
    """

    def __init__(
        self,
        nit: str,
        valid_prefixes: List[str],
        suffix_const: str,
        prefix_map: Dict[str, str],
    ) -> None:
        self.nit = nit
        self.valid_prefixes = valid_prefixes
        self.suffix_const = suffix_const
        self.prefix_map = prefix_map

    def _extract_id_from_path(self, file_path: Path) -> str:
        """Extract 6-digit ID from parent folder name or file name (HSL pattern)."""
        folder_match = re.search(
            r"HSL_?(\d{6})", file_path.parent.name, re.IGNORECASE
        )
        if folder_match:
            return folder_match.group(1)
        file_match = re.search(
            r"HSL[-_ ]?(\d{5,7})", file_path.name, re.IGNORECASE
        )
        if file_match:
            digits = file_match.group(1)
            return digits.zfill(6)[:6]
        return ""

    def _sanitize_prefix(self, raw_name: str) -> str:
        """Extract leading letters and apply prefix_map."""
        match = re.match(r"^([a-zA-Z]+)", raw_name)
        if not match:
            return ""
        prefix = match.group(1).upper()
        return self.prefix_map.get(prefix, prefix)

    def normalize_name(self, file_path: Path) -> Tuple[Optional[str], str]:
        """
        Build canonical name for file. Returns (new_name, reason).
        new_name is None if invalid.
        """
        file_id = self._extract_id_from_path(file_path)
        if not file_id:
            return None, "No se pudo encontrar un ID HSL de 6 dígitos válido."
        prefix = self._sanitize_prefix(file_path.name)
        if prefix not in self.valid_prefixes:
            return None, f"Prefijo '{prefix}' no reconocido o inválido."
        clean_name = f"{prefix}_{self.nit}_{self.suffix_const}{file_id}.pdf"
        return clean_name, "Ok"

    def run(self, files: List[Path]) -> List[NormalizationReport]:
        """Normalize each file; return list of NormalizationReport (SUCCESS/REJECTED/ERROR/SKIPPED)."""
        reports: List[NormalizationReport] = []
        for f in files:
            if not f.is_file():
                continue
            try:
                new_name, reason = self.normalize_name(f)
                if not new_name:
                    reports.append(
                        NormalizationReport(str(f), "N/A", "REJECTED", reason)
                    )
                    continue
                if f.name == new_name:
                    reports.append(
                        NormalizationReport(str(f), new_name, "SKIPPED", "Ya correcto")
                    )
                    continue
                target_path = f.with_name(new_name)
                if target_path.exists():
                    reports.append(
                        NormalizationReport(
                            str(f), new_name, "REJECTED", "El destino ya existe"
                        )
                    )
                else:
                    f.rename(target_path)
                    reports.append(
                        NormalizationReport(
                            str(f), new_name, "SUCCESS", "Renombrado exitoso"
                        )
                    )
            except Exception as e:
                reports.append(
                    NormalizationReport(str(f), "N/A", "ERROR", str(e))
                )
        return reports
