// ---------------------------------------------------------------------------
// 0. Restricciones de unicidad
// ---------------------------------------------------------------------------
CREATE CONSTRAINT tabla_nombre   IF NOT EXISTS FOR (t:Tabla)   REQUIRE t.nombre IS UNIQUE;
CREATE CONSTRAINT medida_nombre  IF NOT EXISTS FOR (m:Medida)  REQUIRE m.nombre IS UNIQUE;

// ---------------------------------------------------------------------------
// 1. Tablas: la de hechos + las dimensiones que de verdad usa un usuario
// ---------------------------------------------------------------------------
MERGE (:Tabla {nombre: "Leads_Contacts",                  rol: "hechos"});
MERGE (:Tabla {nombre: "Tabla_Curso",                     rol: "dimension"});
MERGE (:Tabla {nombre: "Tabla_Ciudad_Actual",             rol: "dimension"});
MERGE (:Tabla {nombre: "Tabla_Ciudad_Interés",            rol: "dimension"});
MERGE (:Tabla {nombre: "Tabla_Residencia_Actual_CONTACTS",rol: "dimension"});
MERGE (:Tabla {nombre: "Tabla_Residencia_Escogida_LEADS", rol: "dimension"});
MERGE (:Tabla {nombre: "Tabla_Residencia_Interés",        rol: "dimension"});
MERGE (:Tabla {nombre: "Tabla_Fuente_PC",                 rol: "dimension"});
MERGE (:Tabla {nombre: "Tabla_Origen",                    rol: "dimension"});
MERGE (:Tabla {nombre: "Maestro_Fuente",                  rol: "dimension"});
MERGE (:Tabla {nombre: "Calendario",                      rol: "dimension"});

// ---------------------------------------------------------------------------
// 2. Columnas de la tabla de hechos (las que aparecen en filtros/medidas)
// ---------------------------------------------------------------------------
UNWIND [
  "Correo electrónico", "Tipo de registro", "Curso", "Particular o Grupo",
  "Fecha creación", "Ciudad actual", "Ciudades de interés",
  "Residencia actual", "Residencia escogida", "Residencias de interés",
  "Fuente_Agrupada", "Origen/Campaña Posibles Clientes", "Fuente de Posible Cliente"
] AS col
MATCH (t:Tabla {nombre: "Leads_Contacts"})
MERGE (c:Columna {nombre: col, tabla: "Leads_Contacts"})
MERGE (t)-[:TIENE_COLUMNA]->(c);

UNWIND [
  {t: "Tabla_Curso",                      c: "Curso"},
  {t: "Tabla_Ciudad_Actual",              c: "Ciudad actual"},
  {t: "Tabla_Ciudad_Interés",             c: "Ciudades de interés"},
  {t: "Tabla_Residencia_Actual_CONTACTS", c: "Residencia actual"},
  {t: "Tabla_Residencia_Escogida_LEADS",  c: "Residencia escogida"},
  {t: "Tabla_Residencia_Interés",         c: "Residencias de interés"},
  {t: "Tabla_Fuente_PC",                  c: "Fuente_Agrupada"},
  {t: "Tabla_Origen",                     c: "Origen/Campaña Posibles Clientes"},
  {t: "Maestro_Fuente",                   c: "Fuente_Leads"},
  {t: "Calendario",                       c: "Date"}
] AS dim
MATCH (t:Tabla {nombre: dim.t})
MERGE (c:Columna {nombre: dim.c, tabla: dim.t})
MERGE (t)-[:TIENE_COLUMNA]->(c);

// ---------------------------------------------------------------------------
// 3. Relaciones del modelo (dimensión -> hechos), por su columna de enlace
// ---------------------------------------------------------------------------
UNWIND [
  {ft: "Leads_Contacts", fc: "Curso",                          tt: "Tabla_Curso",                      tc: "Curso"},
  {ft: "Leads_Contacts", fc: "Ciudad actual",                  tt: "Tabla_Ciudad_Actual",              tc: "Ciudad actual"},
  {ft: "Leads_Contacts", fc: "Ciudades de interés",            tt: "Tabla_Ciudad_Interés",             tc: "Ciudades de interés"},
  {ft: "Leads_Contacts", fc: "Residencia actual",              tt: "Tabla_Residencia_Actual_CONTACTS", tc: "Residencia actual"},
  {ft: "Leads_Contacts", fc: "Residencia escogida",            tt: "Tabla_Residencia_Escogida_LEADS",  tc: "Residencia escogida"},
  {ft: "Leads_Contacts", fc: "Residencias de interés",         tt: "Tabla_Residencia_Interés",         tc: "Residencias de interés"},
  {ft: "Leads_Contacts", fc: "Fuente_Agrupada",                tt: "Tabla_Fuente_PC",                  tc: "Fuente_Agrupada"},
  {ft: "Leads_Contacts", fc: "Origen/Campaña Posibles Clientes",tt: "Tabla_Origen",                    tc: "Origen/Campaña Posibles Clientes"},
  {ft: "Leads_Contacts", fc: "Fuente de Posible Cliente",      tt: "Maestro_Fuente",                   tc: "Fuente_Leads"},
  {ft: "Leads_Contacts", fc: "Fecha creación",                 tt: "Calendario",                       tc: "Date"}
] AS rel
MATCH (a:Columna {nombre: rel.fc, tabla: rel.ft})
MATCH (b:Columna {nombre: rel.tc, tabla: rel.tt})
MERGE (a)-[:RELACIONA]->(b);

// ---------------------------------------------------------------------------
// 4. Medidas — con sus FILTROS como propiedades
// ---------------------------------------------------------------------------

MERGE (m:Medida {nombre: "LEADS Seleccionados"})
  SET m.familia="LEADS", m.anio=null, m.tipo_registro="Leads", m.curso=null,
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de leads (correos únicos) en el periodo seleccionado por el usuario";
MERGE (m:Medida {nombre: "CONTACTS Seleccionados"})
  SET m.familia="CONTACTS", m.anio=null, m.tipo_registro="Contacts", m.curso=null,
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de contacts (correos únicos) en el periodo seleccionado por el usuario";
MERGE (m:Medida {nombre: "LEADS"})
  SET m.familia="LEADS", m.anio=null, m.tipo_registro="Leads", m.curso=null,
      m.particular=null, m.formato="#,0",
      m.descripcion="Total de leads ignorando el filtro de ciudad actual";
MERGE (m:Medida {nombre: "CONTACTS_Particular"})
  SET m.familia="CONTACTS", m.anio=null, m.tipo_registro="Contacts", m.curso=null,
      m.particular="Particular", m.formato="#,0",
      m.descripcion="Total de contacts particulares, ignorando ciudad de interés";

// --- Medidas de comparación temporal (rango de comparación) ---
MERGE (m:Medida {nombre: "LEADS Comparación"})
  SET m.familia="LEADS", m.anio=null, m.tipo_registro="Leads", m.curso=null,
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de leads en el rango de fechas de comparación";
MERGE (m:Medida {nombre: "CONTACTS Comparación"})
  SET m.familia="CONTACTS", m.anio=null, m.tipo_registro="Contacts", m.curso=null,
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de contacts en el rango de fechas de comparación";

// --- LEADS por curso académico ---
MERGE (m:Medida {nombre: "LEADS 2024"})
  SET m.familia="LEADS", m.anio=2024, m.tipo_registro="Leads", m.curso="2024/2025",
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de leads del curso 2024/2025";
MERGE (m:Medida {nombre: "LEADS 2025"})
  SET m.familia="LEADS", m.anio=2025, m.tipo_registro="Leads", m.curso="2025/2026",
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de leads del curso 2025/2026";
MERGE (m:Medida {nombre: "LEADS 2026"})
  SET m.familia="LEADS", m.anio=2026, m.tipo_registro="Leads", m.curso="2026/2027",
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de leads del curso 2026/2027";

// --- CONTACTS por curso académico ---
MERGE (m:Medida {nombre: "CONTACTS 2024"})
  SET m.familia="CONTACTS", m.anio=2024, m.tipo_registro="Contacts", m.curso="2024/2025",
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de contacts del curso 2024/2025";
MERGE (m:Medida {nombre: "CONTACTS 2025"})
  SET m.familia="CONTACTS", m.anio=2025, m.tipo_registro="Contacts", m.curso="2025/2026",
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de contacts del curso 2025/2026";
MERGE (m:Medida {nombre: "CONTACTS 2026"})
  SET m.familia="CONTACTS", m.anio=2026, m.tipo_registro="Contacts", m.curso="2026/2027",
      m.particular=null, m.formato="#,0",
      m.descripcion="Nº de contacts del curso 2026/2027";

// --- Conversion Rate: numerador (convertidos) y denominador (cantidad) ---
MERGE (m:Medida {nombre: "CR CantidadRegistros 2024"})
  SET m.familia="CR", m.anio=2024, m.tipo_registro="Contacts+Leads", m.curso="2024/2025",
      m.particular="Particular", m.formato="0",
      m.descripcion="Denominador del conversion rate 2024/2025: registros totales (contacts particulares + leads)";
MERGE (m:Medida {nombre: "CR CantidadRegistros 2025"})
  SET m.familia="CR", m.anio=2025, m.tipo_registro="Contacts+Leads", m.curso="2025/2026",
      m.particular="Particular", m.formato="0",
      m.descripcion="Denominador del conversion rate 2025/2026: registros totales (contacts particulares + leads)";
MERGE (m:Medida {nombre: "CR CantidadRegistros 2026"})
  SET m.familia="CR", m.anio=2026, m.tipo_registro="Contacts+Leads", m.curso="2026/2027",
      m.particular="Particular", m.formato="0",
      m.descripcion="Denominador del conversion rate 2026/2027: registros totales (contacts particulares + leads)";
MERGE (m:Medida {nombre: "CR Convertidos 2024"})
  SET m.familia="CR", m.anio=2024, m.tipo_registro="Contacts", m.curso="2024/2025",
      m.particular="Particular", m.formato="0",
      m.descripcion="Numerador del conversion rate 2024/2025: contacts particulares convertidos";
MERGE (m:Medida {nombre: "CR Convertidos 2025"})
  SET m.familia="CR", m.anio=2025, m.tipo_registro="Contacts", m.curso="2025/2026",
      m.particular="Particular", m.formato="0",
      m.descripcion="Numerador del conversion rate 2025/2026: contacts particulares convertidos";
MERGE (m:Medida {nombre: "CR Convertidos 2026"})
  SET m.familia="CR", m.anio=2026, m.tipo_registro="Contacts", m.curso="2026/2027",
      m.particular="Particular", m.formato="0",
      m.descripcion="Numerador del conversion rate 2026/2027: contacts particulares convertidos";

// --- Conversion Rate (ratio) por año ---
MERGE (m:Medida {nombre: "CR ConversionRate 2024"})
  SET m.familia="CR", m.anio=2024, m.tipo_registro=null, m.curso="2024/2025",
      m.particular=null, m.formato="0.0 %",
      m.descripcion="Tasa de conversión 2024/2025 = Convertidos / CantidadRegistros";
MERGE (m:Medida {nombre: "CR ConversionRate 2025"})
  SET m.familia="CR", m.anio=2025, m.tipo_registro=null, m.curso="2025/2026",
      m.particular=null, m.formato="0.0 %",
      m.descripcion="Tasa de conversión 2025/2026 = Convertidos / CantidadRegistros";
MERGE (m:Medida {nombre: "CR ConversionRate 2026"})
  SET m.familia="CR", m.anio=2026, m.tipo_registro=null, m.curso="2026/2027",
      m.particular=null, m.formato="0.0 %",
      m.descripcion="Tasa de conversión 2026/2027 = Convertidos / CantidadRegistros";

// --- Incrementos (diferencias absolutas entre periodos) ---
MERGE (m:Medida {nombre: "LEADS Incremento"})
  SET m.familia="LEADS", m.formato="0",
      m.descripcion="Diferencia de leads entre selección y comparación";
MERGE (m:Medida {nombre: "CONTACTS Incremento"})
  SET m.familia="CONTACTS", m.formato="0",
      m.descripcion="Diferencia de contacts entre selección y comparación";
MERGE (m:Medida {nombre: "LEADS Incremento 2024vs2025"})
  SET m.familia="LEADS", m.formato="0",
      m.descripcion="Diferencia de leads entre el curso 2025 y 2024";
MERGE (m:Medida {nombre: "LEADS Incremento 2026vs2025"})
  SET m.familia="LEADS", m.formato="0",
      m.descripcion="Diferencia de leads entre el curso 2026 y 2025";
MERGE (m:Medida {nombre: "CONTACTS Incremento 2024vs2025"})
  SET m.familia="CONTACTS", m.formato="0",
      m.descripcion="Diferencia de contacts entre el curso 2025 y 2024";
MERGE (m:Medida {nombre: "CONTACTS Incremento 2026vs2025"})
  SET m.familia="CONTACTS", m.formato="0",
      m.descripcion="Diferencia de contacts entre el curso 2026 y 2025";

// --- Variaciones porcentuales ---
MERGE (m:Medida {nombre: "LEADS % Variación_2Fechas"})
  SET m.familia="LEADS", m.formato="0.0 %",
      m.descripcion="Variación porcentual de leads entre selección y comparación";
MERGE (m:Medida {nombre: "CONTACTS % Variación_2Fechas"})
  SET m.familia="CONTACTS", m.formato="0.0 %",
      m.descripcion="Variación porcentual de contacts entre selección y comparación";
MERGE (m:Medida {nombre: "LEADS % Variación 2025vs2026"})
  SET m.familia="LEADS", m.formato="0.0 %",
      m.descripcion="Variación porcentual de leads 2026 respecto a 2025";
MERGE (m:Medida {nombre: "LEADS % Variación 2026vs2025"})
  SET m.familia="LEADS", m.formato="0.0 %",
      m.descripcion="Variación porcentual de leads 2026 respecto a 2025 (con etiquetas de texto)";
MERGE (m:Medida {nombre: "CONTACTS % Variación 2025vs2026"})
  SET m.familia="CONTACTS", m.formato="0.0 %",
      m.descripcion="Variación porcentual de contacts entre 2026 y 2024";
MERGE (m:Medida {nombre: "CONTACTS % Variación 2026vs2025"})
  SET m.familia="CONTACTS", m.formato="0.0 %",
      m.descripcion="Variación porcentual de contacts 2026 respecto a 2025";
MERGE (m:Medida {nombre: "CR Variación 2024vs2025"})
  SET m.familia="CR", m.formato="0.0 %",
      m.descripcion="Diferencia de tasa de conversión entre 2025 y 2024";
MERGE (m:Medida {nombre: "CR Variación 2025vs2026"})
  SET m.familia="CR", m.formato="0.0 %",
      m.descripcion="Diferencia de tasa de conversión entre 2026 y 2025";

// --- Año anterior dinámico (previous year) ---
MERGE (m:Medida {nombre: "CONTACTS Previous Year"})
  SET m.familia="CONTACTS", m.tipo_registro="Contacts", m.particular="Particular",
      m.formato="0",
      m.descripcion="Contacts particulares del mismo periodo del año anterior";
MERGE (m:Medida {nombre: "LEADS Previous Year Dinámico"})
  SET m.familia="LEADS", m.tipo_registro="Leads", m.formato="0",
      m.descripcion="Leads del curso anterior al seleccionado (dinámico)";
MERGE (m:Medida {nombre: "CONTACTS Previous Year Dinámico"})
  SET m.familia="CONTACTS", m.tipo_registro="Contacts", m.particular="Particular",
      m.formato="0",
      m.descripcion="Contacts particulares del curso anterior al seleccionado (dinámico)";
MERGE (m:Medida {nombre: "LEADS % Variación_PreviousYear"})
  SET m.familia="LEADS", m.formato="0.0 %",
      m.descripcion="Variación de leads respecto al curso anterior dinámico";
MERGE (m:Medida {nombre: "CONTACTS % Variación_PreviousYear"})
  SET m.familia="CONTACTS", m.formato="0.0 %",
      m.descripcion="Variación de contacts respecto al curso anterior dinámico";

// --- Global ---
MERGE (m:Medida {nombre: "GLOBAL CantidadRegistros"})
  SET m.familia="GLOBAL", m.particular="Particular", m.formato="#,0",
      m.descripcion="Total global de registros (contacts particulares + leads) en el periodo";

// ---------------------------------------------------------------------------
// 5. Tabla -> Medida (todas cuelgan de 'Medidas calculadas' en el modelo,
//    pero semánticamente operan sobre Leads_Contacts)
// ---------------------------------------------------------------------------
MATCH (t:Tabla {nombre: "Leads_Contacts"}), (m:Medida)
MERGE (t)-[:TIENE_MEDIDA]->(m);

// ---------------------------------------------------------------------------
// 6. Medida -> Columna que usa (la columna base contada + columnas de filtro)
// ---------------------------------------------------------------------------
// Todas cuentan "Correo electrónico". Lo conectamos para todas.
MATCH (m:Medida), (c:Columna {nombre: "Correo electrónico", tabla: "Leads_Contacts"})
MERGE (m)-[:USA_COLUMNA]->(c);

// Medidas que filtran por "Tipo de registro" (casi todas las base)
MATCH (m:Medida), (c:Columna {nombre: "Tipo de registro", tabla: "Leads_Contacts"})
WHERE m.tipo_registro IS NOT NULL
MERGE (m)-[:USA_COLUMNA]->(c);

// Medidas que filtran por "Curso"
MATCH (m:Medida), (c:Columna {nombre: "Curso", tabla: "Leads_Contacts"})
WHERE m.curso IS NOT NULL
MERGE (m)-[:USA_COLUMNA]->(c);

// Medidas que filtran por "Particular o Grupo"
MATCH (m:Medida), (c:Columna {nombre: "Particular o Grupo", tabla: "Leads_Contacts"})
WHERE m.particular IS NOT NULL
MERGE (m)-[:USA_COLUMNA]->(c);

// ---------------------------------------------------------------------------
// 7. Cadenas medida -> medida (DERIVA_DE)
// ---------------------------------------------------------------------------
UNWIND [
  // Conversion rate = convertidos / cantidad
  {de: "CR ConversionRate 2024", base: "CR Convertidos 2024"},
  {de: "CR ConversionRate 2024", base: "CR CantidadRegistros 2024"},
  {de: "CR ConversionRate 2025", base: "CR Convertidos 2025"},
  {de: "CR ConversionRate 2025", base: "CR CantidadRegistros 2025"},
  {de: "CR ConversionRate 2026", base: "CR Convertidos 2026"},
  {de: "CR ConversionRate 2026", base: "CR CantidadRegistros 2026"},
  // Variaciones de CR
  {de: "CR Variación 2024vs2025", base: "CR ConversionRate 2024"},
  {de: "CR Variación 2024vs2025", base: "CR ConversionRate 2025"},
  {de: "CR Variación 2025vs2026", base: "CR ConversionRate 2025"},
  {de: "CR Variación 2025vs2026", base: "CR ConversionRate 2026"},
  // Incrementos LEADS/CONTACTS por selección
  {de: "LEADS Incremento", base: "LEADS Seleccionados"},
  {de: "LEADS Incremento", base: "LEADS Comparación"},
  {de: "CONTACTS Incremento", base: "CONTACTS Seleccionados"},
  {de: "CONTACTS Incremento", base: "CONTACTS Comparación"},
  // Incrementos por curso
  {de: "LEADS Incremento 2024vs2025", base: "LEADS 2024"},
  {de: "LEADS Incremento 2024vs2025", base: "LEADS 2025"},
  {de: "LEADS Incremento 2026vs2025", base: "LEADS 2025"},
  {de: "LEADS Incremento 2026vs2025", base: "LEADS 2026"},
  {de: "CONTACTS Incremento 2024vs2025", base: "CONTACTS 2024"},
  {de: "CONTACTS Incremento 2024vs2025", base: "CONTACTS 2025"},
  {de: "CONTACTS Incremento 2026vs2025", base: "CONTACTS 2025"},
  {de: "CONTACTS Incremento 2026vs2025", base: "CONTACTS 2026"},
  // Variaciones % por selección
  {de: "LEADS % Variación_2Fechas", base: "LEADS Seleccionados"},
  {de: "LEADS % Variación_2Fechas", base: "LEADS Comparación"},
  {de: "CONTACTS % Variación_2Fechas", base: "CONTACTS Seleccionados"},
  {de: "CONTACTS % Variación_2Fechas", base: "CONTACTS Comparación"},
  // Variaciones % por curso
  {de: "LEADS % Variación 2025vs2026", base: "LEADS 2025"},
  {de: "LEADS % Variación 2025vs2026", base: "LEADS 2026"},
  {de: "LEADS % Variación 2026vs2025", base: "LEADS 2025"},
  {de: "LEADS % Variación 2026vs2025", base: "LEADS 2026"},
  {de: "CONTACTS % Variación 2025vs2026", base: "CONTACTS 2026"},
  {de: "CONTACTS % Variación 2025vs2026", base: "CONTACTS 2024"},
  {de: "CONTACTS % Variación 2026vs2025", base: "CONTACTS 2025"},
  {de: "CONTACTS % Variación 2026vs2025", base: "CONTACTS 2026"},
  // Previous year dinámico
  {de: "LEADS % Variación_PreviousYear", base: "LEADS Seleccionados"},
  {de: "LEADS % Variación_PreviousYear", base: "LEADS Previous Year Dinámico"},
  {de: "CONTACTS % Variación_PreviousYear", base: "CONTACTS_Particular"},
  {de: "CONTACTS % Variación_PreviousYear", base: "CONTACTS Previous Year Dinámico"}
] AS dep
MATCH (a:Medida {nombre: dep.de}), (b:Medida {nombre: dep.base})
MERGE (a)-[:DERIVA_DE]->(b);
