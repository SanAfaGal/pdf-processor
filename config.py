# config.py
STAGING_PATH = r"C:\Users\sanaf\Desktop\Carpeta compartida\26-31 STAGE"
FINAL_PATH = r"C:\Users\sanaf\Desktop\Carpeta compartida\26-31 FINAL"
REPORT_PATH = (
    r"C:\Users\sanaf\Desktop\Carpeta compartida\Informe_Sihos_03-02-26-11_10_51.xlsx"
)

SUFFIX = "HSL"
NIT_DEFAULT = "890701078"

COLUMNS_TO_USE = [
    "Doc",
    "No Doc",
    "Documento",
    "Numero",
    "Paciente",
    "Administradora",
    "Contrato",
    "Operario",
]

FILE_PREFIXES = {
    "FACTURA": "FEV",
    "FIRMA": "CRC",
    "VALIDACION": "OPF",
    "HISTORIA": ["EPI", "HEV", "HAO", "HAU"],
    "RESULTADOS": "PDX",
    "BITACORA": "TAP",
    "RESOLUCION": "LDP",
    "MEDICAMENTOS": "HAM",
    "AUTORIZACION": "PDE",
}


PREFIX_REPLACEMENTS = {
    "OPD": "OPF",
    "FVE": "FEV",
    "FOPF": "OPF",
    "OPG": "OPF",
    "FVS": "FEV",
    "FEPI": "EPI",
    "PDE": "PDX",
    "HVE": "HEV",
}
