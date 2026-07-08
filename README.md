# Asistente analítico CRM (demo)

Chatbot que permite a un empleado preguntar en lenguaje natural y recibir tablas, gráficos interactivos y conclusiones. Toda la aplicación vive
en un único `index.html` que se sirve por HTTP local; el "cerebro" se reparte entre la **API
Responses de OpenAI** (clasificación, planificación, generación de código y conclusiones) y
**Pyodide** (ejecución del código Pandas en el navegador). Los prompts de cada paso son archivos
`.txt` externos cargados en tiempo de arranque.

> Requisito: servir con `python -m http.server 8000` (no `file://`) y tener `Leads_Contacts.csv`
> y los `context_*.txt` en la misma carpeta que `index.html`.

---

## 1. Arranque (`initChat`)

El usuario introduce su API key de OpenAI y pulsa *Conectar*. `initChat` lanza tres tareas en
paralelo con `Promise.all` y solo revela el chat cuando todas terminan:

1. **`loadPrompts`** — descarga en paralelo los archivos de `PROMPT_FILES` (`context_router.txt`,
   `context_clarify.txt`, `context_modelo_datos.txt`, `context_general.txt`,
   `context_conclusiones.txt`, `context_explicacion.txt`) y los guarda en la global `prompts`,
   indexados por clave. Cada `.txt` es el *system prompt* de un paso distinto del pipeline.
2. **`ensureConversation`** — recupera o crea el hilo de OpenAI (ver sección 2).
3. **Cadena de Pyodide** — `initPyodide` (carga el runtime), `loadPyodidePackages` (instala
   `pandas` y `numpy`), `installRuntimeHelpers` (inyecta helpers Python: parser de fechas en
   español `__parse_fechas_es__`, `__reset_resultado__`, `__serialize_resultado__`),
   `installCityCoords` (inyecta `CIUDADES_ES_COORDS` y `coords_ciudad`) y `loadPrimaryCsv`
   (carga `Leads_Contacts.csv` como el DataFrame global de Pyodide `leads_contacts`, parseando
   `Fecha creación`).

Tras cargar el CSV, `injectColumnValuesIntoContext` añade al final de `prompts.general` la lista
cerrada de valores reales de cada columna categórica, e `injectCityListIntoContext` añade la lista
de ciudades con coordenadas. Así el generador de código conoce los valores exactos sobre los que
puede filtrar.

**Variables globales tras el arranque:**

- `apiKey` — la clave introducida; se usa en cada llamada HTTP.
- `prompts` — diccionario `{clave: texto}` con los system prompts.
- `pyodide` — instancia del runtime; mantiene el estado Python (incluido `leads_contacts`) durante
  toda la sesión.
- `loadedCsvs` — `Set` con los CSV ya cargados, para no recargarlos.
- `conversationId` / `lastResponseId` — identifican el hilo persistente de OpenAI.
- `sessionContext` / `turnHistory` — memoria de la conversación (ver sección 3).

---

## 2. El hilo de OpenAI (`ensureConversation` / `createConversation`)

La demo usa la **Conversations API** de OpenAI para dar memoria de servidor a las consultas de
datos. `ensureConversation`:

- Lee de `localStorage` un `conversationId` previo y su marca de tiempo. Si tiene **menos de 48 h**
  (`SESSION_MAX_AGE_MS`), reutiliza ese hilo y restaura `sessionContext` y `turnHistory` desde
  `localStorage`. Así, recargar la página no pierde el contexto.
- Si está caducado o no existe, llama a `createConversation`, que hace `POST /v1/conversations`,
  guarda el `id` devuelto en `conversationId` y lo persiste en `localStorage`.

Cada vez que se resuelve una consulta, `touchSession` actualiza la marca de tiempo para mantener
viva la sesión.

---

## 3. La memoria de la conversación (dos capas)

La memoria del lado del cliente es independiente del hilo de OpenAI y sirve para enriquecer los
prompts de los pasos que **no** van al hilo:

- **`sessionContext`** (objeto `{slot: valor}`) — contexto acotado: curso, ciudad, métrica, etc.,
  rellenado por el paso *clarify* y por `rememberQueryParams` (que infiere curso/métrica del texto
  con expresiones regulares). Se persiste en `localStorage`.
- **`turnHistory`** (array) — historial de turnos. `recordTurnInHistory` guarda por cada consulta
  resuelta un objeto `{q, r, ts}` con la pregunta y un resumen breve del resultado
  (`summarizeResultForMemory`). Se conserva un máximo de `MAX_HISTORY_TURNS = 40` turnos.

`buildFullMemoryText` combina ambas en un bloque de texto que se inyecta en el *input* del
planificador y del generador de código. Del historial solo se inyectan los últimos
`HISTORY_INJECT_TURNS = 12` turnos, para no saturar el contexto.

---

## 4. El motor de llamadas a OpenAI (`callModel`)

Todas las llamadas al modelo pasan por `callModel(messages, systemPrompt, opts)`, que hace
`POST /v1/responses` con este cuerpo:

- **`model`** — `opts.model || "gpt-4o"`. Todos los pasos usan `gpt-4o`.
- **`instructions`** — el system prompt (`systemPrompt`), normalmente uno de los `context_*.txt`.
- **`input`** — los mensajes, mapeados al formato Responses: rol `user` usa `input_text` y rol
  `assistant` usa `output_text`.
- **`max_output_tokens`** — `opts.maxTokens` (varía por paso, ver tabla más abajo).
- **`temperature`** — solo se añade si `opts.temperature` es numérica.
- **`store`** — igual a `opts.threaded` (por defecto `true`). Controla si la respuesta se persiste
  en el hilo.
- **`truncation: "auto"`** y, si el modelo lo soporta, `prompt_cache_retention: "24h"`.

**El parámetro clave es `threaded`** (`store`):

- Si `threaded` es `true` y existe `conversationId`, se añade `conversation: conversationId`: la
  llamada entra en el hilo persistente y el modelo recuerda las consultas de datos anteriores. Si
  no hay hilo pero sí `lastResponseId`, encadena con `previous_response_id`. Al volver, guarda el
  nuevo `id` en `lastResponseId`.
- Si `threaded` es `false`, la llamada es **stateless**: no toca el hilo. Esto es deliberado para
  los pasos clasificadores (router, clarify, planificador), cuya salida es JSON de fontanería que
  contaminaría el contexto de datos.

Si OpenAI rechaza un parámetro (`error.param`), `callModel` lo elimina y reintenta una vez —así la
demo degrada con elegancia si un parámetro no está soportado.

`extractOpenAIText` recupera el texto de la respuesta, ya sea de `output_text` directo o
recorriendo los bloques `output[].content[]`.

---

## 5. El flujo de un mensaje (`sendMessage`)

Cuando el usuario envía un mensaje, `sendMessage` pone `busy = true`, pinta el mensaje y arranca el
pipeline. El recorrido es:

### Paso 1 — Enrutado (`routeMessage`, `context_router.txt`)

Llamada **stateless** (`threaded: false`, `temperature: 0.2`, `maxTokens: 400`). El router
devuelve un JSON con `tipo`: `saludo`, `modelo` o `datos`.

- **`saludo`** → se muestra la respuesta del router (o un saludo de reserva) y termina el turno.
- **`modelo`** → `answerModelQuery` responde una duda sobre el esquema usando
  `context_modelo_datos.txt` (`temperature: 0.5`, `maxTokens: 1500`); esta es una respuesta de
  texto, no genera código.
- **`datos`** → continúa al paso 2.

Si el router falla o no es parseable, se asume `datos` por defecto.

### Paso 2 — Planificación multi-consulta (`runDataTurn` → `planRequests`)

Llamada **stateless** (`threaded: false`, `temperature: 0.1`, `maxTokens: 600`) con un prompt de
planificador embebido en el código. Recibe el mensaje del usuario más la memoria
(`buildFullMemoryText`) y devuelve un array `peticiones`:

- La regla central es **no dividir salvo que haya peticiones realmente distintas**. Una comparación
  (Madrid vs Barcelona) es siempre **una sola** petición.
- Si hay una única petición → `runDataPipeline`. Si hay varias → `runDataBatch`, que las resuelve
  secuencialmente, una a una, mostrando una cabecera por paso.

### Paso 3 — Slot-filling / Clarify (`runDataPipeline` → `planSlots`)

Antes de generar código, `planSlots` (stateless, `temperature: 0.5`, `maxTokens: 700`,
`context_clarify.txt`) detecta si faltan datos imprescindibles (p. ej. el curso). Si faltan:

- Se crea la global **`pendingClarify`** `{userQuery, missing, answered, total}` y se pregunta al
  usuario slot a slot con botones (`askNextSlot`). El turno queda en pausa (`busy` se mantiene).
- Cada respuesta (`answerClarify`) rellena `sessionContext[slot]` y guarda en `pendingClarify.answered`.
- Cuando no quedan slots, `finalizeClarify` reanuda el pipeline llamando a `answerDataQuery` con los
  slots ya respondidos.

Los slots que ya están en `sessionContext` se filtran y no se vuelven a preguntar.

### Paso 4 — Generación de código (`answerDataQuery`, `context_general.txt`)

Esta es la **única llamada threaded** (`threaded: true`, `temperature: 0.5`, `maxTokens: 1800`):
entra en el hilo de OpenAI para que el modelo recuerde las consultas de datos previas.

`buildEnrichedQuery` arma el *input*: memoria (`buildFullMemoryText`) + consulta actual + contexto
de slots respondidos. El system prompt es `context_general.txt`, que obliga al modelo a responder
**solo** con un bloque ` ```python ... ``` ` que asigna el resultado a la variable `resultado`
(escalar, DataFrame, Series, dict de KPIs o dict Plotly con `"__plotly__": True`).

`extractPythonCode` extrae el bloque de código de la respuesta.

### Paso 5 — Ejecución en Pyodide (`runPython`)

- `ensureTablesLoaded` garantiza que `leads_contacts` esté cargado en Pyodide.
- `runPython` primero ejecuta `__reset_resultado__()` (borra cualquier `resultado` previo), luego
  ejecuta el código del modelo con `runPythonAsync` **a scope global** (sin envolverlo en `try`,
  para que las variables vivan en el espacio global y no haya `NameError`), y finalmente llama a
  `__serialize_resultado__()` para convertir `resultado` a JSON.
- El JSON resultante se etiqueta con un `kind` (`number`, `text`, `dataframe`, `dict`, `plotly`,
  `none` o `error`) que decide cómo se renderiza.

**Reintento automático:** si la ejecución falla, `retryWithModelFix` reenvía al modelo (threaded,
mismo prompt) el código y el traceback pidiendo una corrección, y reejecuta una vez. Si vuelve a
fallar, `friendlyError` muestra un mensaje amable sin tecnicismos.

### Paso 6 — Render del resultado (`appendResult` → `renderResult`)

Según el `kind`:

- **número** → tarjeta KPI grande.
- **texto** → prosa con Markdown.
- **dataframe / dict** → tabla HTML alineada.
- **plotly** → se crea un `<div class="plot-container">` con id único y, tras insertarlo,
  `renderPlotlyInto` dibuja la figura con `Plotly.newPlot`. Para gráficos no geográficos se aplica
  un `hoverlabel` legible con `namelength: -1` (no trunca nombres) y, tras renderizar,
  `unclipPlotHover` elimina el recorte de la capa de hover y de la leyenda para que no las corte la
  celda del chat. Los mapas (`scattermapbox`/`densitymapbox`) pasan además por `beautifyMap`.

### Paso 7 — Memoria del turno

Si la ejecución fue correcta: `rememberQueryParams` actualiza `sessionContext` con curso/métrica
inferidos, `recordTurnInHistory` añade el turno a `turnHistory`, `rememberAnsweredSlots` consolida
los slots respondidos y `touchSession` renueva la marca de tiempo de la sesión. La global
`lastTurn` guarda la última consulta enriquecida (útil para reintentos y conclusiones).

### Paso 8 — Explicación y conclusión (opcionales)

- **Explicación** (`appendExplanationTo`, `context_explicacion.txt`, stateless, `temperature: 0.3`,
  `maxTokens: 700`): panel colapsable que explica qué hace el código generado.
- **Conclusión** (`appendConclusionTo`, `context_conclusiones.txt`, stateless, `temperature: 0.6`,
  `maxTokens: 700`): solo si el interruptor *Conclusiones* está activo. Antes de enviar los datos
  al modelo, `buildConclusionPayload` los **pseudonimiza** (`serializeResultForLLM` sustituye
  categorías de texto por alias genéricos tipo "Ciudad A"; los números se mantienen reales y los
  identificadores personales se descartan). El modelo redacta usando los alias y, al volver,
  `deanonymizeText` revierte los alias a los nombres reales antes de mostrar el texto.

---

## 6. Resumen de parámetros OpenAI por paso

| Paso | System prompt | `threaded` (`store`) | temperatura | `max_output_tokens` |
|------|---------------|----------------------|-------------|---------------------|
| Router | `context_router.txt` | `false` | 0.2 | 400 |
| Modelo de datos | `context_modelo_datos.txt` | `true` (por defecto) | 0.5 | 1500 |
| Planificador | (prompt embebido) | `false` | 0.1 | 600 |
| Clarify | `context_clarify.txt` | `false` | 0.5 | 700 |
| Generación de código | `context_general.txt` | `true` | 0.5 | 1800 |
| Reintento de código | `context_general.txt` | `true` | 0.5 | 1800 |
| Explicación | `context_explicacion.txt` | `true` (por defecto) | 0.3 | 700 |
| Conclusión | `context_conclusiones.txt` | `true` (por defecto) | 0.6 | 700 |

> Regla de oro de threading: **solo las consultas de datos (generación + reintento) entran en el
> hilo de OpenAI**. Router, planificador y clarify van *stateless* para no contaminar el hilo con
> JSON de fontanería; explicación y conclusión reciben los datos ya pseudonimizados en su propio
> *input*.

---

## 7. Mapa de variables globales

| Global | Qué guarda | Cuándo cambia |
|--------|------------|---------------|
| `apiKey` | Clave de OpenAI | Al conectar |
| `prompts` | System prompts `{clave: texto}` | Arranque (`loadPrompts`) |
| `pyodide` | Runtime Python + `leads_contacts` | Arranque; persiste toda la sesión |
| `loadedCsvs` | CSV ya cargados | Al cargar cada CSV |
| `conversationId` | Hilo de OpenAI | `ensureConversation` / `createConversation` |
| `lastResponseId` | Último `response.id` threaded | Cada llamada threaded |
| `sessionContext` | Contexto acotado `{slot: valor}` | Clarify, `rememberQueryParams` |
| `turnHistory` | Historial de turnos (máx. 40) | `recordTurnInHistory` |
| `pendingClarify` | Estado del slot-filling en curso | Durante clarify |
| `lastUserQuery` / `lastTurn` | Última consulta / turno enriquecido | Tras cada consulta |
| `busy` | Bloqueo de envíos concurrentes | Inicio/fin de cada turno |
| `supportsCacheRetention` | Si el modelo acepta `prompt_cache_retention` | Si OpenAI lo rechaza |

`sessionContext`, `turnHistory` y `conversationId` se reflejan en `localStorage` para sobrevivir a
recargas dentro de la ventana de 48 h. `startNewChat` los borra y crea un hilo nuevo.