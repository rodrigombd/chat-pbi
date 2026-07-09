# Asistente analítico CRM — RESA (demo)

> **Rama: modelo multi-tabla (económico + dimensionamiento)**
>
> Esta rama extiende el asistente de una única tabla de hechos (`Leads_Contacts`) a un
> **modelo de cuatro tablas** que incorpora la dimensión económica y de capacidad de las
> residencias. 

Chatbot que permite a un empleado preguntar en lenguaje natural sobre los datos de captación
y de explotación de las residencias de estudiantes RESA, y recibir tablas, gráficos interactivos
y conclusiones.

La demo sigue siendo un sistema **híbrido de dos piezas**:

1. **Frontend** (`frontend/index.html`) — una única página que concentra toda la lógica de la
   aplicación. El "cerebro" de generación se reparte entre la **API Responses de OpenAI**
   (orquestación por *tool calling*, clarify, generación de código Pandas, explicaciones y
   conclusiones) y **Pyodide** (ejecución del código Pandas **en el navegador**, sin backend de
   datos). Los *system prompts* de cada paso son archivos `context_*.txt` externos cargados al
   arrancar.
2. **Backend GraphRAG** (`graphrag/`) — un servicio **FastAPI** que expone `/retrieve`. Recupera de
   **Neo4j**, mediante *embeddings* y expansión del grafo, el **subgrafo relevante** del modelo
   de datos (tablas, columnas y medidas) para cada consulta, y lo devuelve como texto listo para
   inyectar como contexto.

> El backend GraphRAG es **opcional para arrancar**, pero en esta rama es **prácticamente
> imprescindible**: el modelo de datos ya no cabe en el contexto estático, y sin recuperación
> dinámica el generador de código no sabrá que existen `economics`, `sizing` ni
> `maestro_residencias`.

---

## 1. Qué cambia respecto a la rama anterior

### 1.1. De una tabla a cuatro

La rama anterior trabajaba sobre un único DataFrame de hechos, `leads_contacts`. Ahora conviven
cuatro tablas, todas cargadas en Pyodide como variables globales homónimas:

| Tabla | Rol | Grano | Columnas |
|-------|-----|-------|----------|
| `leads_contacts` | hechos | Una fila por solicitud (lead o contact) | Las de captación del CRM |
| `economics` | hechos | Una fila por residencia y mes | `codigo_residencia`, `fecha` (MM/AAAA), `ingresos`, `costes` |
| `sizing` | hechos | Una fila por residencia y tipo de habitación | `codigo_residencia`, `num_rooms`, `room_type` (`S`/`D`/`Q`) |
| `maestro_residencias` | dimensión | Una fila por residencia | `codigo_residencia`, `nombre_residencia` |

Las tres tablas nuevas se enlazan entre sí —y con `leads_contacts`— por la clave
**`codigo_residencia`**.

### 1.2. Tres medidas nuevas (familia `ECO`)

Se suman a la familia `CR` (conversión) ya existente. Como el modelo original es de Power BI,
sus fórmulas se almacenan en el grafo **expresadas en DAX**, y el generador de código las
**traduce a Pandas** en tiempo de ejecución (no se ejecuta DAX en ningún momento).

| Medida | Fórmula (DAX, tal como vive en el grafo) | Tabla(s) |
|--------|------------------------------------------|----------|
| `ECO Margen` | `SUMX(economics, economics[ingresos] - economics[costes])` | `economics` |
| `ECO TotalRooms` | `SUM(sizing[num_rooms])` | `sizing` |
| `ECO MargenPorHabitacion` | `DIVIDE([ECO Margen], [ECO TotalRooms], 0)` | `economics` + `sizing` |

`ECO MargenPorHabitacion` es la primera **medida cruzada** del proyecto: depende de las otras dos
(`DERIVA_DE`) y necesita un *join* por `codigo_residencia`.

### 1.3. Normalización de residencias en `Leads_Contacts` (cambio de datos, no de código)

Este es el cambio **menos visible y más importante**. En la rama anterior, las columnas de
residencia de `Leads_Contacts` guardaban el **nombre** de la residencia (`"As Burgas"`), mientras
que `economics` y `sizing` usan el **código** (`"R002"`). Sin clave común, ningún *join* era
posible.

Se ha ejecutado una migración única (`data/convertir_residencias_a_codigo.py`) que sustituye el
nombre por su código en estas columnas, usando `maestro_residencias` como diccionario:

- `Residencias_actual_corregido`
- `Residencias_interes_corregido`
- `Residencia escogida`

**Consecuencias que debes conocer:**

- Esas columnas ahora contienen `R002`, no `As Burgas`. Para mostrar el nombre al usuario hay que
  hacer `merge` con `maestro_residencias`.
- Los valores que **no** son residencias reales (`Ninguno`, `Sin info`, `Cualquiera`) se han dejado
  intactos a propósito. `---` sí se convierte, porque existe en el maestro como `R001`.
- El script deja una copia de seguridad `Leads_Contacts.csv.bak` antes de sobrescribir.

> **Aviso de encoding.** Tanto `maestro_residencias.csv` como algunos valores de `Leads_Contacts.csv`
> arrastraban *mojibake* (doble codificación UTF-8: `"Málaga"` almacenado como `"MÃ¡laga"`), además
> de caracteres invisibles residuales (`\xa0` *non-breaking space*, `\xad` *soft hyphen*) en
> `Damià Bonet` y `Giner de los Ríos`. El script de migración normaliza ambos lados antes de
> comparar. Si vuelves a exportar el maestro desde origen, **verifica el encoding** o el *join*
> fallará en silencio para esos nombres.

### 1.4. Grafo: cuatro scripts numerados y ejecución ordenada

Antes había un único `grafo_resa.cypher`. Ahora son cuatro, **numerados porque el orden es
obligatorio**:

```
graphrag/
├── 01_grafo_leads_contacts.cypher     # ← el ÚNICO con "MATCH (n) DETACH DELETE n"
├── 02_grafo_economics.cypher
├── 03_grafo_sizing.cypher             # ← contiene la medida cruzada; exige que 02 exista
└── 04_grafo_maestro_residencias.cypher # ← crea las relaciones RELACIONA; exige 01, 02 y 03
```

Ejecútalos **en ese orden**. Los tres últimos usan `MERGE` y no borran nada, pero cada uno hace
`MATCH` sobre nodos creados por los anteriores.

### 1.5. Nuevas relaciones en el grafo

- **`USA_COLUMNA`** — vincula cada medida con las columnas que consume. Existía en la configuración
  de expansión pero **ninguna relación real la usaba**; ahora sí. Se ha añadido también
  retroactivamente a las medidas `CR`.
- **`RELACIONA`** — vincula las columnas clave que hacen *join* entre tablas. Se crean 12
  relaciones en `04_grafo_maestro_residencias.cypher`, conectando `codigo_residencia` de las tres
  tablas nuevas con las tres columnas de residencia de `Leads_Contacts`.

`config.py` ya expande `RELACIONA` con `("RELACIONA", "both", 2)` sobre el label `Columna`, de modo
que el subgrafo recuperado incluye las tablas al otro lado del *join*.

### 1.6. Umbral de recuperación

`score_threshold` ha bajado de `0.70` a **`0.55`**. Motivo: las descripciones de columna son cortas
y su similitud coseno queda por debajo de umbrales altos aunque sean semánticamente relevantes
(`Fecha creación` era el caso típico). Con más tablas en el grafo, un umbral alto dejaba fuera
nodos necesarios.

### 1.7. Carga de CSV en el frontend

`CSV_TABLES` pasa de ser un mapa `nombre → ruta` a un mapa `nombre → {path, sep, primary}`, porque
`maestro_residencias.csv` usa **coma** como separador y el resto usa **punto y coma**:

```javascript
var CSV_TABLES = {
  "leads_contacts":      { path: "../data/Leads_Contacts.csv",      sep: ";", primary: true },
  "economics":           { path: "../data/economics.csv",           sep: ";" },
  "sizing":              { path: "../data/sizing.csv",              sep: ";" },
  "maestro_residencias": { path: "../data/maestro_residencias.csv", sep: "," }
};
```

Solo `leads_contacts` se carga al arrancar. Las otras tres se cargan **bajo demanda**
(`ensureTablesLoaded`), la primera vez que el código generado menciona su nombre.

### 1.8. `context_general.txt` actualizado

El prompt de generación de código ya **no** afirma que exista "un único DataFrame". Ahora documenta
las cuatro tablas, la clave de *join*, el parseo de `fecha` (`format="%m/%Y"`) y la traducción a
Pandas de las tres medidas `ECO`.

---

## 2. Limitación conocida: memoria y consultas elípticas

`retrieveSubgraph` embebe la **consulta cruda del usuario** (`userText`), no el texto enriquecido con
memoria. Es deliberado: el texto enriquecido convierte el *embedding* en un centroide de la sesión y
devuelve los mismos nodos turno tras turno.

El efecto secundario es que las **preguntas elípticas de seguimiento** recuperan un subgrafo pobre:

```
Usuario: ¿cuántos leads hay en Madrid?     → embedding rico, subgrafo correcto
Usuario: ¿y de Barcelona?                  → embedding de tres palabras, sin métrica
```

El paso *clarify* sí recibe la memoria completa, así que la desambiguación de *slots* funciona; lo
que se degrada es la **recuperación del subgrafo**. Con una sola tabla apenas se notaba. Con cuatro
tablas y un umbral de `0.55`, el riesgo de recuperar nodos de la tabla equivocada aumenta.

**Pendiente:** reescritura de la consulta sobre `instruccion_enriquecida` para resolver la elipsis
antes de embeber, y re-recuperación tras el clarify con los *slots* ya resueltos.

---

## 3. Estructura del proyecto

```
chat-pbi/
├── .gitignore
├── README.md
├── requirements.txt
│
├── backend/
│   ├── prompts.json
│   └── tools.json
│
├── data/
│   ├── Leads_Contacts.csv              # Dataset principal (residencias ya como código)
│   ├── economics.csv                   # sep=";"
│   ├── sizing.csv                      # sep=";"
│   ├── maestro_residencias.csv         # sep="," ← ojo al separador
│   └── convertir_residencias_a_codigo.py   # Migración única nombre → código
│
├── evals/
│   ├── build_artifacts.py
│   ├── regression_set.json
│   └── run_evals.py
│
├── frontend/                # ← se sirve por HTTP; es lo que abre el navegador
│   ├── index.html
│   ├── context_router.txt
│   ├── context_clarify.txt
│   ├── context_modelo_datos.txt
│   ├── context_general.txt
│   ├── context_conclusiones.txt
│   └── context_explicacion.txt
│
└── graphrag/                # ← backend FastAPI de recuperación
    ├── .env                 # credenciales Neo4j + OpenAI (NO se versiona)
    ├── api.py               # FastAPI: /health y /retrieve
    ├── config.py            # esquema, labels y parámetros de recuperación
    └── graph/
        ├── 01_grafo_leads_contacts.cypher
        ├── 02_grafo_economics.cypher
        ├── 03_grafo_sizing.cypher
        └── 04_grafo_maestro_residencias.cypher
    ├── requirements.txt
    ├── 01_populate_embeddings.py
    ├── 02_create_vector_index.py
    ├── 03_retrieval_graphrag.py
    ├── 04_answer.py
    └── src/
        ├── db.py
        ├── embeddings.py
        └── graph_parser.py
```

> **Dos rutas relativas importan y dependen de dónde arrancas cada servidor:**
>
> - `index.html` carga los CSV desde `../data/` y los `context_*.txt` desde su **propia carpeta**.
>   Por eso el servidor del frontend debe arrancarse **desde `frontend/`**.
> - `api.py` importa `import config` y `from src.db import get_driver`, y lee `.env` de su carpeta.
>   Por eso el backend debe arrancarse **desde `graphrag/`**.

---

## 4. Requisitos previos

- **Python 3.12** (recomendado; probado con 3.12/3.13).
- Una **API key de OpenAI** (la introduce el usuario en la pantalla de conexión del frontend; el
  backend usa la suya propia vía `.env`).
- Para el backend GraphRAG: una instancia de **Neo4j** con el grafo cargado (ver sección 6).
- Un navegador moderno. **No se puede abrir `index.html` con `file://`**: Pyodide y el `fetch` de
  los prompts requieren servirlo por HTTP.

---

## 5. Cómo ejecutar el chatbot

Necesitas **dos terminales**: backend GraphRAG (puerto 8000) y frontend (puerto 8080). Todos los
comandos asumen que empiezas en la raíz del proyecto (`chat-pbi/`).

### Terminal 1 — Backend GraphRAG (FastAPI, puerto 8000)

```powershell
cd graphrag

python -m venv venv
venv\Scripts\activate            # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

# Crea graphrag/.env con NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD y OPENAI_API_KEY

uvicorn api:app --port 8000 --reload
```

Comprueba que responde antes de seguir:

```powershell
curl http://localhost:8000/health
# Esperado: {"ok": true, "neo4j": true, "top_k": 15, "score_threshold": 0.55}
```

Plantilla de `graphrag/.env`:

```dotenv
NEO4J_URI=neo4j+s://<tu-instancia>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<tu-password>
OPENAI_API_KEY=sk-<tu-clave>
```

### Terminal 2 — Frontend (servidor HTTP estático, puerto 8080)

```powershell
cd frontend
python -m http.server 8080
```

### Abrir la aplicación

1. Ve a **`http://localhost:8080/index.html`**.
2. Introduce tu **API key de OpenAI** y pulsa **Conectar**. Durante el arranque (`initChat`) se
   cargan en paralelo los `context_*.txt`, el hilo de OpenAI, el runtime de Pyodide con `pandas` y
   `numpy`, el CSV `Leads_Contacts.csv` y el chequeo de salud del backend.
3. Empieza a preguntar. Ejemplos que ejercitan el modelo nuevo:
   - *"¿Qué margen tuvo la residencia As Burgas en enero de 2025?"*
   - *"Ranking de residencias por margen por habitación"*
   - *"Compara los leads de Madrid y Barcelona este curso"*

---

## 6. Preparar Neo4j (solo la primera vez)

Desde `graphrag/`, con el `.env` ya configurado:

```powershell
cd graphrag
```

**Paso 1 — Construye el grafo, en este orden exacto.** Desde Neo4j Browser, Aura o `cypher-shell`:

```powershell
cypher-shell -a <NEO4J_URI> -u <USER> -p <PASSWORD> -f 01_grafo_leads_contacts.cypher
cypher-shell -a <NEO4J_URI> -u <USER> -p <PASSWORD> -f 02_grafo_economics.cypher
cypher-shell -a <NEO4J_URI> -u <USER> -p <PASSWORD> -f 03_grafo_sizing.cypher
cypher-shell -a <NEO4J_URI> -u <USER> -p <PASSWORD> -f 04_grafo_maestro_residencias.cypher
```

**Paso 2 — Verifica que las relaciones de *join* se crearon.** Este chequeo es importante: si alguna
columna referenciada no existe, el `MATCH` no casa, devuelve cero filas y **no se crea ninguna
relación, sin lanzar error**.

```cypher
MATCH ()-[r:RELACIONA]->() RETURN count(r);
// Esperado: 12
```

Si devuelve `0`, revisa que los nombres de columna del script `04` coincidan exactamente con los
creados en el `01`.

**Paso 3 — Limpia los embeddings viejos.** Obligatorio si el grafo ya existía: los vectores
obsoletos persisten y contaminan la recuperación.

```cypher
MATCH (n) WHERE n:Columna OR n:Medida OR n:Valor REMOVE n.embedding;
```

**Paso 4 — Recalcula embeddings e índices:**

```powershell
python 01_populate_embeddings.py
python 02_create_vector_index.py
```

`03_retrieval_graphrag.py` es útil para **inspeccionar el subgrafo recuperado** de forma aislada
mientras depuras, sin lanzar el pipeline completo del frontend.

---

## 7. Migrar los datos de residencia (solo la primera vez)

Si tu `Leads_Contacts.csv` todavía contiene **nombres** de residencia en vez de códigos:

```powershell
cd data
python convertir_residencias_a_codigo.py
```

El script informa por consola de cuántos valores no encontró en el maestro. **Lo esperado es `0`.**
Si lista alguno, no continúes: casi siempre es un problema de encoding en el maestro.

Antes de ejecutarlo: **cierra el CSV en Excel** y pausa la sincronización de OneDrive, o fallará con
`PermissionError`.

---

## 8. El flujo de un mensaje (orquestación por *tool calling*)

`sendMessage → orchestrate` monta la memoria de sesión y llama al **router** con *tool calling*
(`context_router.txt`). El router **no** devuelve texto libre: está obligado a invocar una de **dos**
herramientas.

| Herramienta | Cuándo | Qué hace |
|-------------|--------|----------|
| `explicar_modelo_datos` | Preguntas teóricas sobre tablas/columnas/KPIs y saludos | `answerModelQuery` responde en texto usando `context_modelo_datos.txt` (aislado, no toca el hilo) |
| `ejecutar_analisis_python` | Cualquier cálculo, agregación, ranking, comparación, serie temporal o gráfico | Entra en el pipeline de datos. Se puede invocar **varias veces en paralelo** |

Si el router no invoca ninguna herramienta, hay **un reintento** con un mensaje reforzado antes de
caer, por seguridad, en `answerDataQuery`.

### Rama de datos (`answerDataQuery`)

1. **Recuperación GraphRAG** — `retrieveSubgraph(userText, null)` llama a `POST /retrieve` y obtiene
   el subgrafo. Se inyecta como contexto del generador (`wrapSubgraphContext`).
2. **Clarify** (`runClarifyAgent`, `context_clarify.txt`) — decide, usando ese mismo subgrafo, si
   faltan datos imprescindibles. Pregunta *slot* a *slot* con botones (máximo 2) y reanuda
   reutilizando el subgrafo. En modo **batch** se salta (`skipClarify: true`).
3. **Generación de código** (`context_general.txt`, **única llamada *threaded***) — el modelo
   responde solo con un bloque ```python``` que asigna a `resultado`.
4. **Ejecución en Pyodide** (`runPython`) — se resetea `resultado`, se ejecuta a scope global y se
   serializa a JSON con un `kind` (`number`, `text`, `dataframe`, `dict`, `plotly`, `none`, `error`).
   Si falla, `retryWithModelFix` reenvía código y *traceback* para una corrección y reejecuta una vez.
   La serialización pasa por `_df_to_json_safe()`, que sanea *dtypes* exóticos (`Period`) antes de
   convertir a JSON.
5. **Render** (`renderResult`) — número → tarjeta KPI; texto → Markdown; dataframe/dict → tabla;
   plotly → figura interactiva (los mapas pasan por `beautifyMap`).
6. **Explicación** (opcional) y **conclusión** (opcional). Antes de enviar datos al modelo para la
   conclusión se **pseudonimizan** las categorías de texto (los números se mantienen reales) y al
   volver se revierten los alias.

---

## 9. Memoria de la conversación

La memoria del cliente enriquece los prompts y sobrevive a recargas dentro de una ventana de
**3 horas** (`SESSION_MAX_AGE_MS`), persistida en `localStorage`.

- **`sessionContext`** `{slot: valor}` — contexto acotado (curso, ciudad, métrica…), rellenado por el
  clarify y por `rememberQueryParams`.
- **`turnHistory`** — turnos resueltos `{q, r, ts}` (máx. `MAX_HISTORY_TURNS = 60`; se inyectan los
  últimos `HISTORY_INJECT_TURNS = 16`).
- **`sessionSummary`** — cuando `turnHistory` supera `SUMMARY_TRIGGER_TURNS = 18`, los turnos más
  antiguos se comprimen (ventana deslizante), manteniendo los últimos `SUMMARY_KEEP_RECENT = 16`.

`buildFullMemoryText` combina resumen + historial reciente + contexto y lo inyecta en el *input* del
router y del generador de código.

> **Regla de threading:** solo las **consultas de datos** (generación + su reintento) entran en el
> hilo persistente de OpenAI (`store: true`). Router, clarify, explicación de modelo, explicación de
> código y conclusión corren **aislados** (`isolated: true`).
>
> **Asimetría de memoria:** al ser aisladas y no llamar a `recordTurnInHistory`, las consultas sobre
> el *modelo de datos* no dejan rastro en `turnHistory` ni en `sessionSummary`. Solo los turnos de
> datos resueltos con éxito entran en memoria.

---

## 10. Parámetros de OpenAI por paso

Todos los pasos usan **`gpt-4o`**. La compresión del resumen de sesión usa `gpt-4o-mini`. Los
*embeddings* usan `text-embedding-3-small`.

| Paso | System prompt | *Threaded* | Temperatura | `max_output_tokens` |
|------|---------------|------------|-------------|---------------------|
| Router (tool calling) | `context_router.txt` | no (aislado) | 0.2 | 700 |
| Explicar modelo de datos | `context_modelo_datos.txt` | no (aislado) | 0.5 | 1500 |
| Clarify | `context_clarify.txt` | no (aislado) | 0.1 | 500 |
| Generación de código | `context_general.txt` | **sí** | 0.5 | 1800 |
| Reintento de código | `context_general.txt` | **sí** | 0.5 | 1800 |
| Explicación de código | `context_explicacion.txt` | no (aislado) | 0.3 | 700 |
| Conclusión | `context_conclusiones.txt` | no (aislado) | 0.6 | 700 |

---

## 11. Resolución de problemas frecuentes

### Específicos de esta rama

- **`NameError: economics is not defined`** — la tabla no se cargó porque el código generado no la
  mencionó por su nombre exacto, o el CSV no está en `data/`. `ensureTablesLoaded` carga bajo demanda
  buscando el nombre de la variable en el código.
- **El *join* con `maestro_residencias` no devuelve filas** — las columnas de residencia de
  `Leads_Contacts` siguen conteniendo nombres en vez de códigos. Ejecuta la migración (sección 7).
- **El LLM filtra por `codigo_residencia == "As Burgas"`** — el modelo cree que el código *es* el
  nombre. Señal de que la migración no se ha aplicado, o de que el subgrafo recuperado no incluye
  `maestro_residencias`.
- **`MATCH ()-[r:RELACIONA]->() RETURN count(r)` devuelve 0** — algún `MATCH` del script `04` apunta
  a una columna inexistente. Revisa los nombres exactos (tildes, mayúsculas, espacios).
- **Nombres con tilde que no casan en la migración** (`Damià Bonet`, `Giner de los Ríos`) —
  *mojibake* o caracteres invisibles en `maestro_residencias.csv`. El script los normaliza; si
  reexportas el maestro, revisa el encoding.
- **`PermissionError` al escribir `Leads_Contacts.csv`** — lo tienes abierto en Excel o OneDrive lo
  está bloqueando.

### Heredados

- **`NameError: leads_contacts is not defined`** — arranca el frontend **desde `frontend/`** con
  `python -m http.server 8080` (no con `file://`) y confirma que existe `data/Leads_Contacts.csv`.
- **"Backend GraphRAG no disponible"** — `http://localhost:8000/health` no responde. Revisa que
  `uvicorn` esté arrancado **desde `graphrag/`** y que el `.env` sea correcto.
- **`Falta la variable de entorno 'NEO4J_URI'`** — falta o está mal el `graphrag/.env`.
- **`ModuleNotFoundError: config` / `src`** — estás lanzando `uvicorn` desde la carpeta equivocada.
- **Faltan archivos de contexto** — algún `context_*.txt` no está junto a `index.html`.

---

## 12. Mapa de variables globales del frontend

| Global | Qué guarda | Cuándo cambia |
|--------|------------|---------------|
| `apiKey` | Clave de OpenAI del usuario | Al conectar |
| `prompts` | System prompts `{clave: texto}` | Arranque (`loadPrompts`) |
| `pyodide` | Runtime Python + los DataFrames cargados | Arranque; persiste toda la sesión |
| `graphragAvailable` | Si el backend `/health` respondió OK | Arranque (`checkGraphragHealth`) |
| `loadedCsvs` | CSV ya cargados (`Set`) | Al cargar cada CSV, bajo demanda |
| `conversationId` | Hilo persistente de OpenAI | `ensureConversation` / `createConversation` |
| `lastResponseId` | Último `response.id` threaded | Cada llamada threaded |
| `sessionContext` | Contexto acotado `{slot: valor}` | Clarify, `rememberQueryParams` |
| `turnHistory` | Historial de turnos (máx. 60) | `recordTurnInHistory` |
| `sessionSummary` | Resumen comprimido de turnos antiguos | Al superar 18 turnos |
| `pendingClarify` | Estado del slot-filling en curso | Durante clarify |
| `lastUserQuery` / `lastTurn` | Última consulta / turno enriquecido | Tras cada consulta |
| `busy` | Bloqueo de envíos concurrentes | Inicio/fin de cada turno |

`sessionContext`, `turnHistory`, `sessionSummary` y `conversationId` se reflejan en `localStorage`
para sobrevivir a recargas dentro de la ventana de 3 h. **Nuevo chat** los borra y crea un hilo nuevo.

