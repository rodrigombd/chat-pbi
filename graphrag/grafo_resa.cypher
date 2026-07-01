// ----------------------------------------------------------------------------
//  0) LIMPIEZA TOTAL
// ----------------------------------------------------------------------------
MATCH (n) DETACH DELETE n;


// ----------------------------------------------------------------------------
//  1) CONSTRAINTS de unicidad
// ----------------------------------------------------------------------------
CREATE CONSTRAINT tabla_nombre IF NOT EXISTS
  FOR (t:Tabla)   REQUIRE t.nombre IS UNIQUE;
CREATE CONSTRAINT medida_nombre IF NOT EXISTS
  FOR (m:Medida)  REQUIRE m.nombre IS UNIQUE;
CREATE CONSTRAINT columna_clave IF NOT EXISTS
  FOR (c:Columna) REQUIRE (c.tabla, c.nombre) IS UNIQUE;


// ----------------------------------------------------------------------------
//  2) TABLA DE HECHOS
// ----------------------------------------------------------------------------
MERGE (f:Tabla {nombre: "Leads_Contacts"})
  SET f.rol = "hechos",
      f.descripcion = "Tabla de hechos del CRM: un registro por correo electrónico, que puede ser un lead o un contact. Contiene la información de captación de posibles clientes de las residencias RESA.";


// ----------------------------------------------------------------------------
//  3) DIMENSIONES
// ----------------------------------------------------------------------------

// --- Tabla_Curso ---
MERGE (d:Tabla {nombre: "Tabla_Curso"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de curso académico (2024/2025, 2025/2026, 2026/2027).";
MERGE (c:Columna {tabla: "Tabla_Curso", nombre: "Curso"})
  SET c.descripcion = "Curso académico al que corresponde la solicitud.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Curso";

// --- Tabla_Ciudad_Actual ---
MERGE (d:Tabla {nombre: "Tabla_Ciudad_Actual"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de ciudad de residencia actual del lead/contact.";
MERGE (c:Columna {tabla: "Tabla_Ciudad_Actual", nombre: "Ciudad actual"})
  SET c.descripcion = "Ciudad donde reside actualmente el usuario.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Ciudad actual";

// --- Tabla_Ciudad_Interés ---
MERGE (d:Tabla {nombre: "Tabla_Ciudad_Interés"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de ciudades de interés del lead/contact.";
MERGE (c:Columna {tabla: "Tabla_Ciudad_Interés", nombre: "Ciudades de interés"})
  SET c.descripcion = "Ciudad o ciudades en las que el usuario está interesado.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Ciudades de interés";

// --- Tabla_Residencia_Actual_CONTACTS ---
MERGE (d:Tabla {nombre: "Tabla_Residencia_Actual_CONTACTS"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de la residencia actual del contact.";
MERGE (c:Columna {tabla: "Tabla_Residencia_Actual_CONTACTS", nombre: "Residencia actual"})
  SET c.descripcion = "Residencia RESA en la que el contact se aloja actualmente.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Residencia actual";

// --- Tabla_Residencia_Escogida_LEADS ---
MERGE (d:Tabla {nombre: "Tabla_Residencia_Escogida_LEADS"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de la residencia escogida por el lead.";
MERGE (c:Columna {tabla: "Tabla_Residencia_Escogida_LEADS", nombre: "Residencia escogida"})
  SET c.descripcion = "Residencia RESA que el lead ha elegido.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Residencia escogida";

// --- Tabla_Residencia_Interés ---
MERGE (d:Tabla {nombre: "Tabla_Residencia_Interés"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de las residencias de interés del lead/contact.";
MERGE (c:Columna {tabla: "Tabla_Residencia_Interés", nombre: "Residencias de interés"})
  SET c.descripcion = "Residencia(s) RESA en las que el usuario está interesado.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Residencias de interés";

// --- Tabla_Fuente_PC ---
MERGE (d:Tabla {nombre: "Tabla_Fuente_PC"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de la fuente agrupada del usuario (canal por el que llegó).";
MERGE (c:Columna {tabla: "Tabla_Fuente_PC", nombre: "Fuente_Agrupada"})
  SET c.descripcion = "Fuente agrupada del usuario.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Fuente_Agrupada";

// --- Tabla_Origen ---
MERGE (d:Tabla {nombre: "Tabla_Origen"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión del origen o campaña de captación del usuario.";
MERGE (c:Columna {tabla: "Tabla_Origen", nombre: "Origen/Campaña Posibles Clientes"})
  SET c.descripcion = "Origen o campaña de marketing por la que se captó al usuario (SEO & Directo, Paid Media, Ferias, etc.).";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Origen/Campaña Posibles Clientes";

// --- Calendario ---
MERGE (d:Tabla {nombre: "Calendario"})
  SET d.rol = "dimension",
      d.descripcion = "Dimensión de fecha. Se relaciona con la fecha de creación del registro y permite análisis temporal (año, mes, trimestre, semana).";
MERGE (c:Columna {tabla: "Calendario", nombre: "Date"})
  SET c.descripcion = "Fecha del calendario, relacionada con la fecha de creación del lead/contact.";
MERGE (d)-[:TIENE_COLUMNA]->(c)
WITH d
MATCH (f:Tabla {nombre: "Leads_Contacts"})
MERGE (d)-[r:RELACIONA]->(f) SET r.columna = "Fecha creación";


// ----------------------------------------------------------------------------
//  4) COLUMNAS RELEVANTES DE LA TABLA DE HECHOS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "Leads_Contacts"})
UNWIND [
  {nombre: "Correo electrónico",                 desc: "Identificador del registro. DISTINCTCOUNT sobre este campo es la base de casi todas las medidas (cuenta leads/contacts únicos)."},
  {nombre: "Tipo de registro",                   desc: "Discrimina si el registro es 'Leads' o 'Contacts'."},
  {nombre: "Particular o Grupo",                 desc: "Indica si el contact es 'Particular' o 'Grupo'. Las conversiones solo cuentan particulares."},
  {nombre: "Curso",                              desc: "Curso académico del registro (2024/2025, 2025/2026, 2026/2027)."},
  {nombre: "Fecha creación",                     desc: "Fecha de creación del registro. Es la fecha que se relaciona con el Calendario."},
  {nombre: "Ciudad actual",                      desc: "Ciudad de residencia actual del usuario."},
  {nombre: "Ciudades de interés",                desc: "Ciudad(es) de interés del usuario."},
  {nombre: "Residencia actual",                  desc: "Residencia RESA actual del contact."},
  {nombre: "Residencia escogida",                desc: "Residencia RESA escogida por el contact."},
  {nombre: "Residencias de interés",             desc: "Residencia(s) RESA de interés del usuario."},
  {nombre: "Fuente_Agrupada",                    desc: "Fuente agrupada del usuario (canal de captación)."},
  {nombre: "Origen/Campaña Posibles Clientes",   desc: "Origen o campaña de captación del usuario."}
] AS col
MERGE (c:Columna {tabla: "Leads_Contacts", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ----------------------------------------------------------------------------
//  5) MEDIDAS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "Leads_Contacts"})
UNWIND [
  {nombre: "LEADS Seleccionados",                familia: "LEADS",    anio: null, curso: null,        tipo: "Leads",          desc: "Nº de leads (correos únicos) en el periodo seleccionado por el usuario."},
  {nombre: "CONTACTS Seleccionados",             familia: "CONTACTS", anio: null, curso: null,        tipo: "Contacts",       desc: "Nº de contacts (correos únicos) en el periodo seleccionado por el usuario."},
  {nombre: "LEADS",                              familia: "LEADS",    anio: null, curso: null,        tipo: "Leads",          desc: "Total de leads ignorando el filtro de ciudad actual."},
  {nombre: "CONTACTS_Particular",                familia: "CONTACTS", anio: null, curso: null,        tipo: "Contacts",       desc: "Total de contacts particulares, ignorando ciudad de interés."},
  {nombre: "LEADS Comparación",                  familia: "LEADS",    anio: null, curso: null,        tipo: "Leads",          desc: "Nº de leads en el rango de fechas de comparación."},
  {nombre: "CONTACTS Comparación",               familia: "CONTACTS", anio: null, curso: null,        tipo: "Contacts",       desc: "Nº de contacts en el rango de fechas de comparación."},
  {nombre: "LEADS 2024",                         familia: "LEADS",    anio: 2024, curso: "2024/2025", tipo: "Leads",          desc: "Nº de leads del curso 2024/2025."},
  {nombre: "LEADS 2025",                         familia: "LEADS",    anio: 2025, curso: "2025/2026", tipo: "Leads",          desc: "Nº de leads del curso 2025/2026."},
  {nombre: "LEADS 2026",                         familia: "LEADS",    anio: 2026, curso: "2026/2027", tipo: "Leads",          desc: "Nº de leads del curso 2026/2027."},
  {nombre: "CONTACTS 2024",                      familia: "CONTACTS", anio: 2024, curso: "2024/2025", tipo: "Contacts",       desc: "Nº de contacts del curso 2024/2025."},
  {nombre: "CONTACTS 2025",                      familia: "CONTACTS", anio: 2025, curso: "2025/2026", tipo: "Contacts",       desc: "Nº de contacts del curso 2025/2026."},
  {nombre: "CONTACTS 2026",                      familia: "CONTACTS", anio: 2026, curso: "2026/2027", tipo: "Contacts",       desc: "Nº de contacts del curso 2026/2027."},
  {nombre: "CR CantidadRegistros 2024",          familia: "CR",       anio: 2024, curso: "2024/2025", tipo: "Contacts+Leads", desc: "Denominador del conversion rate 2024/2025: registros totales (contacts particulares + leads)."},
  {nombre: "CR CantidadRegistros 2025",          familia: "CR",       anio: 2025, curso: "2025/2026", tipo: "Contacts+Leads", desc: "Denominador del conversion rate 2025/2026: registros totales (contacts particulares + leads)."},
  {nombre: "CR CantidadRegistros 2026",          familia: "CR",       anio: 2026, curso: "2026/2027", tipo: "Contacts+Leads", desc: "Denominador del conversion rate 2026/2027: registros totales (contacts particulares + leads)."},
  {nombre: "CR Convertidos 2024",                familia: "CR",       anio: 2024, curso: "2024/2025", tipo: "Contacts",       desc: "Numerador del conversion rate 2024/2025: contacts particulares convertidos."},
  {nombre: "CR Convertidos 2025",                familia: "CR",       anio: 2025, curso: "2025/2026", tipo: "Contacts",       desc: "Numerador del conversion rate 2025/2026: contacts particulares convertidos."},
  {nombre: "CR Convertidos 2026",                familia: "CR",       anio: 2026, curso: "2026/2027", tipo: "Contacts",       desc: "Numerador del conversion rate 2026/2027: contacts particulares convertidos."},
  {nombre: "CR ConversionRate 2024",             familia: "CR",       anio: 2024, curso: "2024/2025", tipo: null,             desc: "Tasa de conversión 2024/2025 = Convertidos / CantidadRegistros."},
  {nombre: "CR ConversionRate 2025",             familia: "CR",       anio: 2025, curso: "2025/2026", tipo: null,             desc: "Tasa de conversión 2025/2026 = Convertidos / CantidadRegistros."},
  {nombre: "CR ConversionRate 2026",             familia: "CR",       anio: 2026, curso: "2026/2027", tipo: null,             desc: "Tasa de conversión 2026/2027 = Convertidos / CantidadRegistros."},
  {nombre: "LEADS Incremento",                   familia: "LEADS",    anio: null, curso: null,        tipo: null,             desc: "Diferencia de leads entre selección y comparación."},
  {nombre: "CONTACTS Incremento",                familia: "CONTACTS", anio: null, curso: null,        tipo: null,             desc: "Diferencia de contacts entre selección y comparación."},
  {nombre: "LEADS Incremento 2024vs2025",        familia: "LEADS",    anio: null, curso: null,        tipo: null,             desc: "Diferencia de leads entre el curso 2025 y 2024."},
  {nombre: "LEADS Incremento 2026vs2025",        familia: "LEADS",    anio: null, curso: null,        tipo: null,             desc: "Diferencia de leads entre el curso 2026 y 2025."},
  {nombre: "CONTACTS Incremento 2024vs2025",     familia: "CONTACTS", anio: null, curso: null,        tipo: null,             desc: "Diferencia de contacts entre el curso 2025 y 2024."},
  {nombre: "CONTACTS Incremento 2026vs2025",     familia: "CONTACTS", anio: null, curso: null,        tipo: null,             desc: "Diferencia de contacts entre el curso 2026 y 2025."},
  {nombre: "LEADS % Variación_2Fechas",          familia: "LEADS",    anio: null, curso: null,        tipo: null,             desc: "Variación porcentual de leads entre selección y comparación."},
  {nombre: "CONTACTS % Variación_2Fechas",       familia: "CONTACTS", anio: null, curso: null,        tipo: null,             desc: "Variación porcentual de contacts entre selección y comparación."},
  {nombre: "LEADS % Variación 2025vs2026",       familia: "LEADS",    anio: null, curso: null,        tipo: null,             desc: "Variación porcentual de leads 2026 respecto a 2025."},
  {nombre: "LEADS % Variación 2026vs2025",       familia: "LEADS",    anio: null, curso: null,        tipo: null,             desc: "Variación porcentual de leads 2026 respecto a 2025 (con etiquetas de texto)."},
  {nombre: "CONTACTS % Variación 2025vs2026",    familia: "CONTACTS", anio: null, curso: null,        tipo: null,             desc: "Variación porcentual de contacts entre 2026 y 2024."},
  {nombre: "CONTACTS % Variación 2026vs2025",    familia: "CONTACTS", anio: null, curso: null,        tipo: null,             desc: "Variación porcentual de contacts 2026 respecto a 2025."},
  {nombre: "CR Variación 2024vs2025",            familia: "CR",       anio: null, curso: null,        tipo: null,             desc: "Diferencia de tasa de conversión entre 2025 y 2024."},
  {nombre: "CR Variación 2025vs2026",            familia: "CR",       anio: null, curso: null,        tipo: null,             desc: "Diferencia de tasa de conversión entre 2026 y 2025."},
  {nombre: "CONTACTS Previous Year",             familia: "CONTACTS", anio: null, curso: null,        tipo: "Contacts",       desc: "Contacts particulares del mismo periodo del año anterior."},
  {nombre: "LEADS Previous Year Dinámico",       familia: "LEADS",    anio: null, curso: null,        tipo: "Leads",          desc: "Leads del curso anterior al seleccionado (dinámico)."},
  {nombre: "CONTACTS Previous Year Dinámico",    familia: "CONTACTS", anio: null, curso: null,        tipo: "Contacts",       desc: "Contacts particulares del curso anterior al seleccionado (dinámico)."},
  {nombre: "LEADS % Variación_PreviousYear",     familia: "LEADS",    anio: null, curso: null,        tipo: null,             desc: "Variación de leads respecto al curso anterior dinámico."},
  {nombre: "CONTACTS % Variación_PreviousYear",  familia: "CONTACTS", anio: null, curso: null,        tipo: null,             desc: "Variación de contacts respecto al curso anterior dinámico."},
  {nombre: "GLOBAL CantidadRegistros",           familia: "GLOBAL",   anio: null, curso: null,        tipo: null,             desc: "Total global de registros (contacts particulares + leads) en el periodo."}
] AS m
MERGE (med:Medida {nombre: m.nombre})
  SET med.familia = m.familia,
      med.anio = m.anio,
      med.curso = m.curso,
      med.tipo = m.tipo,
      med.descripcion = m.desc
MERGE (f)-[:TIENE_MEDIDA]->(med);


// ----------------------------------------------------------------------------
//  6) DEPENDENCIAS ENTRE MEDIDAS
// ----------------------------------------------------------------------------
UNWIND [
  ["CR ConversionRate 2024", "CR Convertidos 2024"],
  ["CR ConversionRate 2024", "CR CantidadRegistros 2024"],
  ["CR ConversionRate 2025", "CR Convertidos 2025"],
  ["CR ConversionRate 2025", "CR CantidadRegistros 2025"],
  ["CR ConversionRate 2026", "CR Convertidos 2026"],
  ["CR ConversionRate 2026", "CR CantidadRegistros 2026"],
  ["CR Variación 2024vs2025", "CR ConversionRate 2024"],
  ["CR Variación 2024vs2025", "CR ConversionRate 2025"],
  ["CR Variación 2025vs2026", "CR ConversionRate 2025"],
  ["CR Variación 2025vs2026", "CR ConversionRate 2026"],
  ["LEADS Incremento", "LEADS Seleccionados"],
  ["LEADS Incremento", "LEADS Comparación"],
  ["CONTACTS Incremento", "CONTACTS Seleccionados"],
  ["CONTACTS Incremento", "CONTACTS Comparación"],
  ["LEADS Incremento 2024vs2025", "LEADS 2024"],
  ["LEADS Incremento 2024vs2025", "LEADS 2025"],
  ["LEADS Incremento 2026vs2025", "LEADS 2025"],
  ["LEADS Incremento 2026vs2025", "LEADS 2026"],
  ["CONTACTS Incremento 2024vs2025", "CONTACTS 2024"],
  ["CONTACTS Incremento 2024vs2025", "CONTACTS 2025"],
  ["CONTACTS Incremento 2026vs2025", "CONTACTS 2025"],
  ["CONTACTS Incremento 2026vs2025", "CONTACTS 2026"],
  ["LEADS % Variación_2Fechas", "LEADS Seleccionados"],
  ["LEADS % Variación_2Fechas", "LEADS Comparación"],
  ["CONTACTS % Variación_2Fechas", "CONTACTS Seleccionados"],
  ["CONTACTS % Variación_2Fechas", "CONTACTS Comparación"],
  ["LEADS % Variación 2025vs2026", "LEADS 2025"],
  ["LEADS % Variación 2025vs2026", "LEADS 2026"],
  ["LEADS % Variación 2026vs2025", "LEADS 2025"],
  ["LEADS % Variación 2026vs2025", "LEADS 2026"],
  ["CONTACTS % Variación 2025vs2026", "CONTACTS 2026"],
  ["CONTACTS % Variación 2025vs2026", "CONTACTS 2024"],
  ["CONTACTS % Variación 2026vs2025", "CONTACTS 2025"],
  ["CONTACTS % Variación 2026vs2025", "CONTACTS 2026"],
  ["LEADS % Variación_PreviousYear", "LEADS Seleccionados"],
  ["LEADS % Variación_PreviousYear", "LEADS Previous Year Dinámico"],
  ["CONTACTS % Variación_PreviousYear", "CONTACTS_Particular"],
  ["CONTACTS % Variación_PreviousYear", "CONTACTS Previous Year Dinámico"]
] AS dep
MATCH (d:Medida {nombre: dep[0]})
MATCH (b:Medida {nombre: dep[1]})
MERGE (d)-[:DERIVA_DE]->(b);
