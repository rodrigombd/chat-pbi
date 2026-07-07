# Asistente analítico CRM — RESA (demo)

Chatbot que permite a un empleado preguntar en lenguaje natural sobre los datos de captación
de las residencias de estudiantes RESA y recibir tablas, gráficos interactivos y conclusiones.

La demo es un sistema **híbrido de dos piezas**:

1. **Frontend** (`frontend/index.html`) — una única página que concentra toda la lógica de la
   aplicación. El "cerebro" de generación se reparte entre la **API Responses de OpenAI**
   (orquestación por *tool calling*, clarify, generación de código Pandas, explicaciones y
   conclusiones) y **Pyodide** (ejecución del código Pandas **en el navegador**, sin backend de
   datos). Los *system prompts* de cada paso son archivos `context_*.txt` externos cargados al
   arrancar.
2. **Backend GraphRAG** (`graphrag/`) — un servicio **FastAPI** que expone `/retrieve`. Recupera de
   **Neo4j Desktop**, mediante *embeddings* y expansión del grafo, el **subgrafo relevante** del modelo
   de datos (tablas, columnas y medidas) para cada consulta, y lo devuelve como texto listo para
   inyectar como contexto. Así el generador de código conoce el esquema real sin llevarlo
   *hardcodeado*.

> El backend GraphRAG es **opcional para arrancar**: si no está disponible, el asistente sigue
> funcionando con el contexto estático de los `context_*.txt`, pero sin recuperación dinámica del
> modelo (se muestra un aviso). Para un buen funcionamiento del chatbot debe levantarse.

---

## 0. Estructura del proyecto

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
│   └── Leads_Contacts.csv   # Dataset que carga Pyodide en el navegador
│
├── evals/                   # Set de regresión y runner de evaluaciones
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
    ├── grafo_resa.cypher    # script para construir el grafo en Neo4j
    ├── requirements.txt
    ├── 01_populate_embeddings.py
    ├── 02_create_vector_index.py
    ├── 03_retrieval_graphrag.py
    ├── 04_answer.py
    └── src/
        ├── db.py            # driver de Neo4j
        ├── embeddings.py
        └── graph_parser.py
```

> **Dos rutas relativas importan y dependen de dónde arrancas cada servidor:**
>
> - `index.html` carga el CSV desde `../data/Leads_Contacts.csv` y los `context_*.txt` desde su
>   **propia carpeta**. Por eso el servidor del frontend debe arrancarse **desde `frontend/`**.
> - `api.py` importa `import config` y `from src.db import get_driver`, y lee `.env` de su carpeta.
>   Por eso el backend debe arrancarse **desde `graphrag/`**.

---

## 1. Requisitos previos

- **Python 3.12** (recomendado; el proyecto se ha probado con 3.12/3.13).
- Una **API key de OpenAI** (la introduce el usuario en la pantalla de conexión del frontend; el
  backend usa la suya propia vía `.env`).
- Para el backend GraphRAG: una instancia de **Neo4j** con el grafo del modelo de datos
  cargado (ver sección 3).
- Un navegador moderno (Chrome/Edge/Firefox). **No se puede abrir `index.html` con `file://`**:
  Pyodide y el `fetch` de los prompts requieren servirlo por HTTP.

---

## 2. Cómo ejecutar el chatbot (paso a paso)

Necesitas **dos terminales**: una para el **backend GraphRAG** (puerto 8000) y otra para el
**frontend** (puerto 8080). Todos los comandos asumen que estás en la raíz del proyecto
(`chat-pbi/`) al empezar.

### Terminal 1 — Backend GraphRAG (FastAPI, puerto 8000)

```powershell
# 1) Entra en la carpeta del backend (los imports y el .env se resuelven desde aquí)
cd graphrag

# 2) (Recomendado) crea y activa un entorno virtual
python -m venv venv
venv\Scripts\activate            # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

# 3) Instala las dependencias del backend
pip install -r requirements.txt

# 4) Crea el archivo .env con tus credenciales (ver plantilla más abajo)
#    graphrag/.env debe contener NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD y OPENAI_API_KEY

# 5) Arranca la API (recarga automática en desarrollo)
uvicorn api:app --port 8000 --reload
```

Comprueba que responde antes de seguir:

```powershell
# En otra terminal, o en el navegador:
curl http://localhost:8000/health
# Esperado: {"ok": true, "neo4j": true, "top_k": 15, "score_threshold": 0.7}
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
# 1) Desde la raíz del proyecto, entra en la carpeta del frontend
cd frontend

# 2) Levanta un servidor estático (cualquiera vale; usamos el de Python)
python -m http.server 8080
```

### Abrir la aplicación

1. Ve a **`http://localhost:8080/index.html`** en el navegador.
2. Introduce tu **API key de OpenAI** y pulsa **Conectar**. Durante el arranque (`initChat`) se
   cargan en paralelo: los `context_*.txt`, el hilo de OpenAI, el runtime de Pyodide con `pandas`
   y `numpy`, el CSV `Leads_Contacts.csv` y el chequeo de salud del backend GraphRAG.
3. Empieza a preguntar (p. ej. *"Compara los leads de Madrid y Barcelona este curso"*).

> **Si el backend GraphRAG no está levantado**, verás un aviso al conectar, pero podrás usar el
> chat igualmente con el contexto estático de los `context_*.txt`.
>
> **Puertos:** el frontend espera el backend en `http://localhost:8000` (constante
> `GRAPHRAG_BASE_URL` en `index.html`). Si cambias el puerto del backend, actualiza esa constante.

---

## 3. Preparar Neo4j (solo la primera vez)

El backend GraphRAG necesita el grafo del modelo de datos con *embeddings* e índices vectoriales.
Desde `graphrag/`, con el `.env` ya configurado:

```powershell
cd graphrag

# 1) Construye el grafo en Neo4j (nodos Tabla/Medida/Columna y relaciones)
#    Ejecuta grafo_resa.cypher en Neo4j (desde el navegador de Aura,
#    Neo4j Browser o cypher-shell). Ejemplo con cypher-shell:
#    cypher-shell -a <NEO4J_URI> -u <USER> -p <PASSWORD> -f grafo_resa.cypher

# 2) Calcula y guarda los embeddings de cada nodo (usa OpenAI text-embedding-3-small)
python 01_populate_embeddings.py

# 3) Crea los índices vectoriales por label
python 02_create_vector_index.py
```

`03_retrieval_graphrag.py` es útil para **inspeccionar el subgrafo recuperado** de forma aislada
mientras depuras, sin lanzar el pipeline completo del frontend.

---

## 4. El flujo de un mensaje (orquestación por *tool calling*)

Cuando el usuario envía un mensaje, `sendMessage → orchestrate` monta la memoria de sesión y llama
al **router** con *tool calling* (`context_router.txt`). El router **no** devuelve texto libre: está
obligado a invocar una de **dos** herramientas.

| Herramienta | Cuándo | Qué hace |
|-------------|--------|----------|
| `explicar_modelo_datos` | Preguntas teóricas sobre tablas/columnas/KPIs y saludos | `answerModelQuery` responde en texto usando `context_modelo_datos.txt` (aislado, no toca el hilo) |
| `ejecutar_analisis_python` | Cualquier cálculo, agregación, ranking, comparación, serie temporal o gráfico | Entra en el pipeline de datos (pasos siguientes). Se puede invocar **varias veces en paralelo** para peticiones independientes |

Si el router no invoca ninguna herramienta, hay **un reintento** con un mensaje reforzado antes de
caer, por seguridad, en `answerDataQuery` (la rama con más redes de protección: clarify + reintento).

### Rama de datos (`answerDataQuery`)

1. **Recuperación GraphRAG** — `retrieveSubgraph` llama a `POST /retrieve` del backend con la
   consulta enriquecida y obtiene el subgrafo del modelo de datos. Se inyecta como contexto del
   generador de código (`wrapSubgraphContext`).
2. **Clarify** (`runClarifyAgent`, `context_clarify.txt`) — un segundo agente decide, **usando ese
   mismo subgrafo**, si faltan datos imprescindibles (p. ej. el curso). Si faltan, pregunta al
   usuario slot a slot con botones (máximo 2 slots) y reanuda al terminar reutilizando el subgrafo.
   En modo **batch** (varias peticiones en paralelo) el clarify se salta (`skipClarify: true`),
   porque es interactivo y bloqueante.
3. **Generación de código** (`context_general.txt`, **única llamada *threaded***) — el modelo
   responde **solo** con un bloque ```python``` que asigna el resultado a la variable `resultado`
   (escalar, DataFrame, Series, dict de KPIs o dict Plotly con `"__plotly__": True`).
4. **Ejecución en Pyodide** (`runPython`) — se resetea `resultado`, se ejecuta el código a scope
   global y se serializa a JSON etiquetado con un `kind` (`number`, `text`, `dataframe`, `dict`,
   `plotly`, `none`, `error`). Si falla, `retryWithModelFix` reenvía el código y el traceback al
   modelo para una corrección y reejecuta una vez.
5. **Render** (`renderResult`) — número → tarjeta KPI; texto → Markdown; dataframe/dict → tabla;
   plotly → figura interactiva (los mapas pasan por `beautifyMap`).
6. **Explicación** (opcional, `context_explicacion.txt`) y **conclusión** (opcional, solo si el
   interruptor está activo, `context_conclusiones.txt`). Antes de enviar datos al modelo para la
   conclusión se **pseudonimizan** las categorías de texto (los números se mantienen reales) y al
   volver se revierten los alias.

---

## 5. Memoria de la conversación

La memoria del lado del cliente enriquece los prompts y sobrevive a recargas dentro de una ventana
de **3 horas** (`SESSION_MAX_AGE_MS`), persistida en `localStorage`.

- **`sessionContext`** `{slot: valor}` — contexto acotado (curso, ciudad, métrica…), rellenado por
  el paso clarify y por `rememberQueryParams`.
- **`turnHistory`** — historial de turnos resueltos `{q, r, ts}` (máx. `MAX_HISTORY_TURNS = 60`; se
  inyectan los últimos `HISTORY_INJECT_TURNS = 16`).
- **`sessionSummary`** — cuando `turnHistory` supera `SUMMARY_TRIGGER_TURNS = 18`, los turnos más
  antiguos se **comprimen** en un resumen (ventana deslizante), manteniendo recientes los últimos
  `SUMMARY_KEEP_RECENT = 16`.

`buildFullMemoryText` combina resumen + historial reciente + contexto y lo inyecta en el *input* del
router y del generador de código.

> **Regla de threading:** solo las **consultas de datos** (generación + su reintento) entran en el
> hilo persistente de OpenAI (`store: true`). Router, clarify, explicación de modelo, explicación
> de código y conclusión corren **aislados** (`isolated: true`), para no contaminar el hilo con JSON
> de fontanería ni con salidas auxiliares.

---

## 6. Parámetros de OpenAI por paso

Todos los pasos usan **`gpt-4o`**. La compresión del resumen de sesión usa `gpt-4o-mini`.

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

## 7. Resolución de problemas frecuentes

- **`NameError: leads_contacts is not defined`** — el CSV no se cargó. Arranca el frontend
  **desde `frontend/`** con `python -m http.server 8080` (no con `file://`) y confirma que existe
  `data/Leads_Contacts.csv`.
- **"Backend GraphRAG no disponible"** — `http://localhost:8000/health` no responde. Revisa que
  `uvicorn` esté arrancado **desde `graphrag/`** y que el `.env` (Neo4j/OpenAI) sea correcto.
- **`Falta la variable de entorno 'NEO4J_URI'`** (u otra) al arrancar el backend — falta o está mal
  el `graphrag/.env`. Complétalo con las cuatro claves de la plantilla.
- **`ModuleNotFoundError: config` / `src`** al arrancar el backend — estás lanzando `uvicorn` desde
  la carpeta equivocada. Debe ejecutarse **desde `graphrag/`**.
- **Faltan archivos de contexto** — algún `context_*.txt` no está junto a `index.html` dentro de
  `frontend/`.

---

## 8. Mapa de variables globales del frontend

| Global | Qué guarda | Cuándo cambia |
|--------|------------|---------------|
| `apiKey` | Clave de OpenAI del usuario | Al conectar |
| `prompts` | System prompts `{clave: texto}` | Arranque (`loadPrompts`) |
| `pyodide` | Runtime Python + `leads_contacts` | Arranque; persiste toda la sesión |
| `graphragAvailable` | Si el backend `/health` respondió OK | Arranque (`checkGraphragHealth`) |
| `loadedCsvs` | CSV ya cargados | Al cargar cada CSV |
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
