"""
Sustituye los NOMBRES de residencia por su CODIGO_RESIDENCIA en Leads_Contacts.csv,
usando maestro_residencias.csv como diccionario nombre -> codigo.

Requiere en la misma carpeta:
    - Leads_Contacts.csv          (separador ';')
    - maestro_residencias.csv     (separador ',', ya reparado de mojibake)

Genera:
    - Leads_Contacts.csv          (sobrescrito, con copia de seguridad .bak)
    - un informe por consola de valores no encontrados (deberia ser 0)
"""

import shutil
import pandas as pd

LEADS_PATH   = "Leads_Contacts.csv"
MAESTRO_PATH = "maestro_residencias.csv"

COLUMNAS_RESIDENCIA = [
    "Residencias_actual_corregido",
    "Residencias_interes_corregido",
    "Residencia escogida",
]

NO_CONVERTIR = {"", "Ninguno", "Sin info", "Cualquiera", "Sin información"}

maestro = pd.read_csv(MAESTRO_PATH, sep=",", dtype=str, encoding="utf-8").fillna("")
maestro["nombre_residencia"] = maestro["nombre_residencia"].str.strip()
maestro["codigo_residencia"] = maestro["codigo_residencia"].str.strip()

nombre_a_codigo = dict(zip(maestro["nombre_residencia"], maestro["codigo_residencia"]))

df = pd.read_csv(LEADS_PATH, sep=";", dtype=str, low_memory=False)

import unicodedata

def limpiar(s):
    if not isinstance(s, str):
        return s
    try:
        s = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    s = s.replace("\xad", "").replace("\xa0", " ")
    s = unicodedata.normalize("NFC", s)
    return " ".join(s.split())

maestro = pd.read_csv(MAESTRO_PATH, sep=",", dtype=str, encoding="utf-8").fillna("")
maestro["codigo_residencia"] = maestro["codigo_residencia"].str.strip()

nombre_a_codigo = {}
for _, r in maestro.iterrows():
    k = limpiar(r["nombre_residencia"])
    if k:
        nombre_a_codigo[k] = r["codigo_residencia"]

def convertir_columna(serie):
    def _map(valor):
        if not isinstance(valor, str):
            return valor
        v = limpiar(valor)
        if v in NO_CONVERTIR:
            return valor
        return nombre_a_codigo.get(v, valor)
    return serie.map(_map)

no_encontrados = {}
columnas_presentes = [c for c in COLUMNAS_RESIDENCIA if c in df.columns]

for col in columnas_presentes:
    original = df[col].astype("string").fillna("").map(limpiar)
    faltan = sorted(
        v for v in original.unique()
        if v and v not in NO_CONVERTIR and v not in nombre_a_codigo
    )
    if faltan:
        no_encontrados[col] = faltan
    df[col] = convertir_columna(df[col])

print("Columnas de residencia convertidas:", columnas_presentes)
if no_encontrados:
    print("\nATENCION: valores que NO estaban en maestro (se han dejado sin convertir):")
    for col, vals in no_encontrados.items():
        print(f"  [{col}] {len(vals)} valores:")
        for v in vals:
            print("     ", repr(v))
else:
    print("\nTodos los nombres de residencia se han convertido a codigo correctamente.")

shutil.copyfile(LEADS_PATH, LEADS_PATH + ".bak")
df.to_csv(LEADS_PATH, sep=";", index=False, encoding="utf-8")
print(f"\nGuardado {LEADS_PATH} ({len(df)} filas). Copia de seguridad en {LEADS_PATH}.bak")
