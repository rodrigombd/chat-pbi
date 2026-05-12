import re
import pandas as pd
import numpy as np

curso_1_default = "2024/2025"
curso_2_default = "2025/2026"

try:
    query_text = str(last_user_query) if last_user_query is not None else ""
except NameError:
    query_text = ""

patron = r"\b(20\d{2}|\d{2})\s*[-/]\s*(20\d{2}|\d{2})\b"
coincidencias = re.findall(patron, query_text)

cursos_encontrados = []
for anio_ini, anio_fin in coincidencias:
    if len(anio_ini) == 2:
        anio_ini = "20" + anio_ini
    if len(anio_fin) == 2:
        anio_fin = "20" + anio_fin
    
    cursos_encontrados.append(f"{anio_ini}/{anio_fin}")

if not cursos_encontrados:
    anios_sueltos = re.findall(r"\b(20\d{2})\b", query_text)
    for anio in anios_sueltos:
        anio_int = int(anio)
        cursos_encontrados.append(f"{anio_int}/{anio_int+1}")

if len(cursos_encontrados) >= 2:
    cursos_encontrados = sorted(list(set(cursos_encontrados)))
    curso_1 = cursos_encontrados[0]
    curso_2 = cursos_encontrados[-1]
elif len(cursos_encontrados) == 1:
    unico = cursos_encontrados[0]
    try:
        anio_ini = int(unico.split("/")[0])
        curso_1 = f"{anio_ini-1}/{anio_ini}"
        curso_2 = unico
    except Exception:
        curso_1 = curso_1_default
        curso_2 = curso_2_default
else:
    curso_1 = curso_1_default
    curso_2 = curso_2_default

def contar_leads(df, curso=None):
    f = df[df["Tipo de registro"] == "Leads"]
    if curso is not None:
        f = f[f["Curso"] == curso]
    if f.empty:
        return 0
    return int(f["Correo electrónico"].nunique())

def contar_contacts(df, curso=None):
    f = df[
        (df["Tipo de registro"] == "Contacts") &
        (df["Particular o Grupo"] == "Particular")
    ]
    if curso is not None:
        f = f[f["Curso"] == curso]
    if f.empty:
        return 0
    return int(f["Correo electrónico"].nunique())

def calcular_cr(contacts, leads):
    denom = contacts + leads
    if denom <= 0:
        return 0.0
    return contacts / denom

def var_pct(nuevo, viejo):
    if viejo is None or viejo == 0:
        return None
    return (nuevo / viejo) - 1.0

def fmt_pct(p, decimales=2):
    if p is None:
        return "—"
    return f"{p*100:+.{decimales}f}%"

def fmt_pct_abs(p, decimales=2):
    if p is None:
        return "—"
    return f"{p*100:.{decimales}f}%"

def fmt_num(n):
    if n is None:
        return "—"
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)

leads_1 = contar_leads(leads_contacts, curso_1)
leads_2  = contar_leads(leads_contacts, curso_2)

contacts_1 = contar_contacts(leads_contacts, curso_1)
contacts_2  = contar_contacts(leads_contacts, curso_2)

cr_1 = calcular_cr(contacts_1, leads_1)
cr_2  = calcular_cr(contacts_2, leads_2)

delta_leads     = leads_2 - leads_1
delta_contacts  = contacts_2 - contacts_1
delta_cr_pp     = (cr_2 - cr_1) * 100 

var_leads_pct    = var_pct(leads_2, leads_1)
var_contacts_pct = var_pct(contacts_2, contacts_1)
var_cr_pct       = var_pct(cr_2, cr_1)

def analizar_dimension(df, dim_col, curso_1, curso_2):
    df_filt = df[df["Curso"].isin([curso_1, curso_2])].copy()
    if df_filt.empty or dim_col not in df_filt.columns:
        return pd.DataFrame()

    leads_g = (
        df_filt[df_filt["Tipo de registro"] == "Leads"]
        .groupby([dim_col, "Curso"])["Correo electrónico"]
        .nunique()
        .unstack("Curso", fill_value=0)
    )
    contacts_g = (
        df_filt[
            (df_filt["Tipo de registro"] == "Contacts") &
            (df_filt["Particular o Grupo"] == "Particular")
        ]
        .groupby([dim_col, "Curso"])["Correo electrónico"]
        .nunique()
        .unstack("Curso", fill_value=0)
    )

    for c in [curso_1, curso_2]:
        if c not in leads_g.columns:
            leads_g[c] = 0
        if c not in contacts_g.columns:
            contacts_g[c] = 0

    out = pd.DataFrame(index=leads_g.index.union(contacts_g.index))
    out.index.name = dim_col
    out["Leads_1"]    = leads_g.reindex(out.index)[curso_1].fillna(0).astype(int)
    out["Leads_2"]     = leads_g.reindex(out.index)[curso_2].fillna(0).astype(int)
    out["Contacts_1"] = contacts_g.reindex(out.index)[curso_1].fillna(0).astype(int)
    out["Contacts_2"]  = contacts_g.reindex(out.index)[curso_2].fillna(0).astype(int)

    denom_1 = out["Contacts_1"] + out["Leads_1"]
    denom_2  = out["Contacts_2"] + out["Leads_2"]
    out["CR_1"] = np.where(denom_1 > 0, out["Contacts_1"] / denom_1, 0.0)
    out["CR_2"]  = np.where(denom_2  > 0, out["Contacts_2"]  / denom_2,  0.0)

    out["Delta_Leads"]    = out["Leads_2"]    - out["Leads_1"]
    out["Delta_Contacts"] = out["Contacts_2"] - out["Contacts_1"]
    out["Delta_CR_pp"]    = (out["CR_2"] - out["CR_1"]) * 100

    return out.reset_index()

df_origen = analizar_dimension(leads_contacts, "Origen_Agrupado", curso_1, curso_2)
df_ciudad = analizar_dimension(leads_contacts, "Ciudad_deinteres_corregido", curso_1, curso_2)

direccion_leads = "subida" if delta_leads > 0 else ("caída" if delta_leads < 0 else "estabilidad")

def top_drivers_volumen(df_dim, n=3):
    if df_dim.empty:
        return df_dim
    df_sorted = df_dim.reindex(df_dim["Delta_Leads"].abs().sort_values(ascending=False).index)
    if delta_leads < 0:
        df_sorted = df_dim.sort_values("Delta_Leads", ascending=True)
    elif delta_leads > 0:
        df_sorted = df_dim.sort_values("Delta_Leads", ascending=False)
    return df_sorted.head(n)

def top_drivers_cr(df_dim, n=3, min_volumen=20):
    if df_dim.empty:
        return df_dim
    vol_total = df_dim["Leads_1"] + df_dim["Leads_2"] + df_dim["Contacts_1"] + df_dim["Contacts_2"]
    df_f = df_dim[vol_total >= min_volumen].copy()
    if df_f.empty:
        df_f = df_dim.copy()
    if delta_cr_pp < 0:
        df_sorted = df_f.sort_values("Delta_CR_pp", ascending=True)
    elif delta_cr_pp > 0:
        df_sorted = df_f.sort_values("Delta_CR_pp", ascending=False)
    else:
        df_sorted = df_f.reindex(df_f["Delta_CR_pp"].abs().sort_values(ascending=False).index)
    return df_sorted.head(n)

drivers_origen_vol = top_drivers_volumen(df_origen, 3)
drivers_origen_cr  = top_drivers_cr(df_origen, 3, min_volumen=30)
drivers_ciudad_vol = top_drivers_volumen(df_ciudad, 3)
drivers_ciudad_cr  = top_drivers_cr(df_ciudad, 3, min_volumen=20)

md = []

md.append(f"## **Análisis de drivers · {curso_1} → {curso_2}**\n")
md.append(f"**Consulta original: «{query_text if query_text else 'análisis por defecto'}»**\n")

md.append("### **Conclusiones**\n")

if delta_leads != 0:
    md.append(
        f"- **Leads:** {fmt_num(leads_1)} → {fmt_num(leads_2)} "
        f"(**{'+' if delta_leads >= 0 else ''}{fmt_num(delta_leads)}**, "
        f"{fmt_pct(var_leads_pct)})"
    )
else:
    md.append(f"- **Leads:** {fmt_num(leads_1)} → {fmt_num(leads_2)} (sin variación)")

if delta_contacts != 0:
    md.append(
        f"- **Contacts particulares:** {fmt_num(contacts_1)} → {fmt_num(contacts_2)} "
        f"(**{'+' if delta_contacts >= 0 else ''}{fmt_num(delta_contacts)}**, "
        f"{fmt_pct(var_contacts_pct)})"
    )
else:
    md.append(f"- **Contacts particulares:** {fmt_num(contacts_1)} → {fmt_num(contacts_2)} (sin variación)")

signo_cr = "+" if delta_cr_pp >= 0 else ""
md.append(
    f"- **Conversion Rate:** {fmt_pct_abs(cr_1)} → {fmt_pct_abs(cr_2)} "
    f"(**{signo_cr}{delta_cr_pp:.2f} pp**, {fmt_pct(var_cr_pct)})\n"
)

if delta_cr_pp < 0:
    md.append(
        f"> El CR ha **bajado {abs(delta_cr_pp):.2f} pp** entre {curso_1} y {curso_2}. "
        f"Los Leads {direccion_leads} en {fmt_num(abs(delta_leads))} registros y los Contacts {('subieron' if delta_contacts>0 else 'bajaron' if delta_contacts<0 else 'se mantuvieron')} "
        f"en {fmt_num(abs(delta_contacts))}.\n"
    )
elif delta_cr_pp > 0:
    md.append(
        f"> El CR ha **subido {delta_cr_pp:.2f} pp** entre {curso_1} y {curso_2}. "
        f"Los Leads {direccion_leads} en {fmt_num(abs(delta_leads))} registros y los Contacts {('subieron' if delta_contacts>0 else 'bajaron' if delta_contacts<0 else 'se mantuvieron')} "
        f"en {fmt_num(abs(delta_contacts))}.\n"
    )
else:
    md.append(f"> El CR se mantiene estable entre {curso_1} y {curso_2}.\n")

md.append(f"### Top 3 drivers por **Origen** (impacto en volumen de Leads)\n")
if drivers_origen_vol.empty:
    md.append("- *No hay datos suficientes para este análisis.*\n")
else:
    for _, row in drivers_origen_vol.iterrows():
        nombre = row["Origen_Agrupado"] if pd.notna(row["Origen_Agrupado"]) else "Sin info"
        dl = int(row["Delta_Leads"])
        signo = "+" if dl >= 0 else ""
        impacto = "aportó" if dl > 0 else "restó"
        md.append(
            f"- **{nombre}**: {fmt_num(row['Leads_1'])} → {fmt_num(row['Leads_2'])} leads "
            f"(**{signo}{fmt_num(dl)}**). CR pasó de {fmt_pct_abs(row['CR_1'])} a {fmt_pct_abs(row['CR_2'])} "
            f"({'+' if row['Delta_CR_pp']>=0 else ''}{row['Delta_CR_pp']:.2f} pp). "
            f"Este origen **{impacto} {fmt_num(abs(dl))} leads** al cambio global."
        )
    md.append("")

md.append(f"### Top 3 drivers por **Origen** (impacto en CR)\n")
if drivers_origen_cr.empty:
    md.append("- *No hay datos suficientes para este análisis.*\n")
else:
    for _, row in drivers_origen_cr.iterrows():
        nombre = row["Origen_Agrupado"] if pd.notna(row["Origen_Agrupado"]) else "Sin info"
        dcr = row["Delta_CR_pp"]
        signo = "+" if dcr >= 0 else ""
        md.append(
            f"- **{nombre}**: CR {fmt_pct_abs(row['CR_1'])} → {fmt_pct_abs(row['CR_2'])} "
            f"(**{signo}{dcr:.2f} pp**). Leads: {fmt_num(row['Leads_1'])} → {fmt_num(row['Leads_2'])} · "
            f"Contacts: {fmt_num(row['Contacts_1'])} → {fmt_num(row['Contacts_2'])}."
        )
    md.append("")

md.append(f"### Top 2 drivers por **Ciudad de interés** (impacto en volumen de Leads)\n")
if drivers_ciudad_vol.empty:
    md.append("- *No hay datos suficientes para este análisis.*\n")
else:
    for _, row in drivers_ciudad_vol.iterrows():
        nombre = row["Ciudad_deinteres_corregido"] if pd.notna(row["Ciudad_deinteres_corregido"]) else "Sin info"
        dl = int(row["Delta_Leads"])
        signo = "+" if dl >= 0 else ""
        impacto = "aportó" if dl > 0 else "restó"
        md.append(
            f"- **{nombre}**: {fmt_num(row['Leads_1'])} → {fmt_num(row['Leads_2'])} leads "
            f"(**{signo}{fmt_num(dl)}**). CR pasó de {fmt_pct_abs(row['CR_1'])} a {fmt_pct_abs(row['CR_2'])} "
            f"({'+' if row['Delta_CR_pp']>=0 else ''}{row['Delta_CR_pp']:.2f} pp). "
            f"Esta ciudad **{impacto} {fmt_num(abs(dl))} leads** al cambio global."
        )
    md.append("")

md.append(f"### Top 2 drivers por **Ciudad de interés** (impacto en CR)\n")
if drivers_ciudad_cr.empty:
    md.append("- *No hay datos suficientes para este análisis.*\n")
else:
    for _, row in drivers_ciudad_cr.iterrows():
        nombre = row["Ciudad_deinteres_corregido"] if pd.notna(row["Ciudad_deinteres_corregido"]) else "Sin info"
        dcr = row["Delta_CR_pp"]
        signo = "+" if dcr >= 0 else ""
        md.append(
            f"- **{nombre}**: CR {fmt_pct_abs(row['CR_1'])} → {fmt_pct_abs(row['CR_2'])} "
            f"(**{signo}{dcr:.2f} pp**). Leads: {fmt_num(row['Leads_1'])} → {fmt_num(row['Leads_2'])} · "
            f"Contacts: {fmt_num(row['Contacts_1'])} → {fmt_num(row['Contacts_2'])}."
        )
    md.append("")

# --- Conclusión narrativa ---
md.append("### Lectura\n")

partes_conclusion = []

# Usamos los drivers de CR (no los de volumen) para explicar la variación del CR
if not drivers_origen_cr.empty:
    top1_origen = drivers_origen_cr.iloc[0]
    nombre_o = top1_origen["Origen_Agrupado"] if pd.notna(top1_origen["Origen_Agrupado"]) else "Sin info"
    dcr_o = top1_origen["Delta_CR_pp"]
    if dcr_o < 0:
        partes_conclusion.append(f"el origen **{nombre_o}** ha hundido su conversión en **{abs(dcr_o):.2f} pp**")
    elif dcr_o > 0:
        partes_conclusion.append(f"el origen **{nombre_o}** ha disparado su conversión en **{dcr_o:.2f} pp**")

if not drivers_ciudad_cr.empty:
    top1_ciudad = drivers_ciudad_cr.iloc[0]
    nombre_c = top1_ciudad["Ciudad_deinteres_corregido"] if pd.notna(top1_ciudad["Ciudad_deinteres_corregido"]) else "Sin info"
    dcr_c = top1_ciudad["Delta_CR_pp"]
    if dcr_c < 0:
        partes_conclusion.append(f"la ciudad **{nombre_c}** ha caído **{abs(dcr_c):.2f} pp** en conversión")
    elif dcr_c > 0:
        partes_conclusion.append(f"la ciudad **{nombre_c}** ha mejorado **{dcr_c:.2f} pp** en conversión")

if delta_cr_pp < 0:
    intro = f"El CR global ha bajado **{abs(delta_cr_pp):.2f} pp**"
elif delta_cr_pp > 0:
    intro = f"El CR global ha subido **{delta_cr_pp:.2f} pp**"
else:
    intro = "El CR global se mantiene estable"

if partes_conclusion and delta_cr_pp != 0:
    md.append(f"{intro}, impulsado principalmente porque " + " y ".join(partes_conclusion) + ".")
else:
    md.append(f"{intro}. No se detectan drivers determinantes en las dimensiones analizadas.")

if delta_cr_pp < 0 and not drivers_origen_cr.empty:
    peor_origen = drivers_origen_cr.iloc[0]
    nombre_po = peor_origen["Origen_Agrupado"] if pd.notna(peor_origen["Origen_Agrupado"]) else "Sin info"
    md.append(
        f"\n**Recomendación:** revisar la calidad del lead en el origen **{nombre_po}**, "
        f"donde el CR ha caído **{peor_origen['Delta_CR_pp']:.2f} pp**."
    )
elif delta_cr_pp > 0 and not drivers_origen_cr.empty:
    mejor_origen = drivers_origen_cr.iloc[0]
    nombre_mo = mejor_origen["Origen_Agrupado"] if pd.notna(mejor_origen["Origen_Agrupado"]) else "Sin info"
    md.append(
        f"\n**Recomendación:** capitalizar el buen rendimiento del origen **{nombre_mo}** "
        f"(CR **+{mejor_origen['Delta_CR_pp']:.2f} pp**) reasignando inversión hacia ese canal."
    )

resultado = "\n".join(md)