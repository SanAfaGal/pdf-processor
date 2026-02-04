"""Lookup tables and settings for administradoras and contracts."""

import numpy as np
from typing import Dict

# Mapping of administradoras (health insurance companies) to standardized names
ADMINISTRADORAS: Dict[str, str] = {
    "Compensar": "Compensar",
    "Famisanar": "Famisanar",
    "Nueva EPS": "Nueva EPS",
    "Sanitas": "Sanitas",
    "Cigna": "Cigna",
    "Humana": "Humana",
    "Asmet Salud": "Asmet Salud",
    "Coomeva": "Coomeva",
    "Cafesalud": "Cafesalud",
    "SOS": "SOS",
    "Axa Colpatria": "Axa Colpatria",
    "Emssanar": "Emssanar",
    "Medimás": "Medimás",
    "Amigo": "Amigo",
    "Salud Total": "Salud Total",
    "Aliansalud": "Aliansalud",
    "Capital Salud": "Capital Salud",
    "Medial": "Medial",
    "Coomeva": "Coomeva",
    "Mutual Ser": "Mutual Ser",
    "Salud Cen": "Salud Cen",
    "SSOC": "SSOC",
    "Coosalud": "Coosalud",
    "Fondo Ganadero": "Fondo Ganadero",
    "Magisterio": "Magisterio",
}

# Mapping of contract types to standardized names
CONTRATOS: Dict[str, str] = {
    "Subsidiado": "Subsidiado",
    "Contributivo": "Contributivo",
    "Régimen Especial": "Régimen Especial",
    "Vinculado": "Vinculado",
    "Identificado": "Identificado",
    "Activo": "Activo",
    "Pensionado": "Pensionado",
    "Asegurado": "Asegurado",
    "Cotizante": "Cotizante",
    "Familiar": "Familiar",
    "Independiente": "Independiente",
    "Desempleado": "Desempleado",
    "Otro": "Otro",
    "Público": "Público",
    "Privado": "Privado",
    "Mixto": "Mixto",
    "Empleado": "Empleado",
    "Jubilado": "Jubilado",
    "Estudiante": "Estudiante",
    "Beneficiario": "Beneficiario",
    "Afiliado": "Afiliado",
    "Base": "Base",
    "Premium": "Premium",
    "Estándar": "Estándar",
    "Especial": "Especial",
}
