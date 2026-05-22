import re
import numpy as np
import pandas as pd

ID_COL = "Correo electrónico"
COURSE_COL = "Curso"


EXPLICATIVAS_POR_TIPO = {
    "Curso_corregido": [
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Ciudad_deinteres_corregido",
        "Residencias_interes_corregido",
        "Residencia escogida",
        "Ciudad_actual_corregido",
    ],

    "Curso": [
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Ciudad_deinteres_corregido",
        "Residencias_interes_corregido",
        "Residencia escogida",
        "Ciudad_actual_corregido",
    ],

    "Ciudad_deinteres_corregido": [
        "Curso_corregido",
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Residencias_interes_corregido",
        "Residencia escogida",
    ],

    "Ciudad_actual_corregido": [
        "Ciudad_deinteres_corregido",
        "Curso_corregido",
        "Origen_Agrupado",
        "Fuente_Agrupada",
    ],

    "Origen_Agrupado": [
        "Fuente_Agrupada",
        "Ciudad_deinteres_corregido",
        "Curso_corregido",
        "Residencias_interes_corregido",
    ],

    "Fuente_Agrupada": [
        "Origen_Agrupado",
        "Ciudad_deinteres_corregido",
        "Curso_corregido",
        "Residencias_interes_corregido",
    ],

    "Residencias_interes_corregido": [
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Curso_corregido",
        "Ciudad_actual_corregido",
    ],

    "Residencia escogida": [
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Curso_corregido",
        "Ciudad_actual_corregido",
    ],

    "Tipo de registro": [
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Curso_corregido",
        "Ciudad_deinteres_corregido",
        "Residencias_interes_corregido",
    ],

    "Particular o Grupo": [
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Curso_corregido",
        "Ciudad_deinteres_corregido",
    ],

    "Mes creación": [
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Ciudad_deinteres_corregido",
        "Curso_corregido",
        "Residencias_interes_corregido",
    ],

    "__default__": [
        "Curso_corregido",
        "Origen_Agrupado",
        "Fuente_Agrupada",
        "Ciudad_deinteres_corregido",
        "Residencias_interes_corregido",
        "Residencia escogida",
    ],
}


def candidatas_para_comparacion(dim_comparacion):
    """Devuelve las variables explicativas útiles cuando se compara `dim`.

    Excluye SIEMPRE la propia dimensión de comparación.
    """
    base = EXPLICATIVAS_POR_TIPO.get(
        dim_comparacion, EXPLICATIVAS_POR_TIPO["__default__"]
    )
    return [d for d in base if d != dim_comparacion]

CANDIDATE_DIMENSIONS = [
    "Tipo de registro",
    "Particular o Grupo",
    "Curso_corregido",
    "Origen_Agrupado",
    "Fuente_Agrupada",
    "Ciudad_deinteres_corregido",
    "Ciudad_actual_corregido",
    "Residencias_interes_corregido",
    "Residencias_actual_corregido",
    "Residencia escogida",
    "Mes creación",
]

RF_PARAMS = dict(
    n_estimators=120,
    max_depth=8,
    min_samples_leaf=20,
    random_state=42,
    n_jobs=1,
)

TOP_K_DRIVERS = 5
MIN_RECORDS_FOR_BREAKDOWN = 30

try:
    query_text = str(last_user_query) if last_user_query is not None else ""
except NameError:
    query_text = ""

try:
    llm_hint = llm_parsed_cohorts  # type: ignore
except NameError:
    llm_hint = None

try:
    _raw_extra = llm_extra_filters  # type: ignore
except NameError:
    _raw_extra = None

def _normalizar_filtros(raw):
    """Acepta None, lista de dicts, o un objeto convertible a lista. Devuelve
    una lista de tuplas (columna, valor) limpia."""
    if raw is None:
        return []
    try:
        if hasattr(raw, "to_py"):
            raw = raw.to_py()
    except Exception:
        pass
    out = []
    try:
        for item in raw:
            if item is None:
                continue
            if isinstance(item, dict):
                col = item.get("columna") or item.get("column") or item.get("col")
                val = item.get("valor") or item.get("value") or item.get("val")
            else:
                try:
                    col, val = item[0], item[1]
                except Exception:
                    continue
            if col and val is not None:
                out.append((str(col), str(val)))
    except Exception:
        return []
    return out

extra_filters = _normalizar_filtros(_raw_extra)


def aplicar_filtros_extra(df, filtros):
    if not filtros:
        return df
    out = df
    for col, val in filtros:
        if col in out.columns:
            out = out[out[col].astype(str) == str(val)]
    return out


def fmt_num(n):
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def fmt_pct(p, dec=2):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "—"
    return f"{p*100:+.{dec}f}%"


def fmt_pct_abs(p, dec=2):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "—"
    return f"{p*100:.{dec}f}%"


def var_pct(nuevo, viejo):
    if viejo is None or viejo == 0:
        return None
    return (nuevo / viejo) - 1.0


def _detectar_cursos(texto):
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
        return COURSE_COL, cursos[0], cursos[-1]
    if len(cursos) == 1:
        unico = cursos[0]
        try:
            n = int(unico.split("/")[0])
            return COURSE_COL, f"{n-1}/{n}", unico
        except Exception:
            return None
    return None


def _detectar_valores_dimension(texto, df, columnas_excluidas=None):
    columnas_excluidas = set(columnas_excluidas or [])
    texto_lower = texto.lower()

    mejores = []  # (dimension, [valores_encontrados])
    for dim in CANDIDATE_DIMENSIONS:
        if dim not in df.columns or dim == COURSE_COL:
            continue
        if dim in columnas_excluidas:
            continue
        valores_unicos = df[dim].dropna().astype(str).unique()
        encontrados = []
        for v in valores_unicos:
            v_str = str(v).strip()
            if len(v_str) < 3:
                continue
            if re.search(r"\b" + re.escape(v_str.lower()) + r"\b", texto_lower):
                encontrados.append(v_str)
        seen = set()
        unicos_orden = []
        for v in encontrados:
            if v.lower() not in seen:
                seen.add(v.lower())
                unicos_orden.append(v)
        if len(unicos_orden) >= 2:
            mejores.append((dim, unicos_orden))

    if not mejores:
        return None

    mejores.sort(key=lambda x: (-len(x[1]), -sum(len(v) for v in x[1])))
    dim, valores = mejores[0]
    return dim, valores[0], valores[1]


def detectar_cohortes(texto, df, hint=None, columnas_excluidas=None):
    columnas_excluidas = set(columnas_excluidas or [])

    if hint and isinstance(hint, dict):
        dim = hint.get("dimension")
        va = hint.get("valor_a")
        vb = hint.get("valor_b")
        if dim and va and vb and dim in df.columns and dim not in columnas_excluidas:
            return dim, va, vb

    if COURSE_COL not in columnas_excluidas and "Curso_corregido" not in columnas_excluidas:
        r = _detectar_cursos(texto)
        if r:
            return r

    r = _detectar_valores_dimension(texto, df, columnas_excluidas=columnas_excluidas)
    if r:
        return r

    return None


def detectar_dims_dependientes(df, dim_comparacion, candidatas, umbral_solape=0.05):
    excluir = set()
    valores_dim = df[dim_comparacion].dropna().unique()
    if len(valores_dim) < 2:
        return excluir

    for cand in candidatas:
        if cand not in df.columns or cand == dim_comparacion:
            continue
        valores_cand_por_cohorte = []
        for v in valores_dim:
            sub = df[df[dim_comparacion].astype(str) == str(v)]
            if len(sub) > 0:
                valores_cand_por_cohorte.append(
                    set(sub[cand].dropna().astype(str).unique())
                )

        if len(valores_cand_por_cohorte) < 2:
            continue

        solape_min = 1.0
        for i in range(len(valores_cand_por_cohorte)):
            for j in range(i + 1, len(valores_cand_por_cohorte)):
                a = valores_cand_por_cohorte[i]
                b = valores_cand_por_cohorte[j]
                if not a or not b:
                    continue
                jaccard = len(a & b) / len(a | b) if (a | b) else 1.0
                solape_min = min(solape_min, jaccard)

        if solape_min < umbral_solape:
            excluir.add(cand)
    return excluir


PATRONES_METRICA = {
    "cr": [
        r"\bconversi[oó]n\b", r"\bconversion rate\b", r"\bCR\b",
        r"\btasa de conversi[oó]n\b", r"\befectividad\b", r"\beficiencia\b",
        r"\bcierre\b", r"\bratio\b",
    ],
    "contacts": [
        r"\bcontacts?\b", r"\bcontactos?\b", r"\bfirmas?\b", r"\bfirmados?\b",
        r"\breservas?\b", r"\bconvertidos?\b", r"\bclientes?\b",
        r"\bexpedientes?\b",
    ],
    "leads": [
        r"\bleads?\b", r"\binteresad[oa]s?\b", r"\bcaptaci[oó]n\b",
        r"\bvolumen\b", r"\bregistros?\b",
    ],
}


def detectar_metrica(texto):
    if not texto:
        return "auto"
    matches = {}
    for metrica, patrones in PATRONES_METRICA.items():
        for p in patrones:
            if re.search(p, texto, flags=re.IGNORECASE):
                matches[metrica] = matches.get(metrica, 0) + 1

    if not matches:
        return "auto"
    sorted_m = sorted(matches.items(), key=lambda x: -x[1])
    if len(sorted_m) >= 2 and sorted_m[0][1] == sorted_m[1][1]:
        return "auto"
    return sorted_m[0][0]


def kpis_cohorte(df_cohorte):
    leads = int(df_cohorte[df_cohorte["Tipo de registro"] == "Leads"][ID_COL].nunique())
    contacts = int(df_cohorte[
        (df_cohorte["Tipo de registro"] == "Contacts") &
        (df_cohorte["Particular o Grupo"] == "Particular")
    ][ID_COL].nunique())
    denom = leads + contacts
    cr = contacts / denom if denom > 0 else 0.0
    return {"leads": leads, "contacts": contacts, "cr": cr, "total": denom}


def filtrar_cohorte(df, dim, valor):
    return df[df[dim].astype(str) == str(valor)].copy()


def _preparar_features(df, dimensiones_a_usar):
    X_raw = df[dimensiones_a_usar].copy()
    for c in X_raw.columns:
        X_raw[c] = X_raw[c].fillna("Sin info").astype(str)

    MAX_CAT_PER_DIM = 25
    for c in dimensiones_a_usar:
        vc = X_raw[c].value_counts()
        if len(vc) > MAX_CAT_PER_DIM:
            top = set(vc.head(MAX_CAT_PER_DIM).index)
            X_raw[c] = X_raw[c].where(X_raw[c].isin(top), other="Otros (cola)")

    X = pd.get_dummies(X_raw, prefix_sep="||")
    return X


def _agregar_importancias_por_dim(importances, columnas):
    por_dim = {}
    for col, imp in zip(columnas, importances):
        dim_original = col.split("||")[0]
        por_dim[dim_original] = por_dim.get(dim_original, 0.0) + float(imp)
    return (
        pd.DataFrame({"dimension": list(por_dim.keys()),
                      "peso": list(por_dim.values())})
        .sort_values("peso", ascending=False)
        .reset_index(drop=True)
    )


def _calcular_importancias(rf, X, y):
    try:
        from sklearn.inspection import permutation_importance
        result = permutation_importance(
            rf, X.values, y,
            n_repeats=5,
            random_state=42,
            n_jobs=1,
        )
        return np.clip(result.importances_mean, 0, None)
    except Exception:
        return rf.feature_importances_


def explicar_volumen(df_a, df_b, dimensiones, tipo_registro_filter=None):
    from sklearn.ensemble import RandomForestClassifier

    if tipo_registro_filter == "Leads":
        df_a = df_a[df_a["Tipo de registro"] == "Leads"]
        df_b = df_b[df_b["Tipo de registro"] == "Leads"]
    elif tipo_registro_filter == "Contacts":
        df_a = df_a[(df_a["Tipo de registro"] == "Contacts") &
                    (df_a["Particular o Grupo"] == "Particular")]
        df_b = df_b[(df_b["Tipo de registro"] == "Contacts") &
                    (df_b["Particular o Grupo"] == "Particular")]
        POST_CONV = {"Residencia escogida", "Residencias_actual_corregido",
                     "Residencia actual"}
        dimensiones = [d for d in dimensiones if d not in POST_CONV]

    dims = [d for d in dimensiones if d in df_a.columns]
    if not dims or len(df_a) < 10 or len(df_b) < 10:
        return pd.DataFrame(columns=["dimension", "peso"])

    df_combined = pd.concat([df_a.assign(__y=0), df_b.assign(__y=1)], ignore_index=True)
    X = _preparar_features(df_combined, dims)
    y = df_combined["__y"].values
    if X.shape[1] == 0 or len(np.unique(y)) < 2:
        return pd.DataFrame(columns=["dimension", "peso"])

    rf = RandomForestClassifier(**RF_PARAMS)
    rf.fit(X.values, y)
    importancias = _calcular_importancias(rf, X, y)
    return _agregar_importancias_por_dim(importancias, X.columns)


def explicar_cr(df_a, df_b, dimensiones):
    LEAKAGE_VARS = {
        "Tipo de registro",
        "Particular o Grupo",
        "Residencia escogida",
        "Residencias_actual_corregido",
        "Residencia actual",
    }
    dimensiones = [d for d in dimensiones if d not in LEAKAGE_VARS]
    dimensiones = [d for d in dimensiones if d in df_a.columns]
    if not dimensiones:
        return pd.DataFrame(columns=["dimension", "peso"])

    def _embudo(df):
        return df[
            (df["Tipo de registro"] == "Leads") |
            ((df["Tipo de registro"] == "Contacts") &
             (df["Particular o Grupo"] == "Particular"))
        ].copy()

    em_a = _embudo(df_a)
    em_b = _embudo(df_b)
    n_a = len(em_a)
    n_b = len(em_b)
    if n_a == 0 or n_b == 0:
        return pd.DataFrame(columns=["dimension", "peso"])

    cr_global_a = (em_a["Tipo de registro"] == "Contacts").mean()
    cr_global_b = (em_b["Tipo de registro"] == "Contacts").mean()

    resultados = []
    for dim in dimensiones:
        em_a_d = em_a.copy()
        em_b_d = em_b.copy()
        em_a_d[dim] = em_a_d[dim].fillna("Sin info").astype(str)
        em_b_d[dim] = em_b_d[dim].fillna("Sin info").astype(str)

        cr_a_por_cat = em_a_d.groupby(dim)["Tipo de registro"].apply(
            lambda s: (s == "Contacts").mean()
        )
        cr_b_por_cat = em_b_d.groupby(dim)["Tipo de registro"].apply(
            lambda s: (s == "Contacts").mean()
        )
        peso_b_por_cat = em_b_d.groupby(dim).size() / n_b

        idx_comun = cr_a_por_cat.index.intersection(cr_b_por_cat.index)
        if len(idx_comun) == 0:
            continue

        cra = cr_a_por_cat.reindex(idx_comun)
        crb = cr_b_por_cat.reindex(idx_comun)
        pesos = peso_b_por_cat.reindex(idx_comun).fillna(0)
        mask_vol = (em_b_d.groupby(dim).size().reindex(idx_comun) >= 20)
        if not mask_vol.any():
            continue
        cra = cra[mask_vol]
        crb = crb[mask_vol]
        pesos = pesos[mask_vol]

        contribuciones = pesos * (crb - cra)
        importancia = contribuciones.abs().sum()
        resultados.append({"dimension": dim, "peso": float(importancia)})

    if not resultados:
        return pd.DataFrame(columns=["dimension", "peso"])

    return (pd.DataFrame(resultados)
            .sort_values("peso", ascending=False)
            .reset_index(drop=True))


def breakdown_dimension(df_a, df_b, dim, min_total=MIN_RECORDS_FOR_BREAKDOWN):
    """Para una dimensión, agrega leads, contacts y CR de cada valor en cada cohorte."""
    if dim not in df_a.columns:
        return pd.DataFrame()

    def _agg(df):
        d = df.copy()
        d[dim] = d[dim].fillna("Sin info").astype(str)
        leads = (d[d["Tipo de registro"] == "Leads"]
                 .groupby(dim)[ID_COL].nunique())
        contacts = (d[(d["Tipo de registro"] == "Contacts") &
                      (d["Particular o Grupo"] == "Particular")]
                    .groupby(dim)[ID_COL].nunique())
        return leads, contacts

    leads_a, contacts_a = _agg(df_a)
    leads_b, contacts_b = _agg(df_b)

    idx = leads_a.index.union(leads_b.index).union(contacts_a.index).union(contacts_b.index)
    out = pd.DataFrame(index=idx)
    out.index.name = dim
    out["Leads_A"] = leads_a.reindex(idx).fillna(0).astype(int)
    out["Leads_B"] = leads_b.reindex(idx).fillna(0).astype(int)
    out["Contacts_A"] = contacts_a.reindex(idx).fillna(0).astype(int)
    out["Contacts_B"] = contacts_b.reindex(idx).fillna(0).astype(int)

    out["Delta_Leads"] = out["Leads_B"] - out["Leads_A"]
    out["Delta_Contacts"] = out["Contacts_B"] - out["Contacts_A"]

    denom_a = out["Leads_A"] + out["Contacts_A"]
    denom_b = out["Leads_B"] + out["Contacts_B"]
    out["CR_A"] = np.where(denom_a > 0, out["Contacts_A"] / denom_a, 0.0)
    out["CR_B"] = np.where(denom_b > 0, out["Contacts_B"] / denom_b, 0.0)
    out["Delta_CR_pp"] = (out["CR_B"] - out["CR_A"]) * 100

    total = denom_a + denom_b
    out = out[total >= min_total]
    return out.reset_index()


def nombre_legible_dimension(dim):
    legible = {
        "Curso_corregido": "Curso",
        "Curso": "Curso",
        "Origen_Agrupado": "Canal de captación",
        "Fuente_Agrupada": "Fuente",
        "Ciudad_deinteres_corregido": "Ciudad de interés",
        "Ciudad_actual_corregido": "Ciudad de procedencia",
        "Residencias_interes_corregido": "Residencia de interés",
        "Residencias_actual_corregido": "Residencia actual",
        "Residencia escogida": "Residencia escogida",
        "Tipo de registro": "Tipo de registro",
        "Particular o Grupo": "Particular o grupo",
        "Mes creación": "Mes de entrada",
    }
    return legible.get(dim, dim)


def render_tabla_breakdown(bd, label_a, label_b, ordenar_por="Delta_Leads", max_filas=5):
    if bd.empty:
        return "*Sin volumen suficiente para detallar.*"

    bd = bd.copy()
    bd = bd.reindex(bd[ordenar_por].abs().sort_values(ascending=False).index).head(max_filas)

    dim_col = bd.columns[0]
    lineas = [
        f"| Valor | Leads {label_a} → {label_b} | Δ Leads | "
        f"Contactos {label_a} → {label_b} | Δ Contactos | "
        f"Conversión {label_a} → {label_b} | Δ Conv. (pp) |",
        "|---|---|---|---|---|---|---|"
    ]
    for _, r in bd.iterrows():
        valor = r[dim_col] if pd.notna(r[dim_col]) else "Sin info"
        dl = int(r["Delta_Leads"]); s_dl = "+" if dl >= 0 else ""
        dc = int(r["Delta_Contacts"]); s_dc = "+" if dc >= 0 else ""
        dcr = r["Delta_CR_pp"]; s_dcr = "+" if dcr >= 0 else ""
        lineas.append(
            f"| **{valor}** | "
            f"{fmt_num(r['Leads_A'])} → {fmt_num(r['Leads_B'])} | "
            f"**{s_dl}{fmt_num(dl)}** | "
            f"{fmt_num(r['Contacts_A'])} → {fmt_num(r['Contacts_B'])} | "
            f"**{s_dc}{fmt_num(dc)}** | "
            f"{fmt_pct_abs(r['CR_A'])} → {fmt_pct_abs(r['CR_B'])} | "
            f"{s_dcr}{dcr:.2f} |"
        )
    return "\n".join(lineas)


def describir_cambio_metrica(metrica, kpi_a, kpi_b):
    if metrica == "leads":
        v_a, v_b = kpi_a["leads"], kpi_b["leads"]
        delta = v_b - v_a
        pct = var_pct(v_b, v_a)
        signo = "subido" if delta > 0 else ("bajado" if delta < 0 else "mantenido")
        return f"Los **leads** han {signo} de **{fmt_num(v_a)}** a **{fmt_num(v_b)}** ({fmt_pct(pct)})."
    if metrica == "contacts":
        v_a, v_b = kpi_a["contacts"], kpi_b["contacts"]
        delta = v_b - v_a
        pct = var_pct(v_b, v_a)
        signo = "subido" if delta > 0 else ("bajado" if delta < 0 else "mantenido")
        return f"Los **contactos** han {signo} de **{fmt_num(v_a)}** a **{fmt_num(v_b)}** ({fmt_pct(pct)})."
    if metrica == "cr":
        v_a, v_b = kpi_a["cr"], kpi_b["cr"]
        delta_pp = (v_b - v_a) * 100
        signo = "subido" if delta_pp > 0 else ("bajado" if delta_pp < 0 else "mantenido")
        s = "+" if delta_pp >= 0 else ""
        return f"La **conversión** ha {signo} de **{fmt_pct_abs(v_a)}** a **{fmt_pct_abs(v_b)}** ({s}{delta_pp:.2f} puntos)."
    return ""

df_base = aplicar_filtros_extra(leads_contacts, extra_filters)
columnas_fijadas = {col for col, _ in extra_filters}

cohortes = detectar_cohortes(
    query_text, df_base, hint=llm_hint, columnas_excluidas=columnas_fijadas
)

if cohortes is None:
    resultado = (
        "__NEEDS_LLM_PARSING__\n"
        "No se ha podido identificar automáticamente qué dos elementos comparar "
        "en la consulta. Reformula indicando claramente los dos términos a comparar "
        "(por ejemplo: «Madrid vs Barcelona», «2024/2025 vs 2025/2026», "
        "«Paid Media frente a SEO & Directo»)."
    )
else:
    dim, val_a, val_b = cohortes
    dim_legible = nombre_legible_dimension(dim)

    df_a = filtrar_cohorte(df_base, dim, val_a)
    df_b = filtrar_cohorte(df_base, dim, val_b)

    if df_a.empty or df_b.empty:
        resultado = (
            f"No hay datos suficientes para una de las dos cohortes: "
            f"«{val_a}» tiene {len(df_a)} registros, «{val_b}» tiene {len(df_b)}."
        )
    else:
        kpis_a = kpis_cohorte(df_a)
        kpis_b = kpis_cohorte(df_b)
        metrica = detectar_metrica(query_text)
        if llm_hint and isinstance(llm_hint, dict) and llm_hint.get("metrica"):
            m_hint = llm_hint["metrica"]
            if m_hint in ("leads", "contacts", "cr", "auto"):
                metrica = m_hint

        dims_modelo = candidatas_para_comparacion(dim)
        dims_dependientes = detectar_dims_dependientes(
            df_base, dim, dims_modelo
        )
        dims_modelo = [d for d in dims_modelo if d not in dims_dependientes]
        dims_filtradas = {col for col, _ in extra_filters}
        dims_modelo = [d for d in dims_modelo if d not in dims_filtradas]

        DIMS_SENSIBLES = {
            "Ciudad_deinteres_corregido": "Ciudad",
            "Ciudad_actual_corregido": "Ciudad",
            "Residencias_interes_corregido": "Residencia",
            "Residencias_actual_corregido": "Residencia",
            "Residencia escogida": "Residencia",
            "Origen_Agrupado": "Canal",
            "Fuente_Agrupada": "Fuente",
            "Ciudades de interés": "Ciudad",
            "Ciudad actual": "Ciudad",
            "Residencias de interés": "Residencia",
            "Residencia actual": "Residencia",
            "Origen/Campaña Posibles Clientes": "Canal",
            "Fuente de Posible Cliente": "Fuente",
        }
        VALORES_ESTRUCTURALES = {
            "Leads", "Contacts", "Particular", "Grupo",
            "Sin info", "Otros (cola)", "Otros", "---",
        }

        def es_curso(v):
            return bool(re.match(r"^\d{4}/\d{4}$", str(v).strip()))

        def es_estructural(v):
            return str(v).strip() in VALORES_ESTRUCTURALES

        def anonimizar_valor(valor, dim_origen, mapping):
            v_str = str(valor).strip()
            if dim_origen not in DIMS_SENSIBLES:
                return v_str
            if es_curso(v_str) or es_estructural(v_str):
                return v_str
            key = (dim_origen, v_str)
            if key in mapping:
                return mapping[key]
            tipo = DIMS_SENSIBLES[dim_origen]
            prefijo_existentes = [a for (d, _), a in mapping.items()
                                  if DIMS_SENSIBLES.get(d) == tipo]
            idx = len(prefijo_existentes) + 1
            if tipo in ("Residencia", "Canal", "Fuente"):
                def letra(n):
                    s = ""
                    while n > 0:
                        n, r = divmod(n - 1, 26)
                        s = chr(65 + r) + s
                    return s
                alias = f"{tipo} {letra(idx)}"
            else:
                alias = f"{tipo} {idx}"
            mapping[key] = alias
            return alias

        alias_map = {}

        val_a_anon = anonimizar_valor(val_a, dim, alias_map)
        val_b_anon = anonimizar_valor(val_b, dim, alias_map)

        d_leads = kpis_b["leads"] - kpis_a["leads"]
        d_contacts = kpis_b["contacts"] - kpis_a["contacts"]
        d_cr_pp = (kpis_b["cr"] - kpis_a["cr"]) * 100

        kpis_payload = {
            "leads": {
                "valor_a": int(kpis_a["leads"]),
                "valor_b": int(kpis_b["leads"]),
                "delta_abs": int(d_leads),
                "delta_pct": var_pct(kpis_b["leads"], kpis_a["leads"]),
            },
            "contactos": {
                "valor_a": int(kpis_a["contacts"]),
                "valor_b": int(kpis_b["contacts"]),
                "delta_abs": int(d_contacts),
                "delta_pct": var_pct(kpis_b["contacts"], kpis_a["contacts"]),
            },
            "conversion": {
                "valor_a": round(float(kpis_a["cr"]), 6),
                "valor_b": round(float(kpis_b["cr"]), 6),
                "delta_pp": round(float(d_cr_pp), 4),
                "delta_pct": var_pct(kpis_b["cr"], kpis_a["cr"]),
            },
        }

        if metrica == "auto":
            metricas_a_analizar = ["leads", "contacts", "cr"]
        else:
            metricas_a_analizar = [metrica]

        rankings_por_metrica = {}
        for m in metricas_a_analizar:
            if m == "leads":
                rk = explicar_volumen(df_a, df_b, dims_modelo, tipo_registro_filter="Leads")
            elif m == "contacts":
                rk = explicar_volumen(df_a, df_b, dims_modelo, tipo_registro_filter="Contacts")
            else:
                rk = explicar_cr(df_a, df_b, dims_modelo)
            rankings_por_metrica[m] = rk

        ranking_payload = {}
        for m in metricas_a_analizar:
            rk = rankings_por_metrica[m]
            if rk.empty:
                ranking_payload[m] = []
                continue
            top = rk.head(TOP_K_DRIVERS).copy()
            peso_total = top["peso"].sum()
            entradas = []
            for _, r in top.iterrows():
                pct = float(r["peso"]) / peso_total * 100 if peso_total > 0 else 0.0
                entradas.append({
                    "dimension": nombre_legible_dimension(r["dimension"]),
                    "peso_pct": round(pct, 1),
                })
            ranking_payload[m] = entradas

        dimensiones_a_desglosar = []
        if len(metricas_a_analizar) == 1:
            rk_unico = rankings_por_metrica[metricas_a_analizar[0]]
            dimensiones_a_desglosar = list(rk_unico.head(3)["dimension"].values)
        else:
            for m in metricas_a_analizar:
                rk_m = rankings_por_metrica[m]
                if not rk_m.empty:
                    top_dim_m = rk_m.iloc[0]["dimension"]
                    if top_dim_m not in dimensiones_a_desglosar:
                        dimensiones_a_desglosar.append(top_dim_m)

        if metrica == "cr":
            orden = "Delta_CR_pp"
        elif metrica == "contacts":
            orden = "Delta_Contacts"
        else:
            orden = "Delta_Leads"

        breakdown_payload = []
        for d in dimensiones_a_desglosar:
            bd = breakdown_dimension(df_a, df_b, d)
            if bd.empty:
                continue
            bd_ord = bd.reindex(
                bd[orden].abs().sort_values(ascending=False).index
            ).head(5)
            dim_col = bd_ord.columns[0]
            filas = []
            for _, r in bd_ord.iterrows():
                valor_real = r[dim_col] if pd.notna(r[dim_col]) else "Sin info"
                filas.append({
                    "valor": anonimizar_valor(valor_real, d, alias_map),
                    "leads_a": int(r["Leads_A"]),
                    "leads_b": int(r["Leads_B"]),
                    "delta_leads": int(r["Delta_Leads"]),
                    "contacts_a": int(r["Contacts_A"]),
                    "contacts_b": int(r["Contacts_B"]),
                    "delta_contacts": int(r["Delta_Contacts"]),
                    "cr_a": round(float(r["CR_A"]), 6),
                    "cr_b": round(float(r["CR_B"]), 6),
                    "delta_cr_pp": round(float(r["Delta_CR_pp"]), 4),
                })
            breakdown_payload.append({
                "dimension": nombre_legible_dimension(d),
                "filas": filas,
            })

        filtros_payload = []
        for col, val in extra_filters:
            filtros_payload.append({
                "dimension": nombre_legible_dimension(col),
                "valor": anonimizar_valor(val, col, alias_map),
            })
        if metrica == "cr":
            direccion_valor = d_cr_pp
        elif metrica == "contacts":
            direccion_valor = d_contacts
        elif metrica == "leads":
            direccion_valor = d_leads
        else:
            direccion_valor = d_cr_pp
        if direccion_valor > 0:
            direccion = "mejora"
        elif direccion_valor < 0:
            direccion = "deterioro"
        else:
            direccion = "estable"

        import json as _json
        payload = {
            "comparacion": {
                "dimension": dim_legible,
                "cohorte_a": val_a_anon,
                "cohorte_b": val_b_anon,
            },
            "filtros_aplicados": filtros_payload,
            "metrica_protagonista": metrica,
            "direccion_cambio": direccion,
            "kpis": kpis_payload,
            "variables_explicativas": ranking_payload,
            "desglose_drivers": breakdown_payload,
            "volumen_cohortes": {
                "registros_a": int(kpis_a["total"]),
                "registros_b": int(kpis_b["total"]),
            },
        }

        md = []
        md.append(f"## Análisis de **{val_a}** frente a **{val_b}**\n")
        md.append(f"*Comparación por **{dim_legible}**.*\n")
        if extra_filters:
            partes_filtro = []
            for col, val in extra_filters:
                partes_filtro.append(
                    f"**{nombre_legible_dimension(col)}** = {val}"
                )
            md.append(
                "*Filtros aplicados a toda la comparación: "
                + "; ".join(partes_filtro) + ".*\n"
            )

        md.append("### Resumen de la comparación\n")
        md.append(f"|  | {val_a} | {val_b} | Variación |")
        md.append("|---|---|---|---|")
        s_leads = "+" if d_leads >= 0 else ""
        md.append(
            f"| **Leads** | {fmt_num(kpis_a['leads'])} | {fmt_num(kpis_b['leads'])} | "
            f"{s_leads}{fmt_num(d_leads)} ({fmt_pct(var_pct(kpis_b['leads'], kpis_a['leads']))}) |"
        )
        s_contacts = "+" if d_contacts >= 0 else ""
        md.append(
            f"| **Contactos** | {fmt_num(kpis_a['contacts'])} | {fmt_num(kpis_b['contacts'])} | "
            f"{s_contacts}{fmt_num(d_contacts)} ({fmt_pct(var_pct(kpis_b['contacts'], kpis_a['contacts']))}) |"
        )
        s_cr = "+" if d_cr_pp >= 0 else ""
        md.append(
            f"| **Conversión** | {fmt_pct_abs(kpis_a['cr'])} | {fmt_pct_abs(kpis_b['cr'])} | "
            f"{s_cr}{d_cr_pp:.2f} pp ({fmt_pct(var_pct(kpis_b['cr'], kpis_a['cr']))}) |"
        )
        md.append("")

        if metrica == "auto":
            md.append("### Variables que más explican el cambio")
            md.append(
                "*Se analizan las tres métricas (leads, contactos y conversión) "
                "porque la consulta no especifica una en concreto.*\n"
            )
        else:
            etiqueta = {"leads": "los leads", "contacts": "los contactos",
                        "cr": "la conversión"}[metrica]
            md.append(f"### Variables que más explican el cambio en {etiqueta}\n")

        for m in metricas_a_analizar:
            rk = rankings_por_metrica[m]
            if len(metricas_a_analizar) > 1:
                etiqueta_m = {"leads": "Volumen de leads",
                              "contacts": "Volumen de contactos",
                              "cr": "Tasa de conversión"}[m]
                md.append(f"#### {etiqueta_m}\n")

            if rk.empty:
                md.append("*No hay suficiente información para identificar variables relevantes.*\n")
                continue

            top = rk.head(TOP_K_DRIVERS).copy()
            peso_total = top["peso"].sum()
            top["pct"] = top["peso"] / peso_total * 100 if peso_total > 0 else 0
            md.append("| Variable | Peso en la explicación |")
            md.append("|---|---|")
            for _, r in top.iterrows():
                md.append(
                    f"| **{nombre_legible_dimension(r['dimension'])}** | {r['pct']:.1f}% |"
                )
            md.append("")

        md.append("### Detalle de los cambios principales\n")

        if not dimensiones_a_desglosar:
            md.append("*No se pueden mostrar desgloses (datos insuficientes).*\n")
        else:
            for d in dimensiones_a_desglosar:
                md.append(f"#### Por {nombre_legible_dimension(d).lower()}\n")
                bd = breakdown_dimension(df_a, df_b, d)
                md.append(render_tabla_breakdown(bd, val_a, val_b, ordenar_por=orden))
                md.append("")

        markdown_real = "\n".join(md)

        alias_to_real = {}
        for (_dim_origen, real_val), alias_val in alias_map.items():
            alias_to_real.setdefault(alias_val, real_val)

        salida = {
            "kind": "insights_v2",
            "payload": payload,
            "alias_to_real": alias_to_real,
            "markdown_real": markdown_real,
        }
        resultado = "__INSIGHTS_PAYLOAD__" + _json.dumps(salida, ensure_ascii=False)
