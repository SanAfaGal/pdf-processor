import logging
from pathlib import Path
from typing import Optional
import pandas as pd
import unicodedata

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class Util:
    @staticmethod
    def save_report(
        df: pd.DataFrame, default_name: str, custom_path: Optional[Path] = None
    ):
        """
        Generic helper to save DataFrames as Excel or CSV based on extension.
        """
        if df.empty:
            logging.info(f"✨ No records to save for {default_name}.")
            return

        file_to_save = custom_path or Path(default_name)

        try:
            if file_to_save.suffix.lower() == ".csv":
                # utf-8-sig permite que Excel reconozca tildes y caracteres especiales
                df.to_csv(file_to_save, index=False, sep=";", encoding="utf-8-sig")
            else:
                # Por defecto guarda en Excel si no es CSV
                file_to_save = file_to_save.with_suffix(".xlsx")
                df.to_excel(file_to_save, index=False)

            logging.info(f"✅ Report saved: {len(df)} records in {file_to_save}")
        except Exception as e:
            logging.error(f"❌ Error saving report {file_to_save}: {e}")

    @staticmethod
    def extract_valid_prefixes(file_prefixes_dict: dict) -> list:
        """Extracts valid prefixes from a dictionary that may contain strings or lists."""
        valid_prefixes_list = []
        for val in file_prefixes_dict.values():
            if isinstance(val, list):
                valid_prefixes_list.extend(val)
            else:
                valid_prefixes_list.append(val)
        return valid_prefixes_list

    @staticmethod
    def remove_accents(text: str) -> str:
        """Elimina acentos y tildes de una cadena de texto."""
        if not text:
            return ""
        # Normaliza a NFD (Normalization Form Decomposition)
        # Esto separa la letra de su acento
        text = unicodedata.normalize('NFD', text)
        # Filtra y mantiene solo los caracteres que no son marcas de acento (Mnemonic)
        return "".join(c for c in text if unicodedata.category(c) != 'Mn')
    
    @staticmethod
    def get_list_from_file(file_name : str):
        with open(file_name, "r", encoding="UTF-8") as file:
            return [line.strip() for line in file]