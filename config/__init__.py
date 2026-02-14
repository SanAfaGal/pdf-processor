"""Configuration: settings (env validation) and data (hospitals, mappings)."""
from config.settings import Settings
from config.hospitals import HOSPITALS
from config.mappings import ADMINISTRADORAS, CONTRATOS

__all__ = ["Settings", "HOSPITALS", "ADMINISTRADORAS", "CONTRATOS"]
