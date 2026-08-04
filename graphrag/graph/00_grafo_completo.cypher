// ============================================================================
//  GRAFO SEMÁNTICO — MODELO RETAIL (caso de uso Marta)
//  Esquema en estrella: 5 dimensiones + 3 tablas de hechos.
//  Ontología idéntica al modelo RESA: Tabla / Columna / Medida / Valor
//  Relaciones: TIENE_COLUMNA / TIENE_MEDIDA / TIENE_VALOR / USA_COLUMNA
//              / DERIVA_DE / RELACIONA
//  NOTA: las medidas y sus fórmulas DAX son propuestas inferidas de las
//        columnas de hechos. Revisar/ajustar contra las definiciones reales
//        de la Fabric app de Marta.
// ============================================================================


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


// ============================================================================
//  DIMENSIÓN: DIM_Canal
// ============================================================================
MERGE (f:Tabla {nombre: "DIM_Canal"})
  SET f.rol = "dimension",
      f.descripcion = "Dimensión de canal de venta: un registro por canal a través del cual se realiza una venta (tienda física, web, marketplace, app móvil).";

MATCH (f:Tabla {nombre: "DIM_Canal"})
UNWIND [
  {nombre: "ChannelID",          desc: "Identificador del canal. Clave primaria de la dimensión; enlaza con FACT_Ventas."},
  {nombre: "ChannelName",        desc: "Nombre legible del canal (por ejemplo 'Web', 'Mobile App')."},
  {nombre: "ChannelGroup",       desc: "Agrupación del canal: 'Online' u 'Offline'."},
  {nombre: "ChannelDescription", desc: "Descripción larga del canal."}
] AS col
MERGE (c:Columna {tabla: "DIM_Canal", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);

MATCH (c:Columna {tabla: "DIM_Canal", nombre: "ChannelGroup"})
UNWIND ["Online", "Offline"] AS valor
MERGE (v:Valor {columna: "ChannelGroup", tabla: "DIM_Canal", valor: valor})
MERGE (c)-[:TIENE_VALOR]->(v);


// ============================================================================
//  DIMENSIÓN: DIM_Cliente
// ============================================================================
MERGE (f:Tabla {nombre: "DIM_Cliente"})
  SET f.rol = "dimension",
      f.descripcion = "Dimensión de cliente: un registro por cliente. Contiene segmento, región, fecha de alta, nivel de fidelidad y franja de edad.";

MATCH (f:Tabla {nombre: "DIM_Cliente"})
UNWIND [
  {nombre: "CustomerID",      desc: "Identificador del cliente. Clave primaria de la dimensión; enlaza con FACT_Ventas."},
  {nombre: "CustomerSegment", desc: "Segmento de cliente (por ejemplo 'Consumer', 'Small Business')."},
  {nombre: "Region",          desc: "Región geográfica del cliente."},
  {nombre: "SignupDate",      desc: "Fecha de alta del cliente (AAAA-MM-DD)."},
  {nombre: "LoyaltyTier",     desc: "Nivel del programa de fidelidad (por ejemplo 'Bronze', 'Silver', 'Gold')."},
  {nombre: "AgeBand",         desc: "Franja de edad del cliente (por ejemplo '18-24', '35-44')."}
] AS col
MERGE (c:Columna {tabla: "DIM_Cliente", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);

MATCH (c:Columna {tabla: "DIM_Cliente", nombre: "LoyaltyTier"})
UNWIND ["Bronze", "Silver", "Gold"] AS valor
MERGE (v:Valor {columna: "LoyaltyTier", tabla: "DIM_Cliente", valor: valor})
MERGE (c)-[:TIENE_VALOR]->(v);


// ============================================================================
//  DIMENSIÓN: DIM_Producto
// ============================================================================
MERGE (f:Tabla {nombre: "DIM_Producto"})
  SET f.rol = "dimension",
      f.descripcion = "Dimensión de producto: un registro por producto del catálogo. Contiene categoría, subcategoría, marca, precio y coste de referencia, estado y fecha de lanzamiento.";

MATCH (f:Tabla {nombre: "DIM_Producto"})
UNWIND [
  {nombre: "ProductID",      desc: "Identificador del producto. Clave primaria de la dimensión; enlaza con FACT_Ventas y FACT_Precios."},
  {nombre: "ProductName",    desc: "Nombre legible del producto."},
  {nombre: "Category",       desc: "Categoría del producto (por ejemplo 'Electronics', 'Accessories')."},
  {nombre: "Subcategory",    desc: "Subcategoría del producto (por ejemplo 'Imaging', 'Audio')."},
  {nombre: "Brand",          desc: "Marca del producto."},
  {nombre: "ReferencePrice", desc: "Precio de referencia (PVP) del producto."},
  {nombre: "ReferenceCost",  desc: "Coste de referencia del producto."},
  {nombre: "ProductStatus",  desc: "Estado del producto en el catálogo (por ejemplo 'Active', 'Discontinued')."},
  {nombre: "LaunchDate",     desc: "Fecha de lanzamiento del producto (AAAA-MM-DD)."}
] AS col
MERGE (c:Columna {tabla: "DIM_Producto", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ============================================================================
//  DIMENSIÓN: DIM_Promocion
// ============================================================================
MERGE (f:Tabla {nombre: "DIM_Promocion"})
  SET f.rol = "dimension",
      f.descripcion = "Dimensión de promoción: un registro por promoción o campaña. Contiene el tipo, el descuento estándar y el periodo de validez.";

MATCH (f:Tabla {nombre: "DIM_Promocion"})
UNWIND [
  {nombre: "PromotionID",      desc: "Identificador de la promoción. Clave primaria de la dimensión; enlaza con FACT_Ventas. El valor 'PR00' representa 'sin promoción'."},
  {nombre: "PromotionName",    desc: "Nombre legible de la promoción."},
  {nombre: "PromotionType",    desc: "Tipo de promoción (por ejemplo 'Seasonal', 'None')."},
  {nombre: "StandardDiscount", desc: "Descuento estándar de la promoción, en porcentaje."},
  {nombre: "ValidFrom",        desc: "Fecha de inicio de validez de la promoción (AAAA-MM-DD)."},
  {nombre: "ValidTo",          desc: "Fecha de fin de validez de la promoción (AAAA-MM-DD)."}
] AS col
MERGE (c:Columna {tabla: "DIM_Promocion", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ============================================================================
//  DIMENSIÓN: DIM_Tienda
// ============================================================================
MERGE (f:Tabla {nombre: "DIM_Tienda"})
  SET f.rol = "dimension",
      f.descripcion = "Dimensión de tienda: un registro por tienda física. Contiene ubicación (región, provincia, ciudad), tipo, superficie, fecha de apertura, responsable y estado.";

MATCH (f:Tabla {nombre: "DIM_Tienda"})
UNWIND [
  {nombre: "StoreID",     desc: "Identificador de la tienda. Clave primaria de la dimensión; enlaza con FACT_Ventas y FACT_Costes_Tienda."},
  {nombre: "StoreName",   desc: "Nombre legible de la tienda."},
  {nombre: "Region",      desc: "Región geográfica de la tienda."},
  {nombre: "Province",    desc: "Provincia de la tienda."},
  {nombre: "City",        desc: "Ciudad de la tienda."},
  {nombre: "StoreType",   desc: "Tipo de tienda (por ejemplo 'Flagship', 'Urban', 'Retail Park')."},
  {nombre: "SizeM2",      desc: "Superficie de la tienda en metros cuadrados."},
  {nombre: "OpeningDate", desc: "Fecha de apertura de la tienda (AAAA-MM-DD)."},
  {nombre: "Manager",     desc: "Responsable/gerente de la tienda."},
  {nombre: "StoreStatus", desc: "Estado de la tienda (por ejemplo 'Active', 'Closed')."}
] AS col
MERGE (c:Columna {tabla: "DIM_Tienda", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ============================================================================
//  HECHOS: FACT_Ventas  (grano: línea de pedido)
// ============================================================================
MERGE (f:Tabla {nombre: "FACT_Ventas"})
  SET f.rol = "hechos",
      f.descripcion = "Tabla de hechos de ventas: un registro por línea de pedido. Contiene cantidades, ventas brutas y netas, descuentos, devoluciones, costes de producto/envío, comisiones de pago y margen de contribución.";

MATCH (f:Tabla {nombre: "FACT_Ventas"})
UNWIND [
  {nombre: "SalesLineID",        desc: "Identificador de la línea de venta. Clave primaria de la tabla de hechos."},
  {nombre: "OrderID",            desc: "Identificador del pedido al que pertenece la línea."},
  {nombre: "DateKey",            desc: "Clave de fecha de la venta en formato AAAAMMDD."},
  {nombre: "ProductID",          desc: "Clave foránea al producto vendido (DIM_Producto)."},
  {nombre: "StoreID",            desc: "Clave foránea a la tienda donde se produce la venta (DIM_Tienda)."},
  {nombre: "CustomerID",         desc: "Clave foránea al cliente (DIM_Cliente)."},
  {nombre: "ChannelID",          desc: "Clave foránea al canal de venta (DIM_Canal)."},
  {nombre: "PromotionID",        desc: "Clave foránea a la promoción aplicada (DIM_Promocion)."},
  {nombre: "Quantity",           desc: "Unidades vendidas en la línea."},
  {nombre: "GrossSales",         desc: "Ventas brutas de la línea, antes de descuentos."},
  {nombre: "DiscountRate",       desc: "Porcentaje de descuento aplicado."},
  {nombre: "DiscountAmount",     desc: "Importe de descuento aplicado."},
  {nombre: "NetSales",           desc: "Ventas netas de la línea, después de descuentos."},
  {nombre: "ReturnedQuantity",   desc: "Unidades devueltas de la línea."},
  {nombre: "ReturnAmount",       desc: "Importe devuelto."},
  {nombre: "ProductCost",        desc: "Coste del producto de la línea."},
  {nombre: "ShippingCost",       desc: "Coste de envío de la línea."},
  {nombre: "PaymentFee",         desc: "Comisión de pago de la línea."},
  {nombre: "ContributionMargin", desc: "Margen de contribución de la línea (ventas netas menos costes directos)."}
] AS col
MERGE (c:Columna {tabla: "FACT_Ventas", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ============================================================================
//  HECHOS: FACT_Precios  (grano: producto x mes)
// ============================================================================
MERGE (f:Tabla {nombre: "FACT_Precios"})
  SET f.rol = "hechos",
      f.descripcion = "Tabla de hechos de precios: un registro por producto y mes. Contiene precio de lista, IVA, precio sin IVA, coste y margen unitarios.";

MATCH (f:Tabla {nombre: "FACT_Precios"})
UNWIND [
  {nombre: "PriceID",      desc: "Identificador del registro de precio. Clave primaria de la tabla de hechos."},
  {nombre: "MonthDateKey", desc: "Clave de mes en formato AAAAMMDD (primer día del mes)."},
  {nombre: "ProductID",    desc: "Clave foránea al producto (DIM_Producto)."},
  {nombre: "ListPrice",    desc: "Precio de lista del producto en ese mes."},
  {nombre: "VATRate",      desc: "Tipo de IVA aplicado, en porcentaje."},
  {nombre: "PriceExVAT",   desc: "Precio sin IVA."},
  {nombre: "UnitCost",     desc: "Coste unitario del producto en ese mes."},
  {nombre: "UnitMargin",   desc: "Margen unitario (precio sin IVA menos coste unitario)."}
] AS col
MERGE (c:Columna {tabla: "FACT_Precios", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ============================================================================
//  HECHOS: FACT_Costes_Tienda  (grano: tienda x mes)
// ============================================================================
MERGE (f:Tabla {nombre: "FACT_Costes_Tienda"})
  SET f.rol = "hechos",
      f.descripcion = "Tabla de hechos de costes de tienda: un registro por tienda y mes. Desglosa los costes operativos (personal, alquiler, comisiones, energía, logística, mantenimiento, otros) y su total.";

MATCH (f:Tabla {nombre: "FACT_Costes_Tienda"})
UNWIND [
  {nombre: "StoreCostID",     desc: "Identificador del registro de coste. Clave primaria de la tabla de hechos."},
  {nombre: "MonthDateKey",    desc: "Clave de mes en formato AAAAMMDD (primer día del mes)."},
  {nombre: "StoreID",         desc: "Clave foránea a la tienda (DIM_Tienda)."},
  {nombre: "PersonnelCost",   desc: "Coste de personal del mes."},
  {nombre: "RentCost",        desc: "Coste de alquiler del mes."},
  {nombre: "CommissionCost",  desc: "Coste de comisiones del mes."},
  {nombre: "EnergyCost",      desc: "Coste de energía del mes."},
  {nombre: "LogisticsCost",   desc: "Coste de logística del mes."},
  {nombre: "MaintenanceCost", desc: "Coste de mantenimiento del mes."},
  {nombre: "OtherCost",       desc: "Otros costes del mes."},
  {nombre: "TotalStoreCost",  desc: "Coste total de la tienda en el mes (suma de los anteriores)."}
] AS col
MERGE (c:Columna {tabla: "FACT_Costes_Tienda", nombre: col.nombre})
  SET c.descripcion = col.desc
MERGE (f)-[:TIENE_COLUMNA]->(c);


// ============================================================================
//  MEDIDAS  (propuestas — validar DAX con la Fabric app de Marta)
// ============================================================================

// --- Ventas ---
MATCH (f:Tabla {nombre: "FACT_Ventas"})
UNWIND [
  {nombre: "VTA VentasNetas",      familia: "VTA", tipo: "FACT_Ventas", desc: "Suma de las ventas netas.",
    formula: "SUM(FACT_Ventas[NetSales])"},
  {nombre: "VTA VentasBrutas",     familia: "VTA", tipo: "FACT_Ventas", desc: "Suma de las ventas brutas.",
    formula: "SUM(FACT_Ventas[GrossSales])"},
  {nombre: "VTA Unidades",         familia: "VTA", tipo: "FACT_Ventas", desc: "Total de unidades vendidas.",
    formula: "SUM(FACT_Ventas[Quantity])"},
  {nombre: "VTA MargenContribucion", familia: "VTA", tipo: "FACT_Ventas", desc: "Margen de contribución total.",
    formula: "SUM(FACT_Ventas[ContributionMargin])"},
  {nombre: "VTA TasaDevolucion",   familia: "VTA", tipo: "FACT_Ventas", desc: "Tasa de devolución = unidades devueltas / unidades vendidas.",
    formula: "DIVIDE(SUM(FACT_Ventas[ReturnedQuantity]), SUM(FACT_Ventas[Quantity]), 0)"}
] AS m
MERGE (med:Medida {nombre: m.nombre})
  SET med.familia = m.familia, med.tipo = m.tipo, med.descripcion = m.desc,
      med.formula = m.formula, med.tabla = f.nombre
MERGE (f)-[:TIENE_MEDIDA]->(med);

// --- Costes de tienda ---
MATCH (f:Tabla {nombre: "FACT_Costes_Tienda"})
UNWIND [
  {nombre: "CST CosteTotalTienda", familia: "CST", tipo: "FACT_Costes_Tienda", desc: "Coste operativo total de tienda.",
    formula: "SUM(FACT_Costes_Tienda[TotalStoreCost])"}
] AS m
MERGE (med:Medida {nombre: m.nombre})
  SET med.familia = m.familia, med.tipo = m.tipo, med.descripcion = m.desc,
      med.formula = m.formula, med.tabla = f.nombre
MERGE (f)-[:TIENE_MEDIDA]->(med);

// --- Columnas que usan las medidas ---
MATCH (med:Medida {nombre: "VTA TasaDevolucion"})
MATCH (c1:Columna {tabla: "FACT_Ventas", nombre: "ReturnedQuantity"})
MATCH (c2:Columna {tabla: "FACT_Ventas", nombre: "Quantity"})
MERGE (med)-[:USA_COLUMNA]->(c1)
MERGE (med)-[:USA_COLUMNA]->(c2);

// --- Medida cruzada Ventas + Costes: rentabilidad por tienda ---
MATCH (tv:Tabla {nombre: "FACT_Ventas"})
MATCH (tc:Tabla {nombre: "FACT_Costes_Tienda"})
MERGE (med:Medida {nombre: "MIX ResultadoTienda"})
  SET med.familia = "MIX",
      med.tipo = "FACT_Ventas+FACT_Costes_Tienda",
      med.descripcion = "Resultado por tienda: margen de contribución de ventas menos el coste total de tienda.",
      med.formula = "[VTA MargenContribucion] - [CST CosteTotalTienda]",
      med.tabla = "FACT_Ventas+FACT_Costes_Tienda"
MERGE (tv)-[:TIENE_MEDIDA]->(med)
MERGE (tc)-[:TIENE_MEDIDA]->(med);

MATCH (dep:Medida {nombre: "MIX ResultadoTienda"})
MATCH (m1:Medida {nombre: "VTA MargenContribucion"})
MATCH (m2:Medida {nombre: "CST CosteTotalTienda"})
MERGE (dep)-[:DERIVA_DE]->(m1)
MERGE (dep)-[:DERIVA_DE]->(m2);


// ============================================================================
//  RELACIONES ENTRE TABLAS (claves de join del esquema en estrella)
// ============================================================================
// FACT_Ventas -> dimensiones
MATCH (fk:Columna {tabla: "FACT_Ventas", nombre: "ProductID"})
MATCH (pk:Columna {tabla: "DIM_Producto", nombre: "ProductID"})
MERGE (fk)-[:RELACIONA]->(pk);

MATCH (fk:Columna {tabla: "FACT_Ventas", nombre: "StoreID"})
MATCH (pk:Columna {tabla: "DIM_Tienda", nombre: "StoreID"})
MERGE (fk)-[:RELACIONA]->(pk);

MATCH (fk:Columna {tabla: "FACT_Ventas", nombre: "CustomerID"})
MATCH (pk:Columna {tabla: "DIM_Cliente", nombre: "CustomerID"})
MERGE (fk)-[:RELACIONA]->(pk);

MATCH (fk:Columna {tabla: "FACT_Ventas", nombre: "ChannelID"})
MATCH (pk:Columna {tabla: "DIM_Canal", nombre: "ChannelID"})
MERGE (fk)-[:RELACIONA]->(pk);

MATCH (fk:Columna {tabla: "FACT_Ventas", nombre: "PromotionID"})
MATCH (pk:Columna {tabla: "DIM_Promocion", nombre: "PromotionID"})
MERGE (fk)-[:RELACIONA]->(pk);

// FACT_Precios -> DIM_Producto
MATCH (fk:Columna {tabla: "FACT_Precios", nombre: "ProductID"})
MATCH (pk:Columna {tabla: "DIM_Producto", nombre: "ProductID"})
MERGE (fk)-[:RELACIONA]->(pk);

// FACT_Costes_Tienda -> DIM_Tienda
MATCH (fk:Columna {tabla: "FACT_Costes_Tienda", nombre: "StoreID"})
MATCH (pk:Columna {tabla: "DIM_Tienda", nombre: "StoreID"})
MERGE (fk)-[:RELACIONA]->(pk);
