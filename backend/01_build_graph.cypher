// ============================================================================
//  RESA · Grafo semántico (capa de conocimiento gobernada)
//  Modelo: Tabla / Campo / Valor / Medida / Regla
//  Idempotente: usa MERGE en todo. Re-ejecutable sin duplicar.
//  Ejecutar en Neo4j Browser o cypher-shell sobre una base limpia.
// ============================================================================

// ----------------------------------------------------------------------------
//  0. Constraints de unicidad (clave natural por tipo de nodo)
// ----------------------------------------------------------------------------
CREATE CONSTRAINT tabla_nombre  IF NOT EXISTS FOR (t:Tabla)  REQUIRE t.nombre IS UNIQUE;
CREATE CONSTRAINT campo_id      IF NOT EXISTS FOR (c:Campo)  REQUIRE c.id     IS UNIQUE;
CREATE CONSTRAINT valor_id      IF NOT EXISTS FOR (v:Valor)  REQUIRE v.id     IS UNIQUE;
CREATE CONSTRAINT medida_nombre IF NOT EXISTS FOR (m:Medida) REQUIRE m.nombre IS UNIQUE;
CREATE CONSTRAINT regla_id      IF NOT EXISTS FOR (r:Regla)  REQUIRE r.id     IS UNIQUE;

// ----------------------------------------------------------------------------
//  1. Tabla de hechos
// ----------------------------------------------------------------------------
MERGE (t:Tabla {nombre: "leads_contacts"})
SET t.grano       = "Cada fila es UNA solicitud de residencia, NO una persona.",
    t.descripcion = "Tabla de hechos denormalizada. Unión de leads y contactos. Única tabla sobre la que se ejecutan consultas. 23 columnas.";

// ----------------------------------------------------------------------------
//  2. Campos (columnas) — id estable = "leads_contacts.<NombreColumna>"
//     UNWIND de una lista de mapas para mantener el script compacto y legible.
// ----------------------------------------------------------------------------
UNWIND [
  // --- Identificación y datos personales ---
  {nombre:"Correo electrónico", tipo:"string", familia:"identificacion", pii:true, corregido:false,
   descripcion:"Identifica a la PERSONA, no a la fila. Puede repetirse en varias filas (varias solicitudes). Muchos valores son 'ninguno' o vacío: no sirve como clave única."},
  {nombre:"Nombre", tipo:"string", familia:"identificacion", pii:true, corregido:false,
   descripcion:"Nombre del registro."},
  {nombre:"Apellidos", tipo:"string", familia:"identificacion", pii:true, corregido:false,
   descripcion:"Apellidos del registro."},

  // --- Clasificación del registro ---
  {nombre:"Tipo de registro", tipo:"string", familia:"clasificacion", pii:false, corregido:false,
   descripcion:"Filtro fundamental. 'Leads' = interés mostrado; 'Contacts' = contacto comercial efectivo."},
  {nombre:"Particular o Grupo", tipo:"string", familia:"clasificacion", pii:false, corregido:false,
   descripcion:"'Particular', 'Grupo', 'Residente Grupo' o nulo. Para conversión solo cuentan los 'Particular'."},

  // --- Temporal ---
  {nombre:"Fecha creación", tipo:"datetime", familia:"temporal", pii:false, corregido:false,
   descripcion:"Fecha de entrada al CRM. Eje temporal de calendario. INDEPENDIENTE de Curso."},
  {nombre:"Mes creación", tipo:"int", familia:"temporal", pii:false, corregido:false,
   descripcion:"Mes 1-12 extraído de Fecha creación."},
  {nombre:"Mes y año creación", tipo:"string", familia:"temporal", pii:false, corregido:false,
   descripcion:"Formato 'mes-aa' (ej. 'jul-25')."},

  // --- Curso académico ---
  {nombre:"Curso", tipo:"string", familia:"curso", pii:false, corregido:false,
   descripcion:"Curso académico 'YYYY/YYYY'. Es un FILTRO DE SEGMENTO, no una fecha. Independiente de Fecha creación."},
  {nombre:"Curso_corregido", tipo:"string", familia:"curso", pii:false, corregido:true,
   descripcion:"Versión saneada del curso. Preferente al agrupar por curso. Valores: 2024/2025, 2025/2026, 2026/2027, 2027/2028, 'Otros cursos', 'Sin info'."},

  // --- Ciudades ---
  {nombre:"Ciudades de interés", tipo:"string", familia:"ciudad_interes", pii:false, corregido:false,
   descripcion:"Ciudad donde el usuario busca residencia (versión cruda)."},
  {nombre:"Ciudad actual", tipo:"string", familia:"ciudad_actual", pii:false, corregido:false,
   descripcion:"Ciudad de procedencia del usuario (versión cruda)."},
  {nombre:"Ciudad_deinteres_corregido", tipo:"string", familia:"ciudad_interes", pii:false, corregido:true,
   descripcion:"Ciudad de interés saneada (nulos -> 'Sin info'). Úsese al agrupar por ciudad de interés."},
  {nombre:"Ciudad_actual_corregido", tipo:"string", familia:"ciudad_actual", pii:false, corregido:true,
   descripcion:"Ciudad actual saneada. Úsese al agrupar por ciudad actual."},

  // --- Residencias ---
  {nombre:"Residencias de interés", tipo:"string", familia:"residencia_interes", pii:false, corregido:false,
   descripcion:"Residencia que el usuario indica que le interesa (cruda)."},
  {nombre:"Residencia actual", tipo:"string", familia:"residencia_actual", pii:false, corregido:false,
   descripcion:"Residencia en la que reside actualmente, si la hay (cruda)."},
  {nombre:"Residencia escogida", tipo:"string", familia:"residencia", pii:false, corregido:false,
   descripcion:"Residencia finalmente adjudicada (si hubo contacto efectivo). '---' cuando no aplica."},
  {nombre:"Residencias_interes_corregido", tipo:"string", familia:"residencia_interes", pii:false, corregido:true,
   descripcion:"Residencia de interés saneada. Se geolocaliza SOLO con Ciudad_deinteres_corregido."},
  {nombre:"Residencias_actual_corregido", tipo:"string", familia:"residencia_actual", pii:false, corregido:true,
   descripcion:"Residencia actual saneada. Se geolocaliza SOLO con Ciudad_actual_corregido."},

  // --- Marketing / atribución ---
  {nombre:"Origen/Campaña Posibles Clientes", tipo:"string", familia:"origen", pii:false, corregido:false,
   descripcion:"Canal de marketing original concreto. Alta cardinalidad."},
  {nombre:"Fuente de Posible Cliente", tipo:"string", familia:"fuente", pii:false, corregido:false,
   descripcion:"Fuente original concreta. Alta cardinalidad."},
  {nombre:"Origen_Agrupado", tipo:"string", familia:"origen", pii:false, corregido:true,
   descripcion:"Agrupación limpia del origen. Úsese al agrupar por origen. Conjunto cerrado de 7 valores."},
  {nombre:"Fuente_Agrupada", tipo:"string", familia:"fuente", pii:false, corregido:true,
   descripcion:"Agrupación limpia de la fuente. Úsese al agrupar por fuente. Conjunto cerrado de 9 valores."}
] AS col
MERGE (c:Campo {id: "leads_contacts." + col.nombre})
SET c.nombre      = col.nombre,
    c.tipo        = col.tipo,
    c.familia     = col.familia,
    c.pii         = col.pii,
    c.corregido   = col.corregido,
    c.descripcion = col.descripcion
WITH c
MATCH (t:Tabla {nombre: "leads_contacts"})
MERGE (c)-[:PERTENECE_A]->(t);

// ----------------------------------------------------------------------------
//  3. Relaciones VERSION_CORREGIDA_DE  (campo saneado -> campo crudo)
// ----------------------------------------------------------------------------
UNWIND [
  ["Curso_corregido", "Curso"],
  ["Ciudad_deinteres_corregido", "Ciudades de interés"],
  ["Ciudad_actual_corregido", "Ciudad actual"],
  ["Residencias_interes_corregido", "Residencias de interés"],
  ["Residencias_actual_corregido", "Residencia actual"],
  ["Origen_Agrupado", "Origen/Campaña Posibles Clientes"],
  ["Fuente_Agrupada", "Fuente de Posible Cliente"]
] AS par
MATCH (corr:Campo {id: "leads_contacts." + par[0]})
MATCH (crud:Campo {id: "leads_contacts." + par[1]})
MERGE (corr)-[:VERSION_CORREGIDA_DE]->(crud);

// ----------------------------------------------------------------------------
//  4. Relaciones GEOLOCALIZA_CON  (regla estricta residencia <-> ciudad)
//     Residencia y ciudad de su MISMA familia. Prohibido cruzar familias.
// ----------------------------------------------------------------------------
UNWIND [
  ["Residencias_actual_corregido", "Ciudad_actual_corregido"],
  ["Residencias_interes_corregido", "Ciudad_deinteres_corregido"]
] AS geo
MATCH (res:Campo {id: "leads_contacts." + geo[0]})
MATCH (ciu:Campo {id: "leads_contacts." + geo[1]})
MERGE (res)-[:GEOLOCALIZA_CON]->(ciu);

// ----------------------------------------------------------------------------
//  5. Relación SE_UNE_POR  (clave de join entre tablas)
//     Hoy solo hay leads_contacts, así que no hay join activo. Dejamos el
//     patrón documentado: Correo electrónico es la clave natural de persona
//     y sería el punto de unión con futuras tablas (p. ej. una dim_personas).
//     Auto-relación marcada como clave de unión potencial.
// ----------------------------------------------------------------------------
MATCH (c:Campo {id: "leads_contacts.Correo electrónico"})
SET c.clave_union = true,
    c.nota_union  = "Clave natural de PERSONA. Punto de join con futuras tablas de dimensión. No es clave única de fila.";

// ----------------------------------------------------------------------------
//  6. Valores canónicos (solo conjuntos cerrados útiles para el retriever)
// ----------------------------------------------------------------------------
UNWIND [
  {campo:"Tipo de registro",   valores:["Leads", "Contacts"]},
  {campo:"Particular o Grupo", valores:["Particular", "Grupo", "Residente Grupo"]},
  {campo:"Curso_corregido",    valores:["2024/2025", "2025/2026", "2026/2027", "2027/2028", "Otros cursos", "Sin info"]},
  {campo:"Origen_Agrupado",    valores:["SEO & Directo", "Paid Media", "Ferias", "Comisionistas", "Eventos", "Resa Housing", "Otros"]},
  {campo:"Fuente_Agrupada",    valores:["Web Resa", "Unitour", "Directo", "Chat", "Uniscopio", "Contacto Residencia", "Hello", "Facebook", "Otros"]}
] AS spec
UNWIND spec.valores AS valorTexto
MATCH (c:Campo {id: "leads_contacts." + spec.campo})
MERGE (v:Valor {id: spec.campo + "::" + valorTexto})
SET v.valor = valorTexto, v.campo = spec.campo
MERGE (c)-[:TIENE_VALOR]->(v);

// ----------------------------------------------------------------------------
//  7. Medidas / KPIs
// ----------------------------------------------------------------------------
UNWIND [
  {nombre:"Volumen de Leads", familia:"volumen", formato:"entero",
   formula:"count(filas) WHERE `Tipo de registro` == 'Leads'",
   descripcion:"Número de solicitudes (filas) con Tipo de registro == 'Leads'. Se cuenta por FILAS, no por correos únicos."},

  {nombre:"Volumen de Contactos", familia:"volumen", formato:"entero",
   formula:"count(filas) WHERE `Tipo de registro` == 'Contacts' AND `Particular o Grupo` == 'Particular'",
   descripcion:"Número de solicitudes con Tipo de registro == 'Contacts' Y Particular o Grupo == 'Particular'. Los contactos en grupo NO entran."},

  {nombre:"Tasa de Conversión (CR)", familia:"conversion", formato:"porcentaje_1dec",
   formula:"contactos_particulares / (contactos_particulares + leads), en %",
   descripcion:"Para un curso/segmento: numerador = contactos particulares; denominador = contactos particulares + leads. Siempre en formato porcentaje, no fracción 0-1. Si el denominador es 0, devolver '--'."},

  {nombre:"Variación absoluta de CR", familia:"variacion", formato:"puntos_porcentuales",
   formula:"CR_periodo_nuevo − CR_periodo_viejo (en pp)",
   descripcion:"Diferencia de CR entre dos periodos, expresada en puntos porcentuales."},

  {nombre:"Variación porcentual de volumen", familia:"variacion", formato:"porcentaje_1dec",
   formula:"(valor_nuevo / valor_viejo) − 1; '--' si valor_viejo == 0",
   descripcion:"Variación relativa de un volumen entre dos periodos. Si el denominador es 0 devuelve '--' (replica el comportamiento DAX del informe)."},

  {nombre:"GLOBAL CantidadRegistros", familia:"volumen", formato:"entero",
   formula:"count(filas) WHERE Leads OR (Contacts AND Particular)",
   descripcion:"Total de registros del periodo (contactos particulares + leads) sin filtrar por curso."}
] AS m
MERGE (med:Medida {nombre: m.nombre})
SET med.familia     = m.familia,
    med.formato     = m.formato,
    med.formula     = m.formula,
    med.descripcion = m.descripcion;

// ----------------------------------------------------------------------------
//  8. SE_CALCULA_CON  (Medida -> Campos que necesita)  [requisito central]
// ----------------------------------------------------------------------------
UNWIND [
  {medida:"Volumen de Leads",            campos:["Tipo de registro"]},
  {medida:"Volumen de Contactos",        campos:["Tipo de registro", "Particular o Grupo"]},
  {medida:"Tasa de Conversión (CR)",     campos:["Tipo de registro", "Particular o Grupo"]},
  {medida:"GLOBAL CantidadRegistros",    campos:["Tipo de registro", "Particular o Grupo"]},
  {medida:"Variación porcentual de volumen", campos:["Fecha creación"]},
  {medida:"Variación absoluta de CR",    campos:["Curso_corregido"]}
] AS rel
MATCH (med:Medida {nombre: rel.medida})
UNWIND rel.campos AS nombreCampo
MATCH (c:Campo {id: "leads_contacts." + nombreCampo})
MERGE (med)-[:SE_CALCULA_CON]->(c);

// ----------------------------------------------------------------------------
//  9. DERIVA_DE  (Medida compuesta -> Medidas base)
// ----------------------------------------------------------------------------
UNWIND [
  ["Tasa de Conversión (CR)", "Volumen de Leads"],
  ["Tasa de Conversión (CR)", "Volumen de Contactos"],
  ["Variación absoluta de CR", "Tasa de Conversión (CR)"],
  ["GLOBAL CantidadRegistros", "Volumen de Leads"],
  ["GLOBAL CantidadRegistros", "Volumen de Contactos"]
] AS d
MATCH (a:Medida {nombre: d[0]})
MATCH (b:Medida {nombre: d[1]})
MERGE (a)-[:DERIVA_DE]->(b);

// ----------------------------------------------------------------------------
//  10. Reglas de negocio gobernadas
// ----------------------------------------------------------------------------
UNWIND [
  {id:"grano_solicitud", titulo:"El grano es la solicitud, no la persona",
   texto:"Cada fila es una solicitud. Cuenta SIEMPRE por filas (len/size). Usa nunique() solo si el usuario pide explícitamente 'personas únicas'. No agrupes por correo: muchos son 'ninguno' o vacío.",
   aplica_campos:["Correo electrónico"], aplica_medidas:["Volumen de Leads","Volumen de Contactos","GLOBAL CantidadRegistros"]},

  {id:"curso_vs_fecha", titulo:"Curso y Fecha creación son independientes",
   texto:"Curso es un filtro de segmento; Fecha creación es el eje de calendario. Para preguntas de curso: filtra por Curso/Curso_corregido y agrupa por Fecha creación. Para año natural: NO filtres por curso, extrae dt.year de Fecha creación. Nunca los conflas.",
   aplica_campos:["Curso","Curso_corregido","Fecha creación"], aplica_medidas:[]},

  {id:"geolocalizacion_estricta", titulo:"Geolocalización estricta por familia",
   texto:"Para ubicar una residencia usa SOLO la ciudad de su misma familia. Residencias_actual_corregido -> Ciudad_actual_corregido; Residencias_interes_corregido -> Ciudad_deinteres_corregido. Cruzar familias produce duplicados graves. Patrón: df[[res, ciudad]].dropna().drop_duplicates().",
   aplica_campos:["Residencias_actual_corregido","Residencias_interes_corregido","Ciudad_actual_corregido","Ciudad_deinteres_corregido"], aplica_medidas:[]},

  {id:"usar_corregido", titulo:"Agrupar siempre por la versión corregida",
   texto:"Al agrupar por curso, ciudad, residencia, origen o fuente, usa SIEMPRE la columna _corregido / _Agrupado correspondiente, no la cruda. Evita ruido por nulos y categorías minoritarias.",
   aplica_campos:["Curso_corregido","Ciudad_deinteres_corregido","Ciudad_actual_corregido","Origen_Agrupado","Fuente_Agrupada"], aplica_medidas:[]},

  {id:"denominador_cero", titulo:"Denominador cero devuelve '--'",
   texto:"En variaciones porcentuales y CR, si el denominador es 0 devuelve '--' en vez de error o infinito. Replica el comportamiento DAX del informe PowerBI.",
   aplica_campos:[], aplica_medidas:["Tasa de Conversión (CR)","Variación porcentual de volumen"]}
] AS r
MERGE (regla:Regla {id: r.id})
SET regla.titulo = r.titulo, regla.texto = r.texto
WITH regla, r
CALL {
  WITH regla, r
  UNWIND r.aplica_campos AS nc
  MATCH (c:Campo {id: "leads_contacts." + nc})
  MERGE (regla)-[:APLICA_A]->(c)
}
CALL {
  WITH regla, r
  UNWIND r.aplica_medidas AS nm
  MATCH (m:Medida {nombre: nm})
  MERGE (regla)-[:APLICA_A]->(m)
}
RETURN "Grafo RESA construido" AS status;
