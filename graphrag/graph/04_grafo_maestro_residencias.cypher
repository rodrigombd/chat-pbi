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
      f.descripcion = "Tabla maestra de residencias: un registro por residencia RESA. Traduce el codigo_residencia a su nombre legible. Se usa para enriquecer las tablas de hechos economics y sizing con el nombre de cada residencia.";


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
MERGE (cm)-[:RELACIONA]->(ce)
MERGE (cm)-[:RELACIONA]->(cs)
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