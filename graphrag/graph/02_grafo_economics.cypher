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
  {nombre: "codigo_residencia",     desc: "Identificador de la residencia RESA. Clave que enlaza economics con las tablas sizing y maestro_residencias."},
  {nombre: "fecha",                 desc: "Mes al que corresponden los ingresos y costes, en formato MM/AAAA (por ejemplo 01/2023). Columna temporal de la tabla economics, usada para series y evoluciones mensuales."},
  {nombre: "ingresos",              desc: "Ingresos mensuales de la residencia en euros para el mes indicado."},
  {nombre: "costes",                desc: "Costes mensuales de la residencia en euros para el mes indicado."}
] AS col
MERGE (c:Columna {tabla: "economics", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ----------------------------------------------------------------------------
//  4) MEDIDAS
// ----------------------------------------------------------------------------
MATCH (f:Tabla {nombre: "economics"})
UNWIND [
  {nombre: "ECO Margen",  familia: "ECO", tipo: "economics", desc: "Margen económico de la residencia: ingresos menos costes. Se puede agregar por residencia y/o por mes (fecha).",
    formula: "SUMX(economics, economics[ingresos] - economics[costes])"}
] AS m
MERGE (med:Medida {nombre: m.nombre})
  SET med.familia = m.familia,
      med.tipo = m.tipo,
      med.descripcion = m.desc,
      med.formula = m.formula
MERGE (f)-[:TIENE_MEDIDA]->(med);


// ----------------------------------------------------------------------------
//  5) COLUMNAS QUE USA CADA MEDIDA
// ----------------------------------------------------------------------------
MATCH (med:Medida {nombre: "ECO Margen"})
MATCH (ci:Columna {tabla: "economics", nombre: "ingresos"})
MATCH (cc:Columna {tabla: "economics", nombre: "costes"})
MERGE (med)-[:USA_COLUMNA]->(ci)
MERGE (med)-[:USA_COLUMNA]->(cc);
