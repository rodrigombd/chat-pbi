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
  {nombre: "codigo_residencia",     desc: "Identificador de la residencia RESA. Clave que enlaza sizing con las tablas economics y maestro_residencias."},
  {nombre: "num_rooms",             desc: "Número de habitaciones de un tipo concreto en la residencia. Al sumar num_rooms de una misma residencia se obtiene su total de habitaciones."},
  {nombre: "room_type",             desc: "Tipo de habitacion. Valores posibles: 'S' (Single/individual), 'D' (Double/doble) y 'Q' (Quadruple/cuádruple)."}
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
  {nombre: "ECO TotalRooms", familia: "ECO", tipo: "sizing", desc: "Número total de habitaciones de una residencia: suma de num_rooms de todos los tipos de habitación de esa misma residencia (codigo_residencia).",
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
      med.descripcion = "Margen por habitación de una residencia: margen económico total de la residencia dividido entre su número total de habitaciones. Cruza economics (margen) y sizing (total de habitaciones) por codigo_residencia.",
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
