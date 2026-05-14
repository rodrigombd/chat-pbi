"""
Análisis de drivers — Random Forest sobre dimensiones del modelo.

Objetivo: dada la última consulta del usuario, identificar qué variables
explican la diferencia entre dos cohortes (típicamente dos cursos académicos).

Estrategia:
  1. Detectar las dos cohortes a comparar a partir de `last_user_query`.
  2. Construir un dataset a nivel de registro con target binario
       1 = pertenece a la cohorte "nueva", 0 = cohorte "vieja"
     (técnica de drift-detection / A-vs-B explanation).
  3. Entrenar un RandomForestClassifier sobre las dimensiones disponibles.
  4. Extraer feature_importances_ y mapearlas a variables originales.
  5. Para las top features, hacer breakdown univariado mostrando qué valores
     concretos han cambiado y en qué magnitud.
  6. Devolver markdown con KPIs de cabecera + ranking de drivers + lectura.

Variables globales esperadas en el entorno Pyodide:
  - leads_contacts (pd.DataFrame)
  - last_user_query (str)
"""

import re
import numpy as np
import pandas as pd

# ===================== CONFIGURACIÓN =====================

# Dimensiones categóricas que el RF puede usar como features.
# IMPORTANTE: NO incluir `Curso` ni `Curso_corregido` aquí porque el target
# binario se construye a partir del curso (sería información del propio
# target y dominaría las importancias artificialmente).
CANDIDATE_DIMENSIONS = [
    "Tipo de registro",
    "Particular o Grupo",
    "Origen_Agrupado",
    "Fuente_Agrupada",
    "Ciudad_deinteres_corregido",
    "Ciudad_actual_corregido",
    "Residencias_interes_corregido",
    "Residencias_actual_corregido",
    "Residencia escogida",
    "Mes creación",
]

# Columna ID para conteos únicos.
ID_COL = "Correo electrónico"

# Columna que define el "curso" (cohorte temporal por defecto).
COURSE_COL = "Curso"

# Parámetros del Random Forest (modestos para Pyodide).
RF_PARAMS = dict(
    n_estimators=120,
    max_depth=8,
    min_samples_leaf=20,
    random_state=42,
    n_jobs=1,
)

# Cursos por defecto si la consulta no menciona ninguno.
COURSE_DEFAULTS = ("2024/2025", "2025/2026")

# Número de drivers a reportar.
TOP_K_DRIVERS = 5

# Para el breakdown univariado, mínimo de registros para considerar relevante.
MIN_RECORDS_FOR_BREAKDOWN = 30

# ===================== UTILIDADES =====================

try:
    query_text = str(last_user_query) if last_user_query is not None else ""
except NameError:
    query_text = ""


def detectar_cursos(texto, default=COURSE_DEFAULTS):
    """Extrae cursos del tipo 'YYYY/YYYY' o 'YY/YY' de la consulta del usuario.
    Si solo hay uno, asume comparación contra el inmediatamente anterior.
    Si no hay ninguno, devuelve el par por defecto."""
    patron = r"\b(20\d{2}|\d{2})\s*[-/]\s*(20\d{2}|\d{2})\b"
    cursos = []
    for ini, fin in re.findall(patron, texto):
        if len(ini) == 2:
            ini = "20" + ini
        if len(fin) == 2:
            fin = "20" + fin
        cursos.append(f"{ini}/{fin}")

    if not cursos:
        anios = re.findall(r"\b(20\d{2})\b", texto)
        for a in anios:
            n = int(a)
            cursos.append(f"{n}/{n+1}")

    if len(cursos) >= 2:
        cursos = sorted(set(cursos))
        return cursos[0], cursos[-1]
    if len(cursos) == 1:
        unico = cursos[0]
        try:
            n = int(unico.split("/")[0])
            return f"{n-1}/{n}", unico
        except Exception:
            return default
    return default


def fmt_num(n):
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def fmt_pct(p, dec=2):
    if p is None or pd.isna(p):
        return "—"
    return f"{p*100:+.{dec}f}%"


def fmt_pct_abs(p, dec=2):
    if p is None or pd.isna(p):
        return "—"
    return f"{p*100:.{dec}f}%"


def contar_leads(df, curso=None):
    f = df[df["Tipo de registro"] == "Leads"]
    if curso is not None:
        f = f[f[COURSE_COL] == curso]
    return int(f[ID_COL].nunique()) if not f.empty else 0


def contar_contacts(df, curso=None):
    f = df[
        (df["Tipo de registro"] == "Contacts") &
        (df["Particular o Grupo"] == "Particular")
    ]
    if curso is not None:
        f = f[f[COURSE_COL] == curso]
    return int(f[ID_COL].nunique()) if not f.empty else 0


def calcular_cr(contacts, leads):
    denom = contacts + leads
    return contacts / denom if denom > 0 else 0.0


def var_pct(nuevo, viejo):
    if viejo is None or viejo == 0:
        return None
    return (nuevo / viejo) - 1.0


# ===================== ENTRENAR RANDOM FOREST =====================

def entrenar_rf(df_completo, curso_1, curso_2, dimensiones):
    """Entrena un RandomForestClassifier para distinguir registros del curso_2
    de los del curso_1. Devuelve (importancias_por_dimension, n_total)."""
    from sklearn.ensemble import RandomForestClassifier

    # Filtrar a las dos cohortes.
    df = df_completo[df_completo[COURSE_COL].isin([curso_1, curso_2])].copy()
    if df.empty:
        return pd.DataFrame(), 0

    # Quedarse solo con dimensiones presentes en el df.
    dims = [d for d in dimensiones if d in df.columns and d != COURSE_COL]
    if not dims:
        return pd.DataFrame(), 0

    # Rellenar nulos y forzar a string para get_dummies.
    X_raw = df[dims].copy()
    for c in X_raw.columns:
        X_raw[c] = X_raw[c].fillna("Sin info").astype(str)

    # One-hot encoding con prefijo = nombre de la dimensión original.
    # max_categories implícito via drop_first=False; controlamos cardinalidad antes.
    # Para dimensiones muy cardinales, conservamos solo las top-N por frecuencia.
    MAX_CAT_PER_DIM = 25
    for c in dims:
        vc = X_raw[c].value_counts()
        if len(vc) > MAX_CAT_PER_DIM:
            top = set(vc.head(MAX_CAT_PER_DIM).index)
            X_raw[c] = X_raw[c].where(X_raw[c].isin(top), other="Otros (cola)")

    X = pd.get_dummies(X_raw, prefix_sep="||")
    y = (df[COURSE_COL] == curso_2).astype(int).values

    if X.shape[1] == 0 or len(np.unique(y)) < 2:
        return pd.DataFrame(), len(df)

    rf = RandomForestClassifier(**RF_PARAMS)
    rf.fit(X.values, y)

    # Acumular importancias por dimensión original.
    importancias = pd.Series(rf.feature_importances_, index=X.columns)
    por_dim = {}
    for col, imp in importancias.items():
        dim_original = col.split("||")[0]
        por_dim[dim_original] = por_dim.get(dim_original, 0.0) + float(imp)

    df_imp = (
        pd.DataFrame({"dimension": list(por_dim.keys()),
                      "importancia": list(por_dim.values())})
        .sort_values("importancia", ascending=False)
        .reset_index(drop=True)
    )
    return df_imp, len(df)


# ===================== BREAKDOWN UNIVARIADO =====================

def breakdown_por_dimension(df_completo, dim, curso_1, curso_2,
                            min_total=MIN_RECORDS_FOR_BREAKDOWN):
    """Para una dimensión, devuelve un DataFrame con conteos de Leads y
    Contacts y deltas entre las dos cohortes."""
    if dim not in df_completo.columns:
        return pd.DataFrame()

    df = df_completo[df_completo[COURSE_COL].isin([curso_1, curso_2])].copy()
    if df.empty:
        return pd.DataFrame()

    df[dim] = df[dim].fillna("Sin info").astype(str)

    leads_g = (
        df[df["Tipo de registro"] == "Leads"]
        .groupby([dim, COURSE_COL])[ID_COL].nunique()
        .unstack(COURSE_COL, fill_value=0)
    )
    contacts_g = (
        df[(df["Tipo de registro"] == "Contacts") &
           (df["Particular o Grupo"] == "Particular")]
        .groupby([dim, COURSE_COL])[ID_COL].nunique()
        .unstack(COURSE_COL, fill_value=0)
    )

    idx = leads_g.index.union(contacts_g.index)
    out = pd.DataFrame(index=idx)
    out.index.name = dim
    for c in (curso_1, curso_2):
        out[f"Leads_{c}"] = leads_g.reindex(idx).get(c, pd.Series(0, index=idx)).fillna(0).astype(int)
        out[f"Contacts_{c}"] = contacts_g.reindex(idx).get(c, pd.Series(0, index=idx)).fillna(0).astype(int)

    out["Delta_Leads"] = out[f"Leads_{curso_2}"] - out[f"Leads_{curso_1}"]
    out["Delta_Contacts"] = out[f"Contacts_{curso_2}"] - out[f"Contacts_{curso_1}"]

    denom_1 = out[f"Contacts_{curso_1}"] + out[f"Leads_{curso_1}"]
    denom_2 = out[f"Contacts_{curso_2}"] + out[f"Leads_{curso_2}"]
    out[f"CR_{curso_1}"] = np.where(denom_1 > 0, out[f"Contacts_{curso_1}"] / denom_1, 0.0)
    out[f"CR_{curso_2}"] = np.where(denom_2 > 0, out[f"Contacts_{curso_2}"] / denom_2, 0.0)
    out["Delta_CR_pp"] = (out[f"CR_{curso_2}"] - out[f"CR_{curso_1}"]) * 100

    # Filtrar valores con volumen mínimo.
    total = denom_1 + denom_2
    out = out[total >= min_total]

    return out.reset_index()


# ===================== EJECUCIÓN =====================

curso_1, curso_2 = detectar_cursos(query_text)

# KPIs de cabecera.
leads_1 = contar_leads(leads_contacts, curso_1)
leads_2 = contar_leads(leads_contacts, curso_2)
contacts_1 = contar_contacts(leads_contacts, curso_1)
contacts_2 = contar_contacts(leads_contacts, curso_2)
cr_1 = calcular_cr(contacts_1, leads_1)
cr_2 = calcular_cr(contacts_2, leads_2)

delta_leads = leads_2 - leads_1
delta_contacts = contacts_2 - contacts_1
delta_cr_pp = (cr_2 - cr_1) * 100
var_leads = var_pct(leads_2, leads_1)
var_contacts = var_pct(contacts_2, contacts_1)
var_cr = var_pct(cr_2, cr_1)

# Random Forest.
df_imp, n_registros = entrenar_rf(leads_contacts, curso_1, curso_2, CANDIDATE_DIMENSIONS)

# ===================== CONSTRUIR MARKDOWN =====================

md = []
md.append(f"## **Análisis de drivers · {curso_1} → {curso_2}**\n")
md.append(f"*Consulta original: «{query_text if query_text else 'análisis por defecto'}»*\n")

md.append("### KPIs de cabecera\n")
md.append(
    f"- **Leads:** {fmt_num(leads_1)} → {fmt_num(leads_2)} "
    f"(**{'+' if delta_leads >= 0 else ''}{fmt_num(delta_leads)}**, {fmt_pct(var_leads)})"
)
md.append(
    f"- **Contacts particulares:** {fmt_num(contacts_1)} → {fmt_num(contacts_2)} "
    f"(**{'+' if delta_contacts >= 0 else ''}{fmt_num(delta_contacts)}**, {fmt_pct(var_contacts)})"
)
signo = "+" if delta_cr_pp >= 0 else ""
md.append(
    f"- **Conversion Rate:** {fmt_pct_abs(cr_1)} → {fmt_pct_abs(cr_2)} "
    f"(**{signo}{delta_cr_pp:.2f} pp**, {fmt_pct(var_cr)})\n"
)

# ----- Sección Random Forest -----
md.append("### Drivers detectados por Random Forest\n")
md.append(
    f"*Modelo entrenado para distinguir registros de {curso_2} frente a {curso_1}. "
    f"Dataset: {fmt_num(n_registros)} registros.*\n"
)

if df_imp.empty:
    md.append("- *No ha sido posible entrenar el modelo (datos insuficientes o dimensiones no disponibles).*\n")
else:
    top_drivers = df_imp.head(TOP_K_DRIVERS)
    total_imp = top_drivers["importancia"].sum()

    md.append("| # | Dimensión | Importancia | % del top |")
    md.append("|---|---|---|---|")
    for i, row in top_drivers.iterrows():
        pct_local = (row["importancia"] / total_imp * 100) if total_imp > 0 else 0
        md.append(
            f"| {i+1} | **{row['dimension']}** | "
            f"{row['importancia']:.4f} | {pct_local:.1f}% |"
        )
    md.append("")

    # ----- Breakdown de los top 3 drivers -----
    md.append(f"### Breakdown de los {min(3, len(top_drivers))} drivers principales\n")

    for i, row in top_drivers.head(3).iterrows():
        dim = row["dimension"]
        md.append(f"#### {i+1}. {dim} *(importancia: {row['importancia']:.4f})*\n")

        bd = breakdown_por_dimension(leads_contacts, dim, curso_1, curso_2)
        if bd.empty:
            md.append("- *Sin volumen suficiente para desglose univariado.*\n")
            continue

        # Top movimientos por delta de leads (positivos y negativos).
        bd_sorted = bd.reindex(bd["Delta_Leads"].abs().sort_values(ascending=False).index)
        top_movs = bd_sorted.head(5)

        md.append(
            f"| Valor | Leads {curso_1} → {curso_2} | Δ Leads | "
            f"CR {curso_1} → {curso_2} | Δ CR (pp) |"
        )
        md.append("|---|---|---|---|---|")
        for _, r in top_movs.iterrows():
            val = r[dim] if pd.notna(r[dim]) else "Sin info"
            dl = int(r["Delta_Leads"])
            signo_dl = "+" if dl >= 0 else ""
            cr_old = r[f"CR_{curso_1}"]
            cr_new = r[f"CR_{curso_2}"]
            dcr = r["Delta_CR_pp"]
            signo_dcr = "+" if dcr >= 0 else ""
            md.append(
                f"| **{val}** | "
                f"{fmt_num(r[f'Leads_{curso_1}'])} → {fmt_num(r[f'Leads_{curso_2}'])} | "
                f"**{signo_dl}{fmt_num(dl)}** | "
                f"{fmt_pct_abs(cr_old)} → {fmt_pct_abs(cr_new)} | "
                f"{signo_dcr}{dcr:.2f} |"
            )
        md.append("")

# ----- Lectura narrativa -----
md.append("### Lectura\n")

partes = []
if not df_imp.empty:
    top1 = df_imp.iloc[0]["dimension"]
    partes.append(f"la variable que mejor explica el cambio entre {curso_1} y {curso_2} es **{top1}**")
    if len(df_imp) > 1:
        top2 = df_imp.iloc[1]["dimension"]
        partes.append(f"seguida de **{top2}**")

if delta_cr_pp < -0.5:
    intro = f"El CR ha caído **{abs(delta_cr_pp):.2f} pp**"
elif delta_cr_pp > 0.5:
    intro = f"El CR ha subido **{delta_cr_pp:.2f} pp**"
else:
    intro = f"El CR se mantiene relativamente estable ({signo}{delta_cr_pp:.2f} pp)"

if partes:
    md.append(f"{intro}. Según el Random Forest, " + " y ".join(partes) + ".")
else:
    md.append(f"{intro}. No se han detectado drivers claros en las dimensiones analizadas.")

# Recomendación según signo del cambio.
if not df_imp.empty:
    top1 = df_imp.iloc[0]["dimension"]
    if delta_cr_pp < -0.5:
        md.append(
            f"\n**Recomendación:** investigar en detalle la dimensión **{top1}** "
            f"para entender qué valores concretos están deteriorando el embudo. "
            f"Revisar la tabla de breakdown anterior."
        )
    elif delta_cr_pp > 0.5:
        md.append(
            f"\n**Recomendación:** identificar los valores de **{top1}** que están "
            f"empujando la mejora y reforzar la inversión o los procesos asociados."
        )
    else:
        md.append(
            f"\n**Recomendación:** aunque el CR global no varía mucho, **{top1}** "
            f"sí presenta movimientos internos relevantes. Vale la pena vigilarla."
        )

md.append(
    "\n---\n"
    "*Metodología: clasificador binario (curso reciente vs anterior) sobre "
    "one-hot encoding de las dimensiones del modelo. "
    "Las importancias agregan la contribución de cada dimensión sumando "
    "las importancias de sus categorías. "
    "Las dimensiones con cardinalidad > 25 se truncan a las 25 categorías "
    "más frecuentes para evitar overfitting.*"
)

resultado = "\n".join(md)
