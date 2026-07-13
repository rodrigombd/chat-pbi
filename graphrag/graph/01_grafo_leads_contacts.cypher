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
//  3) COLUMNAS RELEVANTES DE LA TABLA DE HECHOS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "Leads_Contacts"})
UNWIND [
  {nombre: "Correo electrónico",                  desc: "Identificador del registro."},
  {nombre: "Tipo de registro",                    desc: "Discrimina si el registro es 'Leads' o 'Contacts'."},
  {nombre: "Particular o Grupo",                  desc: "Indica si el contact es 'Particular' o 'Grupo'. Las conversiones solo cuentan particulares."},
  {nombre: "Curso_corregido",                     desc: "Curso académico del registro."},
  {nombre: "Fecha creación",                      desc: "Fecha de creación del registro. Fecha creación, columna temporal de la tabla Leads_Contacts, fecha de alta / creación del registro, usada para series y evoluciones mensuales"},
  {nombre: "Ciudad_actual_corregido",             desc: "Ciudad de residencia actual del usuario."},
  {nombre: "Ciudad_deinteres_corregido",        desc: "Ciudad de interés del usuario."},
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


// ----------------------------------------------------------------------------
//  4) MEDIDAS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "Leads_Contacts"})
UNWIND [
  {nombre: "CR CantidadRegistros",               familia: "CR",       tipo: "Contacts+Leads", desc: "Registros totales (contacts particulares + leads), general por contexto/slicer.",
    formula: "VAR cant_registros = CALCULATE(\n    DISTINCTCOUNT(Leads_Contacts[Correo electrónico]),\n    Leads_Contacts[Tipo de registro] = \"Contacts\",\n    Leads_Contacts[Particular o Grupo] = \"Particular\",\n    REMOVEFILTERS('Tabla_Ciudad_Interés'),\n    REMOVEFILTERS('Tabla_Residencia_Interés'))\n                   +\n            CALCULATE(\n    DISTINCTCOUNT(Leads_Contacts[Correo electrónico]),\n    Leads_Contacts[Tipo de registro] = \"Leads\",\n    REMOVEFILTERS(Tabla_Ciudad_Actual),\n    REMOVEFILTERS(Tabla_Residencia_Actual_CONTACTS))\n                RETURN IF(ISBLANK(cant_registros), 0, cant_registros)"},
  {nombre: "CR Convertidos",                     familia: "CR",       tipo: "Contacts",       desc: "Contacts particulares convertidos, general por contexto/slicer.",
    formula: "VAR cant_registros = CALCULATE(\n    DISTINCTCOUNT(Leads_Contacts[Correo electrónico]),\n    Leads_Contacts[Tipo de registro] = \"Contacts\",\n    Leads_Contacts[Particular o Grupo] = \"Particular\",\n    REMOVEFILTERS('Tabla_Ciudad_Interés'),\n    REMOVEFILTERS('Tabla_Residencia_Interés'))\n    \nRETURN IF(ISBLANK(cant_registros), 0, cant_registros)"},
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
MATCH (m:Medida {nombre: "CR CantidadRegistros"})
MATCH (c1:Columna {tabla: "Leads_Contacts", nombre: "Correo electrónico"})
MATCH (c2:Columna {tabla: "Leads_Contacts", nombre: "Tipo de registro"})
MATCH (c3:Columna {tabla: "Leads_Contacts", nombre: "Particular o Grupo"})
MERGE (m)-[:USA_COLUMNA]->(c1)
MERGE (m)-[:USA_COLUMNA]->(c2)
MERGE (m)-[:USA_COLUMNA]->(c3);

MATCH (m:Medida {nombre: "CR Convertidos"})
MATCH (c1:Columna {tabla: "Leads_Contacts", nombre: "Correo electrónico"})
MATCH (c2:Columna {tabla: "Leads_Contacts", nombre: "Tipo de registro"})
MATCH (c3:Columna {tabla: "Leads_Contacts", nombre: "Particular o Grupo"})
MERGE (m)-[:USA_COLUMNA]->(c1)
MERGE (m)-[:USA_COLUMNA]->(c2)
MERGE (m)-[:USA_COLUMNA]->(c3);


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
