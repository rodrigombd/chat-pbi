# Asistente analítico CRM (demo) — Versión Claude

Chatbot que permite a un empleado preguntar en lenguaje natural y recibir tablas, gráficos interactivos y conclusiones. Toda la aplicación vive en un único `index.html` que se sirve por HTTP local; el "cerebro" se reparte entre la **API Messages de Anthropic (Claude)** (clasificación, planificación, generación de código y conclusiones) y **Pyodide** (ejecución del código Pandas en el navegador). Los prompts de cada paso son archivos `.txt` externos cargados en tiempo de arranque.

> Requisito: servir con `python -m http.server 8000` (no `file://`) y tener `Leads_Contacts.csv` y los `context_*.txt` en la misma carpeta que `index.html`.

---

## 1. Arranque (`initChat`)

El usuario introduce su API key de Anthropic y pulsa *Conectar*. `initChat` lanza una secuencia de carga y solo revela el chat cuando todas terminan satisfactoriamente:

1. **`loadPrompts`** — Descarga los archivos de `PROMPT_FILES` (`context_router.txt`, `context_clarify.txt`, `context_modelo_datos.txt`, `context_general.txt`, `context_conclusiones.txt`) y los guarda en la global `prompts`, indexados por clave. Cada `.txt` es el *system prompt* de un paso distinto del pipeline.
2. **Cadena de Pyodide** — `initPyodide` (carga el runtime), `loadPyodidePackages` (instala `pandas` y `numpy`), `installRuntimeHelpers` (inyecta helpers Python: parser de fechas en español `__parse_fechas_es__`, `__reset_resultado__`, `__serialize_resultado__` y formateo seguro JSON) y `loadPrimaryCsv` (carga `Leads_Contacts.csv` como el DataFrame global de Pyodide `leads_contacts`, parseando `Fecha creación`).

**Variables globales tras el arranque:**

* `apiKey` — La clave introducida; se usa en cada llamada HTTP a Anthropic.
* `prompts` — Diccionario `{clave: texto}` con los system prompts.
* `pyodide` — Instancia del runtime; mantiene el estado Python (incluido `leads_contacts`) durante toda la sesión.
* `loadedCsvs` — `Set` con los CSV ya cargados, para no recargarlos inútilmente.
* `chatHistory` — Arreglo en memoria que guarda el contexto de la conversación (ver sección 2).

---

## 2. La memoria de la conversación (`chatHistory`)

A diferencia de las APIs gestionadas por hilos, esta versión mantiene la memoria del lado del cliente utilizando el arreglo **`chatHistory`**.

* Cada vez que el usuario hace una consulta de datos y el asistente genera código, ambos mensajes se empujan a este arreglo (roles `user` y `assistant`).
* Para evitar superar el límite de tokens de contexto, la función `trimHistory()` recorta el historial manteniendo únicamente los últimos `MAX_HISTORY = 12` mensajes.
* La memoria **no es persistente** (no utiliza `localStorage`), por lo que al recargar la página se inicia una sesión completamente en blanco.

---

## 3. El motor de llamadas a Anthropic (`callModel`)

Todas las llamadas al modelo pasan por `callModel(messages, systemPrompt, opts)`, que hace un `POST /v1/messages` a la API de Anthropic con las siguientes particularidades:

* **Modelo:** Se utiliza por defecto `claude-haiku-4-5-20251001` (u otro definido en `MODEL_ID`).
* **Cabeceras:** Incluye `x-api-key`, `anthropic-version` (`2023-06-01`), y la cabecera `anthropic-dangerous-direct-browser-access: true` requerida para llamadas directas desde el frontend.
* **Prompt de Sistema:** Se pasa a través del parámetro `system` como un bloque de texto (con soporte `ephemeral` para caché nativa de Anthropic si aplica).
* **Mensajes:** Se formatean para encajar con el rol esperado por la API (`user` o `assistant`), inyectando también directivas de control de caché en el último mensaje de usuario para optimizar el procesamiento repetitivo.

---

## 4. El pipeline de un mensaje (`sendMessage`)

El flujo de procesamiento es estrictamente secuencial y cada paso utiliza su propio *system prompt* para optimizar la ventana de contexto.

```text
  router  →  saludo  ────────────────────────────────────────────────────────►
           \─►  modelo  → respuesta texto ───────────────────────────────────►
           \─►  datos  → clarify  → (slots?) → ejecutar python  →  result
                                                                       │
                                                              (¿Toggle Activo?)
                                                                       ▼
                                                             context_conclusiones
                                                                       │
                                                                       ▼
                                                                   conclusión

```

### Paso 1 — Enrutado (`routeMessage`, `context_router.txt`)

Llamada **stateless** (sin historial). El router decide la intención devolviendo un JSON con la propiedad `tipo`:

* **`saludo`** → Se muestra la respuesta del router (o un saludo genérico) y el turno termina.
* **`modelo`** → Pasa por `answerModelQuery`, respondiendo dudas técnicas sobre el esquema utilizando `context_modelo_datos.txt`.
* **`datos`** → Pasa a la fase de planificación de la consulta.

### Paso 2 — Clarify / Slot-filling (`planSlots`, `context_clarify.txt`)

Llamada **stateless**. Se evalúa si a la consulta del usuario le faltan datos críticos (por ejemplo, definir el "curso" o el "tipo de registro").

* Si faltan datos, se activa la global `pendingClarify` y el chatbot pausa su ejecución para preguntar con botones interactivos (`askNextSlot`).
* El usuario interactúa hasta llenar los *slots*.
* Una vez completados, se reanuda la generación de código pasando los *slots* resueltos como contexto enriquecido (`buildEnrichedQuery`).

### Paso 3 — Generación de código (`answerDataQuery`, `context_general.txt`)

Esta es la **única llamada con estado** que empuja datos al `chatHistory`. Recibe el prompt enriquecido (pregunta + slots acotados) y usa `context_general.txt` para instruir al modelo a responder exclusivamente con un bloque de código Python ejecutable que asigne su respuesta final a una variable llamada `resultado`.

### Paso 4 — Ejecución en Pyodide y Reintento Automático (`runPython`)

* Se asegura que las dependencias y tablas requeridas están cargadas (`ensureTablesLoaded`).
* Se limpia el entorno (`__reset_resultado__()`), se ejecuta el bloque generado, y se serializa el output (`__serialize_resultado__()`) a un formato JSON estructurado con una propiedad `kind` (`number`, `dataframe`, `plotly`, `dict`, etc.).
* **Reintento:** Si Python lanza un error, `retryWithModelFix` captura el *Traceback*, lo inserta temporalmente en el historial, y pide al modelo que corrija su propio código defectuoso.

### Paso 5 — Renderizado visual (`renderResult`)

La salida generada toma distintas formas según el `kind` devuelto por Pyodide:

* **`number`**: Un valor escalar destacado (KPI).
* **`dataframe` / `dict**`: Tablas HTML estructuradas.
* **`plotly`**: Una visualización interactiva generada con la librería `Plotly.newPlot`.

### Paso 6 — Conclusión analítica (Opcional)

Si el interruptor de conclusiones está encendido, se llama a `appendConclusionTo`.
Para proteger datos, `serializeResultForLLM` **pseudonimiza** las categorías de texto devolviendo *alias* (ej. "Ciudad A", "Campaña B"). El modelo redacta un breve análisis leyendo esos alias y, al retornar el texto final, la aplicación revierte de forma local la pseudonimización (`deanonymizeText`) antes de imprimirlo en pantalla.

---

## 5. Resumen de parámetros Anthropic por paso

| Paso | System prompt | Historial / Stateful | `max_tokens` |
| --- | --- | --- | --- |
| **Router** | `context_router.txt` | No (`stateless`) | 300 |
| **Modelo de datos** | `context_modelo_datos.txt` | No (`stateless`) | 1200 |
| **Clarify** | `context_clarify.txt` | No (`stateless`) | 600 |
| **Generación de código** | `context_general.txt` | **Sí** (usa `chatHistory`) | 1800 |
| **Reintento de código** | `context_general.txt` | **Sí** (usa `chatHistory`) | 1800 |
| **Conclusión** | `context_conclusiones.txt` | No (`stateless`) | 500 |

---

## 6. Mapa de variables globales

| Variable | Descripción | Ciclo de vida / Actualización |
| --- | --- | --- |
| `apiKey` | Clave autenticación API Anthropic | Se asigna en `initChat` |
| `prompts` | Diccionario de system prompts | Cargado una sola vez en el arranque |
| `pyodide` | Entorno Python en WebAssembly | Persiste vivo y mantiene estado durante toda la sesión |
| `chatHistory` | Arreglo de contexto para consultas de datos | Empuja mensajes tras `answerDataQuery` y reintentos (max 12 elementos) |
| `loadedCsvs` | Archivos de datos disponibles | Se actualiza al llamar `loadCsv` |
| `pendingClarify` | Estado del slot-filling | Se establece si `planSlots` detecta lagunas en la consulta |
| `lastUserQuery` / `lastTurn` | Metadatos de la última consulta procesada | Sobrescrito al iniciar la generación de una nueva respuesta |
| `busy` | Semáforo de bloqueo de UI | Evita envíos concurrentes mientras el bot "piensa" |
