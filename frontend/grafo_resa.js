var GRAFO_RESA = {
  medidas: [
    { nombre: "LEADS Seleccionados", familia: "LEADS", anio: null, curso: null, tipo: "Leads", desc: "Nº de leads (correos únicos) en el periodo seleccionado por el usuario" },
    { nombre: "CONTACTS Seleccionados", familia: "CONTACTS", anio: null, curso: null, tipo: "Contacts", desc: "Nº de contacts (correos únicos) en el periodo seleccionado por el usuario" },
    { nombre: "LEADS", familia: "LEADS", anio: null, curso: null, tipo: "Leads", desc: "Total de leads ignorando el filtro de ciudad actual" },
    { nombre: "CONTACTS_Particular", familia: "CONTACTS", anio: null, curso: null, tipo: "Contacts", desc: "Total de contacts particulares, ignorando ciudad de interés" },
    { nombre: "LEADS Comparación", familia: "LEADS", anio: null, curso: null, tipo: "Leads", desc: "Nº de leads en el rango de fechas de comparación" },
    { nombre: "CONTACTS Comparación", familia: "CONTACTS", anio: null, curso: null, tipo: "Contacts", desc: "Nº de contacts en el rango de fechas de comparación" },
    { nombre: "LEADS 2024", familia: "LEADS", anio: 2024, curso: "2024/2025", tipo: "Leads", desc: "Nº de leads del curso 2024/2025" },
    { nombre: "LEADS 2025", familia: "LEADS", anio: 2025, curso: "2025/2026", tipo: "Leads", desc: "Nº de leads del curso 2025/2026" },
    { nombre: "LEADS 2026", familia: "LEADS", anio: 2026, curso: "2026/2027", tipo: "Leads", desc: "Nº de leads del curso 2026/2027" },
    { nombre: "CONTACTS 2024", familia: "CONTACTS", anio: 2024, curso: "2024/2025", tipo: "Contacts", desc: "Nº de contacts del curso 2024/2025" },
    { nombre: "CONTACTS 2025", familia: "CONTACTS", anio: 2025, curso: "2025/2026", tipo: "Contacts", desc: "Nº de contacts del curso 2025/2026" },
    { nombre: "CONTACTS 2026", familia: "CONTACTS", anio: 2026, curso: "2026/2027", tipo: "Contacts", desc: "Nº de contacts del curso 2026/2027" },
    { nombre: "CR CantidadRegistros 2024", familia: "CR", anio: 2024, curso: "2024/2025", tipo: "Contacts+Leads", desc: "Denominador del conversion rate 2024/2025: registros totales (contacts particulares + leads)" },
    { nombre: "CR CantidadRegistros 2025", familia: "CR", anio: 2025, curso: "2025/2026", tipo: "Contacts+Leads", desc: "Denominador del conversion rate 2025/2026: registros totales (contacts particulares + leads)" },
    { nombre: "CR CantidadRegistros 2026", familia: "CR", anio: 2026, curso: "2026/2027", tipo: "Contacts+Leads", desc: "Denominador del conversion rate 2026/2027: registros totales (contacts particulares + leads)" },
    { nombre: "CR Convertidos 2024", familia: "CR", anio: 2024, curso: "2024/2025", tipo: "Contacts", desc: "Numerador del conversion rate 2024/2025: contacts particulares convertidos" },
    { nombre: "CR Convertidos 2025", familia: "CR", anio: 2025, curso: "2025/2026", tipo: "Contacts", desc: "Numerador del conversion rate 2025/2026: contacts particulares convertidos" },
    { nombre: "CR Convertidos 2026", familia: "CR", anio: 2026, curso: "2026/2027", tipo: "Contacts", desc: "Numerador del conversion rate 2026/2027: contacts particulares convertidos" },
    { nombre: "CR ConversionRate 2024", familia: "CR", anio: 2024, curso: "2024/2025", tipo: null, desc: "Tasa de conversión 2024/2025 = Convertidos / CantidadRegistros" },
    { nombre: "CR ConversionRate 2025", familia: "CR", anio: 2025, curso: "2025/2026", tipo: null, desc: "Tasa de conversión 2025/2026 = Convertidos / CantidadRegistros" },
    { nombre: "CR ConversionRate 2026", familia: "CR", anio: 2026, curso: "2026/2027", tipo: null, desc: "Tasa de conversión 2026/2027 = Convertidos / CantidadRegistros" },
    { nombre: "LEADS Incremento", familia: "LEADS", anio: null, curso: null, tipo: null, desc: "Diferencia de leads entre selección y comparación" },
    { nombre: "CONTACTS Incremento", familia: "CONTACTS", anio: null, curso: null, tipo: null, desc: "Diferencia de contacts entre selección y comparación" },
    { nombre: "LEADS Incremento 2024vs2025", familia: "LEADS", anio: null, curso: null, tipo: null, desc: "Diferencia de leads entre el curso 2025 y 2024" },
    { nombre: "LEADS Incremento 2026vs2025", familia: "LEADS", anio: null, curso: null, tipo: null, desc: "Diferencia de leads entre el curso 2026 y 2025" },
    { nombre: "CONTACTS Incremento 2024vs2025", familia: "CONTACTS", anio: null, curso: null, tipo: null, desc: "Diferencia de contacts entre el curso 2025 y 2024" },
    { nombre: "CONTACTS Incremento 2026vs2025", familia: "CONTACTS", anio: null, curso: null, tipo: null, desc: "Diferencia de contacts entre el curso 2026 y 2025" },
    { nombre: "LEADS % Variación_2Fechas", familia: "LEADS", anio: null, curso: null, tipo: null, desc: "Variación porcentual de leads entre selección y comparación" },
    { nombre: "CONTACTS % Variación_2Fechas", familia: "CONTACTS", anio: null, curso: null, tipo: null, desc: "Variación porcentual de contacts entre selección y comparación" },
    { nombre: "LEADS % Variación 2025vs2026", familia: "LEADS", anio: null, curso: null, tipo: null, desc: "Variación porcentual de leads 2026 respecto a 2025" },
    { nombre: "LEADS % Variación 2026vs2025", familia: "LEADS", anio: null, curso: null, tipo: null, desc: "Variación porcentual de leads 2026 respecto a 2025 (con etiquetas de texto)" },
    { nombre: "CONTACTS % Variación 2025vs2026", familia: "CONTACTS", anio: null, curso: null, tipo: null, desc: "Variación porcentual de contacts entre 2026 y 2024" },
    { nombre: "CONTACTS % Variación 2026vs2025", familia: "CONTACTS", anio: null, curso: null, tipo: null, desc: "Variación porcentual de contacts 2026 respecto a 2025" },
    { nombre: "CR Variación 2024vs2025", familia: "CR", anio: null, curso: null, tipo: null, desc: "Diferencia de tasa de conversión entre 2025 y 2024" },
    { nombre: "CR Variación 2025vs2026", familia: "CR", anio: null, curso: null, tipo: null, desc: "Diferencia de tasa de conversión entre 2026 y 2025" },
    { nombre: "CONTACTS Previous Year", familia: "CONTACTS", anio: null, curso: null, tipo: "Contacts", desc: "Contacts particulares del mismo periodo del año anterior" },
    { nombre: "LEADS Previous Year Dinámico", familia: "LEADS", anio: null, curso: null, tipo: "Leads", desc: "Leads del curso anterior al seleccionado (dinámico)" },
    { nombre: "CONTACTS Previous Year Dinámico", familia: "CONTACTS", anio: null, curso: null, tipo: "Contacts", desc: "Contacts particulares del curso anterior al seleccionado (dinámico)" },
    { nombre: "LEADS % Variación_PreviousYear", familia: "LEADS", anio: null, curso: null, tipo: null, desc: "Variación de leads respecto al curso anterior dinámico" },
    { nombre: "CONTACTS % Variación_PreviousYear", familia: "CONTACTS", anio: null, curso: null, tipo: null, desc: "Variación de contacts respecto al curso anterior dinámico" },
    { nombre: "GLOBAL CantidadRegistros", familia: "GLOBAL", anio: null, curso: null, tipo: null, desc: "Total global de registros (contacts particulares + leads) en el periodo" }
  ],
  deriva: [
    ["CR ConversionRate 2024", "CR Convertidos 2024"], ["CR ConversionRate 2024", "CR CantidadRegistros 2024"],
    ["CR ConversionRate 2025", "CR Convertidos 2025"], ["CR ConversionRate 2025", "CR CantidadRegistros 2025"],
    ["CR ConversionRate 2026", "CR Convertidos 2026"], ["CR ConversionRate 2026", "CR CantidadRegistros 2026"],
    ["CR Variación 2024vs2025", "CR ConversionRate 2024"], ["CR Variación 2024vs2025", "CR ConversionRate 2025"],
    ["CR Variación 2025vs2026", "CR ConversionRate 2025"], ["CR Variación 2025vs2026", "CR ConversionRate 2026"],
    ["LEADS Incremento", "LEADS Seleccionados"], ["LEADS Incremento", "LEADS Comparación"],
    ["CONTACTS Incremento", "CONTACTS Seleccionados"], ["CONTACTS Incremento", "CONTACTS Comparación"],
    ["LEADS Incremento 2024vs2025", "LEADS 2024"], ["LEADS Incremento 2024vs2025", "LEADS 2025"],
    ["LEADS Incremento 2026vs2025", "LEADS 2025"], ["LEADS Incremento 2026vs2025", "LEADS 2026"],
    ["CONTACTS Incremento 2024vs2025", "CONTACTS 2024"], ["CONTACTS Incremento 2024vs2025", "CONTACTS 2025"],
    ["CONTACTS Incremento 2026vs2025", "CONTACTS 2025"], ["CONTACTS Incremento 2026vs2025", "CONTACTS 2026"],
    ["LEADS % Variación_2Fechas", "LEADS Seleccionados"], ["LEADS % Variación_2Fechas", "LEADS Comparación"],
    ["CONTACTS % Variación_2Fechas", "CONTACTS Seleccionados"], ["CONTACTS % Variación_2Fechas", "CONTACTS Comparación"],
    ["LEADS % Variación 2025vs2026", "LEADS 2025"], ["LEADS % Variación 2025vs2026", "LEADS 2026"],
    ["LEADS % Variación 2026vs2025", "LEADS 2025"], ["LEADS % Variación 2026vs2025", "LEADS 2026"],
    ["CONTACTS % Variación 2025vs2026", "CONTACTS 2026"], ["CONTACTS % Variación 2025vs2026", "CONTACTS 2024"],
    ["CONTACTS % Variación 2026vs2025", "CONTACTS 2025"], ["CONTACTS % Variación 2026vs2025", "CONTACTS 2026"],
    ["LEADS % Variación_PreviousYear", "LEADS Seleccionados"], ["LEADS % Variación_PreviousYear", "LEADS Previous Year Dinámico"],
    ["CONTACTS % Variación_PreviousYear", "CONTACTS_Particular"], ["CONTACTS % Variación_PreviousYear", "CONTACTS Previous Year Dinámico"]
  ],
  dimensiones: [
    { tabla: "Tabla_Curso", columna: "Curso", desc: "Curso académico (2024/2025, 2025/2026, 2026/2027)" },
    { tabla: "Tabla_Ciudad_Actual", columna: "Ciudad actual", desc: "Ciudad de residencia actual" },
    { tabla: "Tabla_Ciudad_Interés", columna: "Ciudades de interés", desc: "Ciudades de interés del lead/contact" },
    { tabla: "Tabla_Residencia_Actual_CONTACTS", columna: "Residencia actual", desc: "Residencia actual del contact" },
    { tabla: "Tabla_Residencia_Escogida_LEADS", columna: "Residencia escogida", desc: "Residencia escogida por el lead" },
    { tabla: "Tabla_Residencia_Interés", columna: "Residencias de interés", desc: "Residencias de interés" },
    { tabla: "Tabla_Fuente_PC", columna: "Fuente_Agrupada", desc: "Fuente agrupada del posible cliente" },
    { tabla: "Tabla_Origen", columna: "Origen/Campaña Posibles Clientes", desc: "Origen o campaña de captación" },
    { tabla: "Calendario", columna: "Date", desc: "Fecha (relacionada con Fecha creación)" }
  ]
};

function _norm(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function _puntuar(medida, consultaNorm, terminos) {
  var texto = _norm(medida.nombre + " " + medida.familia + " " +
                    (medida.curso || "") + " " + (medida.tipo || "") + " " + medida.desc);
  var score = 0;
  for (var i = 0; i < terminos.length; i++) {
    var t = terminos[i];
    if (!t) continue;
    if (texto.indexOf(t) !== -1) score += 1;
    if (_norm(medida.familia) === t) score += 2;
    // Bonus por año explícito en la consulta
    if (medida.anio && t === String(medida.anio)) score += 3;
    if (medida.curso && medida.curso.indexOf(t) !== -1) score += 3;
  }
  if ((consultaNorm.indexOf("conversion") !== -1 || consultaNorm.indexOf("tasa") !== -1)
      && medida.familia === "CR") score += 2;
  return score;
}

function extraerSubgrafo(consulta, topK) {
  topK = topK || 6;
  var consultaNorm = _norm(consulta);
  var terminos = consultaNorm.split(/\s+/).filter(Boolean);

  var puntuadas = GRAFO_RESA.medidas
    .map(function (m) { return { m: m, score: _puntuar(m, consultaNorm, terminos) }; })
    .filter(function (x) { return x.score > 0; })
    .sort(function (a, b) { return b.score - a.score; })
    .slice(0, topK);

  var seleccion = {};
  puntuadas.forEach(function (x) { seleccion[x.m.nombre] = x.m; });

  var cambio = true;
  while (cambio) {
    cambio = false;
    GRAFO_RESA.deriva.forEach(function (par) {
      if (seleccion[par[0]] && !seleccion[par[1]]) {
        var base = GRAFO_RESA.medidas.find(function (m) { return m.nombre === par[1]; });
        if (base) { seleccion[par[1]] = base; cambio = true; }
      }
    });
  }

  return _serializar(seleccion, consulta);
}

function _serializar(seleccion, consulta) {
  var nombres = Object.keys(seleccion);
  if (nombres.length === 0) {
    var dims = GRAFO_RESA.dimensiones.map(function (d) {
      return "  - " + d.tabla + "[" + d.columna + "]: " + d.desc;
    }).join("\n");
    return "MODELO DE DATOS (no se identificó una medida concreta).\n" +
           "Tabla de hechos: Leads_Contacts. Dimensiones disponibles:\n" + dims;
  }

  var lineas = ["MODELO DE DATOS RELEVANTE PARA ESTA CONSULTA:", ""];
  lineas.push("Tabla de hechos: Leads_Contacts (un registro por correo electrónico).");
  lineas.push("");
  lineas.push("Medidas relevantes:");
  nombres.forEach(function (n) {
    var m = seleccion[n];
    var filtros = [];
    if (m.tipo) filtros.push("Tipo de registro = " + m.tipo);
    if (m.curso) filtros.push("Curso = " + m.curso);
    var fstr = filtros.length ? "  [filtros: " + filtros.join("; ") + "]" : "";
    lineas.push("  - " + m.nombre + ": " + m.desc + fstr);
  });

  var cadenas = GRAFO_RESA.deriva.filter(function (par) {
    return seleccion[par[0]] && seleccion[par[1]];
  });
  if (cadenas.length) {
    lineas.push("");
    lineas.push("Dependencias entre medidas:");
    cadenas.forEach(function (par) {
      lineas.push("  - '" + par[0] + "' se calcula a partir de '" + par[1] + "'");
    });
  }

  lineas.push("");
  lineas.push("Puedes agrupar/filtrar por: " +
    GRAFO_RESA.dimensiones.map(function (d) { return d.columna; }).join(", ") + ".");

  return lineas.join("\n");
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { extraerSubgrafo: extraerSubgrafo, GRAFO_RESA: GRAFO_RESA };
}
