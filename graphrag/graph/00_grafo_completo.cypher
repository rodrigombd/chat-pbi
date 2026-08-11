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
      f.descripcion = "Tabla de hechos del CRM: un registro por solicitud del usuario, que puede ser un lead o un contact. Contiene la información de solicitud para residir en una de las residencias de RESA.";


// ----------------------------------------------------------------------------
//  3) COLUMNAS RELEVANTES DE LA TABLA DE HECHOS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "Leads_Contacts"})
UNWIND [
  {nombre: "Correo electrónico",                  desc: "Identificador del usuario."},
  {nombre: "Tipo de registro",                    desc: "Etapa del CRM del registro. Toma exactamente dos valores: 'Leads' o 'Contacts', que son etapas distintas y NO intercambiables. Para responder cualquier pregunta sobre 'leads' hay que filtrar Tipo de registro == 'Leads'; para 'contacts', Tipo de registro == 'Contacts'. Si la pregunta menciona explícitamente leads o contacts, este filtro es OBLIGATORIO; omitirlo devuelve todos los registros y es un error."},
  {nombre: "Particular o Grupo",                  desc: "Indica si el contact es 'Particular' o 'Grupo'."},
  {nombre: "Curso_corregido",                     desc: "Curso académico para el que se solicita el servicio."},
  {nombre: "Fecha creación",                      desc: "Fecha creación del registro, AAAA-MM-DDTHH:MM:SS"},
  {nombre: "Ciudad_actual_corregido",             desc: "Ciudad de residencia actual del usuario, en la que se ubica la residencia actual."},
  {nombre: "Ciudad_deinteres_corregido",          desc: "Ciudad de interés del usuario, en la que se ubica la residencia de interés."},
  {nombre: "Residencias_actual_corregido",        desc: "Código de residencia RESA actual del contact."},
  {nombre: "Residencia escogida",                 desc: "Código de residencia RESA escogida por el contact."},
  {nombre: "Residencias_interes_corregido",       desc: "Código de residencia RESA de interés del usuario."},
  {nombre: "Fuente_Agrupada",                     desc: "Fuente agrupada del usuario (canal de captación)."},
  {nombre: "Origen_Agrupado",                     desc: "Origen o campaña de captación del usuario."}
] AS col
MERGE (c:Columna {tabla: "Leads_Contacts", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ----------------------------------------------------------------------------
//  3b) VALORES DE COLUMNAS CATEGÓRICAS
// ----------------------------------------------------------------------------
MATCH (c:Columna {tabla: "Leads_Contacts", nombre: "Curso_corregido"})
UNWIND ["2024/2025", "2025/2026", "2026/2027"] AS valor
MERGE (v:Valor {columna: "Curso", tabla: "Leads_Contacts", valor: valor})
MERGE (c)-[:TIENE_VALOR]->(v);

MATCH (c:Columna {tabla: "Leads_Contacts", nombre: "Origen_Agrupado"})
UNWIND ["Comisionistas", "Eventos", "Ferias", "Otros", "Paid Media", "Resa Housing", "SEO & Directo"] AS valor
MERGE (v:Valor {columna: "Origen_Agrupado", tabla: "Leads_Contacts", valor: valor})
MERGE (c)-[:TIENE_VALOR]->(v);

MATCH (c:Columna {tabla: "Leads_Contacts", nombre: "Tipo de registro"})
UNWIND ["Leads", "Contacts"] AS valor
MERGE (v:Valor {columna: "Tipo de registro", tabla: "Leads_Contacts", valor: valor})
MERGE (c)-[:TIENE_VALOR]->(v);

MATCH (c:Columna {tabla: "Leads_Contacts", nombre: "Particular o Grupo"})
UNWIND ["Particular", "Grupo"] AS valor
MERGE (v:Valor {columna: "Particular o Grupo", tabla: "Leads_Contacts", valor: valor})
MERGE (c)-[:TIENE_VALOR]->(v);


// ----------------------------------------------------------------------------
//  4) MEDIDAS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "Leads_Contacts"})
UNWIND [
  {nombre: "CR CantidadRegistros",               familia: "CR",       tipo: "Contacts+Leads", desc: "Registros totales (contacts particulares + leads).",
    formula: "VAR cant_registros = CALCULATE(\n    DISTINCTCOUNT(Leads_Contacts[Correo electrónico]),\n    Leads_Contacts[Tipo de registro] = \"Contacts\",\n    Leads_Contacts[Particular o Grupo] = \"Particular\")\n                   +\n            CALCULATE(\n    DISTINCTCOUNT(Leads_Contacts[Correo electrónico]),\n    Leads_Contacts[Tipo de registro] = \"Leads\")\n                RETURN IF(ISBLANK(cant_registros), 0, cant_registros)"},
  {nombre: "CR Convertidos",                     familia: "CR",       tipo: "Contacts",       desc: "Contacts particulares convertidos.",
    formula: "VAR cant_registros = CALCULATE(\n    DISTINCTCOUNT(Leads_Contacts[Correo electrónico]),\n    Leads_Contacts[Tipo de registro] = \"Contacts\",\n    Leads_Contacts[Particular o Grupo] = \"Particular\")\n    \nRETURN IF(ISBLANK(cant_registros), 0, cant_registros)"},
  {nombre: "CR ConversionRate",                  familia: "CR",       tipo: null,             desc: "Tasa de conversión = Convertidos / CantidadRegistros.",
    formula: "var conversion_rate = DIVIDE([CR Convertidos], [CR CantidadRegistros],0)\nRETURN\nconversion_rate"}
] AS m
MERGE (med:Medida {nombre: m.nombre})
  SET med.familia = m.familia,
      med.tipo = m.tipo,
      med.descripcion = m.desc,
      med.formula = m.formula,
      med.tabla = f.nombre
MERGE (f)-[:TIENE_MEDIDA]->(med);


// ----------------------------------------------------------------------------
//  5) COLUMNAS QUE USA CADA MEDIDA
// ----------------------------------------------------------------------------
// MATCH (m:Medida {nombre: "CR CantidadRegistros"})
// MATCH (c1:Columna {tabla: "Leads_Contacts", nombre: "Correo electrónico"})
// MATCH (c2:Columna {tabla: "Leads_Contacts", nombre: "Tipo de registro"})
// MATCH (c3:Columna {tabla: "Leads_Contacts", nombre: "Particular o Grupo"})
// MERGE (m)-[:USA_COLUMNA]->(c1)
// MERGE (m)-[:USA_COLUMNA]->(c2)
// MERGE (m)-[:USA_COLUMNA]->(c3);

// MATCH (m:Medida {nombre: "CR Convertidos"})
// MATCH (c1:Columna {tabla: "Leads_Contacts", nombre: "Correo electrónico"})
// MATCH (c2:Columna {tabla: "Leads_Contacts", nombre: "Tipo de registro"})
// MATCH (c3:Columna {tabla: "Leads_Contacts", nombre: "Particular o Grupo"})
// MERGE (m)-[:USA_COLUMNA]->(c1)
// MERGE (m)-[:USA_COLUMNA]->(c2)
// MERGE (m)-[:USA_COLUMNA]->(c3);


// ----------------------------------------------------------------------------
//  6) DEPENDENCIAS ENTRE MEDIDAS
// ----------------------------------------------------------------------------
UNWIND [
  ["CR ConversionRate", "CR Convertidos"],
  ["CR ConversionRate", "CR CantidadRegistros"]
] AS dep
MATCH (d:Medida {nombre: dep[0]})
MATCH (b:Medida {nombre: dep[1]})
MERGE (d)-[:DERIVA_DE]->(b);

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
MERGE (f:Tabla {nombre: "economics"})
  SET f.rol = "hechos",
      f.descripcion = "Tabla de hechos económica: un registro por residencia y mes. Contiene los ingresos y los costes mensuales de cada residencia RESA, identificada por su codigo_residencia.";


// ----------------------------------------------------------------------------
//  3) COLUMNAS RELEVANTES DE LA TABLA DE HECHOS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "economics"})
UNWIND [
  {nombre: "codigo_residencia",     desc: "Id de residencia."},
  {nombre: "fecha",                 desc: "MM/AAAA."},
  {nombre: "ingresos",              desc: "Ingresos mensuales."},
  {nombre: "costes",                desc: "Costes mensuales."}
] AS col
MERGE (c:Columna {tabla: "economics", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ----------------------------------------------------------------------------
//  4) MEDIDAS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "economics"})
UNWIND [
  {nombre: "ECO Margen",  familia: "ECO", tipo: "economics", desc: "Margen económico de la residencia. Se puede agregar por residencia y/o por mes (fecha).",
    formula: "SUMX(economics, economics[ingresos] - economics[costes])"}
] AS m
MERGE (med:Medida {nombre: m.nombre})
  SET med.familia = m.familia,
      med.tipo = m.tipo,
      med.descripcion = m.desc,
      med.formula = m.formula,
      med.tabla = f.nombre
MERGE (f)-[:TIENE_MEDIDA]->(med);


// ----------------------------------------------------------------------------
//  5) COLUMNAS QUE USA CADA MEDIDA
// ----------------------------------------------------------------------------
MATCH (med:Medida {nombre: "ECO Margen"})
MATCH (ci:Columna {tabla: "economics", nombre: "ingresos"})
MATCH (cc:Columna {tabla: "economics", nombre: "costes"})
MERGE (med)-[:USA_COLUMNA]->(ci)
MERGE (med)-[:USA_COLUMNA]->(cc);

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
MERGE (f:Tabla {nombre: "sizing"})
  SET f.rol = "hechos",
      f.descripcion = "Tabla de hechos de dimensionamiento: un registro por residencia y tipo de habitación. Indica cuántas habitaciones de cada tipo tiene cada residencia RESA, identificada por su codigo_residencia.";


// ----------------------------------------------------------------------------
//  3) COLUMNAS RELEVANTES DE LA TABLA DE HECHOS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "sizing"})
UNWIND [
  {nombre: "codigo_residencia",     desc: "Id de residencia."},
  {nombre: "num_rooms",             desc: "Número de habitaciones de un tipo concreto en la residencia."},
  {nombre: "room_type",             desc: "Tipo de habitacion. Valores posibles: 'S' (Single), 'D' (Double) y 'Q' (Quadruple)."}
] AS col
MERGE (c:Columna {tabla: "sizing", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ----------------------------------------------------------------------------
//  3b) VALORES DE COLUMNAS CATEGÓRICAS
// ----------------------------------------------------------------------------
MATCH (c:Columna {tabla: "sizing", nombre: "room_type"})
UNWIND ["S", "D", "Q"] AS valor
MERGE (v:Valor {columna: "room_type", tabla: "sizing", valor: valor})
MERGE (c)-[:TIENE_VALOR]->(v);


// ----------------------------------------------------------------------------
//  4) MEDIDAS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "sizing"})
UNWIND [
  {nombre: "ECO TotalRooms", familia: "ECO", tipo: "sizing", desc: "Número total de habitaciones de una residencia.",
    formula: "SUM(sizing[num_rooms])"}
] AS m
MERGE (med:Medida {nombre: m.nombre})
  SET med.familia = m.familia,
      med.tipo = m.tipo,
      med.descripcion = m.desc,
      med.formula = m.formula,
      med.tabla = f.nombre
MERGE (f)-[:TIENE_MEDIDA]->(med);


// ----------------------------------------------------------------------------
//  5) COLUMNAS QUE USA CADA MEDIDA
// ----------------------------------------------------------------------------
MATCH (med:Medida {nombre: "ECO TotalRooms"})
MATCH (cn:Columna {tabla: "sizing", nombre: "num_rooms"})
MATCH (ck:Columna {tabla: "sizing", nombre: "codigo_residencia"})
MERGE (med)-[:USA_COLUMNA]->(cn)
MERGE (med)-[:USA_COLUMNA]->(ck);


// ----------------------------------------------------------------------------
//  6) MEDIDA CRUZADA economics + sizing
//     IMPORTANTE: este bloque asume que grafo_economics.cypher YA se ha
//     ejecutado antes que este script, para que existan la tabla economics
//     y la medida "ECO Margen".
// ----------------------------------------------------------------------------
MATCH (te:Tabla {nombre: "economics"})
MATCH (ts:Tabla {nombre: "sizing"})
MERGE (med:Medida {nombre: "ECO MargenPorHabitacion"})
  SET med.familia = "ECO",
      med.tipo = "economics+sizing",
      med.descripcion = "Margen por habitación de una residencia: margen económico total de la residencia dividido entre su número total de habitaciones.",
      med.formula = "DIVIDE([ECO Margen], [ECO TotalRooms], 0)",
      med.tabla = "economics+sizing"
MERGE (te)-[:TIENE_MEDIDA]->(med)
MERGE (ts)-[:TIENE_MEDIDA]->(med);

MATCH (dep:Medida {nombre: "ECO MargenPorHabitacion"})
MATCH (m1:Medida {nombre: "ECO Margen"})
MATCH (m2:Medida {nombre: "ECO TotalRooms"})
MERGE (dep)-[:DERIVA_DE]->(m1)
MERGE (dep)-[:DERIVA_DE]->(m2);

MATCH (med:Medida {nombre: "ECO MargenPorHabitacion"})
MATCH (ck:Columna {tabla: "sizing", nombre: "codigo_residencia"})
MATCH (cke:Columna {tabla: "economics", nombre: "codigo_residencia"})
MERGE (med)-[:USA_COLUMNA]->(ck)
MERGE (med)-[:USA_COLUMNA]->(cke);

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
//  2) TABLA DE DIMENSIÓN
// ----------------------------------------------------------------------------
MERGE (f:Tabla {nombre: "maestro_residencias"})
  SET f.rol = "dimension",
      f.descripcion = "Tabla maestra de residencias: un registro por residencia RESA. Traduce el codigo_residencia a su nombre legible.";


// ----------------------------------------------------------------------------
//  3) COLUMNAS RELEVANTES DE LA TABLA DE DIMENSIÓN
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "maestro_residencias"})
UNWIND [
  {nombre: "codigo_residencia",     desc: "Identificador de la residencia RESA. Clave primaria de esta dimensión y clave que enlaza con las tablas de hechos economics y sizing."},
  {nombre: "nombre_residencia",     desc: "Nombre legible de la residencia RESA (por ejemplo 'Barcelona Diagonal'). Permite mostrar la residencia por su nombre en lugar de por su código."}
] AS col
MERGE (c:Columna {tabla: "maestro_residencias", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);

// ----------------------------------------------------------------------------
//  4) RELACIONES ENTRE TABLAS (claves de join)
//     Requiere que grafo_economics.cypher y grafo_sizing.cypher ya se hayan
//     ejecutado antes que este script.
// ----------------------------------------------------------------------------
MATCH (cm:Columna {tabla: "maestro_residencias", nombre: "codigo_residencia"})
MATCH (ce:Columna {tabla: "economics",           nombre: "codigo_residencia"})
MATCH (cs:Columna {tabla: "sizing",              nombre: "codigo_residencia"})
MATCH (cla:Columna {tabla: "Leads_Contacts",     nombre: "Residencias_actual_corregido"})
MATCH (cle:Columna {tabla: "Leads_Contacts",     nombre: "Residencia escogida"})
MATCH (cli:Columna {tabla: "Leads_Contacts",     nombre: "Residencias_interes_corregido"})
MERGE (ce)-[:RELACIONA]->(cm)
MERGE (cs)-[:RELACIONA]->(cm)
MERGE (ce)-[:RELACIONA]->(cs)
MERGE (cla)-[:RELACIONA]->(cm)
MERGE (cle)-[:RELACIONA]->(cm)
MERGE (cli)-[:RELACIONA]->(cm)
MERGE (cla)-[:RELACIONA]->(ce)
MERGE (cle)-[:RELACIONA]->(ce)
MERGE (cli)-[:RELACIONA]->(ce)
MERGE (cla)-[:RELACIONA]->(cs)
MERGE (cle)-[:RELACIONA]->(cs)
MERGE (cli)-[:RELACIONA]->(cs);