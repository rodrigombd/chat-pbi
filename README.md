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


**¿Vienes a ponerlo en marcha?** Ve directo a la **[sección 1: guía de ejecución paso a paso](#1-guía-de-ejecución-paso-a-paso-de-cero-a-chatbot-funcionando)**,
que cubre el camino completo desde un clon limpio: entorno, instancia de Neo4j, carga de los nodos,
*embeddings*, migración de datos y arranque de los dos servidores.

---

## 1. Guía de ejecución paso a paso (de cero a chatbot funcionando)


> **Resumen del camino:** instalar dependencias → crear instancia Neo4j → cargar los nodos del grafo
> → calcular *embeddings* e índice vectorial → migrar los datos de residencia → arrancar backend →
> arrancar frontend.
>
> Los pasos **1.2 a 1.5** son de **primera instalación**. En el día a día solo repites **1.6 y 1.7**.

### 1.1. Requisitos previos

- **Python 3.12** (probado con 3.12/3.13).
- Una **API key de OpenAI**. Se usa en dos sitios: la introduces en la pantalla de conexión del
  frontend, y además el backend necesita la suya en `graphrag/.env`.
- Los CSV en `data/` (`Leads_Contacts.csv`, `economics.csv`, `sizing.csv`, `maestro_residencias.csv`).

### 1.2. Crear el entorno Python

Todos los comandos parten de la raíz del proyecto (`chat-pbi/`).

```powershell
cd graphrag

python -m venv venv
venv\Scripts\activate            # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
```

> El `requirements.txt` de la raíz y el de `graphrag/` son distintos. El que necesita el backend es
> **`graphrag/requirements.txt`**.

### 1.3. Crear la instancia de Neo4j

Tienes dos opciones.

#### Opción A — Neo4j Aura (cloud, gratis)

1. Entra en <https://console.neo4j.io> y crea una cuenta.
2. **Create instance → AuraDB Free**. Elige la región más cercana (Europa) y un nombre, p. ej.
   `resa-graphrag`.
3. Al crearla, Aura te muestra **una sola vez** las credenciales generadas (usuario `neo4j` y una
   contraseña aleatoria). **Descarga o copia el fichero de credenciales ahora**: la contraseña no se
   puede volver a consultar, solo resetear.
4. Espera a que el estado pase a **Running** (1-3 minutos).
5. Anota la **Connection URI**, con el formato `neo4j+s://xxxxxxxx.databases.neo4j.io`.

> La instancia gratuita de Aura se **pausa automáticamente tras varios días sin uso**. Si el backend
> falla al arrancar con un error de conexión, entra en la consola y pulsa **Resume**.

#### Opción B — Neo4j Desktop (local)

1. Instala **Neo4j Desktop** desde <https://neo4j.com/download/>.
2. **New → Create project** → **Add → Local DBMS**. Pon una contraseña.
3. Pulsa **Start** y espera al estado *Active*.
4. Tu URI será `bolt://localhost:7687` y el usuario `neo4j`.

#### Crear el `.env`

Crea el archivo **`graphrag/.env`** con las credenciales que acabas de obtener:

```dotenv
NEO4J_URI=neo4j+s://<tu-instancia>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<tu-password>
OPENAI_API_KEY=sk-<tu-clave>
```

### 1.4. Crear los nodos del grafo

El modelo de datos completo vive en **un único script**: `graphrag/graph/00_grafo_completo.cypher`.
Crea las tablas, columnas, valores y medidas, y todas sus relaciones (`TIENE_COLUMNA`,
`TIENE_MEDIDA`, `USA_COLUMNA`, `TIENE_VALOR`, `DERIVA_DE` y `RELACIONA`).


**1.4.1. Neo4j Browser / consola de Aura:**

1. Abre el **Query** de tu instancia.
2. Abre `graphrag/graph/00_grafo_completo.cypher` en VSCode, copia **todo** el contenido
   y pégalo en el editor de consultas de Neo4j.
3. Ejecútalo.


### 1.5. Calcular embeddings e índice vectorial

Con el grafo ya creado y el `.env` configurado, desde `graphrag/` y con el venv activado:

```powershell
python 01_populate_embeddings.py
python 02_create_vector_index.py
```

El primero recorre los nodos `Tabla`, `Medida`, `Columna` y `Valor`, compone el texto de cada uno
según `text_properties` de `config.py`, lo embebe con `text-embedding-3-small` y lo guarda en la
propiedad `embedding`. El segundo crea los índices vectoriales que usa la recuperación.


### 1.6. Migrar los datos de residencia (solo la primera vez)

Si tu `Leads_Contacts.csv` todavía contiene **nombres** de residencia (`As Burgas`) en vez de códigos
(`R002`), ningún *join* funcionará. Ejecuta la migración:

```powershell
cd ..\data
python convertir_residencias_a_codigo.py
```

El script informa por consola de cuántos valores no encontró en el maestro.

Antes de ejecutarlo, **cierra el CSV en Excel** y pausa la sincronización de OneDrive, o fallará con
`PermissionError`. El script deja una copia de seguridad en `Leads_Contacts.csv.bak`.


### 1.7. Arrancar el backend GraphRAG (terminal 1, puerto 8000)

```powershell
cd graphrag
venv\Scripts\activate
uvicorn api:app --port 8000 --reload
```

> **Arráncalo desde `graphrag/`, no desde la raíz.** `api.py` hace `import config` y
> `from src.db import get_driver`, y lee el `.env` de su propia carpeta. Desde otro directorio
> obtendrás `ModuleNotFoundError: config`.


### 1.8. Arrancar el frontend (terminal 2, puerto 8080)

```powershell
python -m http.server 8080 # Desde la raíz del proyecto
```

### 1.9. Abrir la aplicación

1. Ve a **`http://localhost:8080/frontend/index.html`**.
2. Introduce tu **API key de OpenAI** y pulsa **Conectar**. El arranque (`initChat`) carga en
   paralelo los `context_*.txt`, el hilo de OpenAI, el runtime de Pyodide con `pandas` y `numpy`, el
   CSV `Leads_Contacts.csv` y el *health check* del backend. La primera vez tarda: Pyodide descarga
   el runtime.


### 1.10. Tabla resumen

| # | Paso | Dónde | ¿Se repite? |
|---|------|-------|-------------|
| 1.2 | `venv` + `pip install -r requirements.txt` | `graphrag/` | Solo al instalar |
| 1.3 | Crear instancia Neo4j + `.env` | Aura / Desktop | Solo al instalar |
| 1.4 | Cargar `00_grafo_completo.cypher` | Neo4j Browser / `cypher-shell` | Al cambiar el modelo |
| 1.5 | `01_populate_embeddings.py` + `02_create_vector_index.py` | `graphrag/` | Al cambiar el grafo |
| 1.6 | `convertir_residencias_a_codigo.py` | `data/` | Solo al instalar |
| 1.7 | `uvicorn api:app --port 8000` | `graphrag/` | **Cada sesión** |
| 1.8 | `python -m http.server 8080` | `raíz` | **Cada sesión** |

Para depurar la recuperación sin levantar el frontend, `03_retrieval_graphrag.py` imprime el subgrafo
de una consulta de forma aislada; `04_answer_model.py` y `05_answer_data.py` ejecutan por CLI las dos
ramas de respuesta.

---

## 2. Qué cambia respecto a la rama anterior

### 2.1. De una tabla a cuatro

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

### 2.2. Tres medidas nuevas (familia `ECO`)

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

### 2.3. Normalización de residencias en `Leads_Contacts` (cambio de datos, no de código)

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

### 2.4. Grafo: un único script consolidado

El grafo se construye entero desde **`graphrag/graph/00_grafo_completo.cypher`**. Internamente
mantiene el orden que exige el modelo —limpieza, *constraints*, tabla de hechos, columnas, valores,
medidas, tablas nuevas y, al final, las relaciones `RELACIONA`— porque cada bloque hace `MATCH` sobre
nodos creados por los anteriores.

```
graphrag/graph/
└── 00_grafo_completo.cypher   # ← empieza con "MATCH (n) DETACH DELETE n": reconstruye todo
```

Que sea un solo archivo no elimina la fragilidad del orden, solo la encapsula: si reorganizas
bloques, o partes uno con un `;` intermedio, las variables se pierden y los `MATCH` dejan de casar
**en silencio**. Ver 1.4.

### 2.5. Nuevas relaciones en el grafo

- **`USA_COLUMNA`** — vincula cada medida con las columnas que consume. Existía en la configuración
  de expansión pero **ninguna relación real la usaba**; ahora sí. Se ha añadido también
  retroactivamente a las medidas `CR`.
- **`RELACIONA`** — vincula las columnas clave que hacen *join* entre tablas. Se crean 12
  relaciones en `04_grafo_maestro_residencias.cypher`, conectando `codigo_residencia` de las tres
  tablas nuevas con las tres columnas de residencia de `Leads_Contacts`.

`config.py` ya expande `RELACIONA` con `("RELACIONA", "both", 2)` sobre el label `Columna`, de modo
que el subgrafo recuperado incluye las tablas al otro lado del *join*.

### 2.6. Umbral de recuperación

El valor vigente en `config.py` es **`score_threshold = 0.65`**, con `top_k = 15` y un
`expansion_score_threshold = 0.45` más laxo para los nodos que entran por expansión del grafo.

El recorrido explica el número: se bajó de `0.70` a `0.55` porque las descripciones de columna eran
cortas y su similitud coseno caía por debajo de umbrales altos aunque fueran relevantes
(`Fecha creación` era el caso típico). Enriquecer el texto de los nodos en el propio grafo atacó la
causa real —la calidad del *embedding*, no el umbral— y permitió volver a subirlo a `0.65`, que
recorta el ruido de nodos de la tabla equivocada.

### 2.7. Carga de CSV en el frontend

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

### 2.8. `context_general.txt` actualizado

El prompt de generación de código ya **no** afirma que exista "un único DataFrame". Ahora documenta
las cuatro tablas, la clave de *join*, el parseo de `fecha` (`format="%m/%Y"`) y la traducción a
Pandas de las tres medidas `ECO`.

---

## 3. Limitación conocida: memoria y consultas elípticas

`retrieveSubgraph` embebe la **consulta cruda del usuario** (`userText`), no el texto enriquecido con
memoria. Es deliberado: el texto enriquecido convierte el *embedding* en un centroide de la sesión y
devuelve los mismos nodos turno tras turno.

El efecto secundario es que las **preguntas elípticas de seguimiento** recuperan un subgrafo pobre:

```
Usuario: ¿cuántos leads hay en Madrid?     → embedding rico, subgrafo correcto
Usuario: ¿y de Barcelona?                  → embedding de tres palabras, sin métrica
```

El paso *clarify* sí recibe la memoria completa, así que la desambiguación de *slots* funciona; lo
que se degrada es la **recuperación del subgrafo**. Con una sola tabla apenas se notaba; con cuatro,
el riesgo de recuperar nodos de la tabla equivocada aumenta.

**Pendiente:** reescritura de la consulta sobre `instruccion_enriquecida` para resolver la elipsis
antes de embeber, y re-recuperación tras el clarify con los *slots* ya resueltos.

---

## 4. Estructura del proyecto

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
    ├── requirements.txt     # ← el que instala el backend (distinto del de la raíz)
    ├── api.py               # FastAPI: /health y /retrieve
    ├── config.py            # esquema, labels y parámetros de recuperación
    ├── 01_populate_embeddings.py
    ├── 02_create_vector_index.py
    ├── 03_retrieval_graphrag.py    # inspección aislada del subgrafo (debug)
    ├── 04_answer_model.py          # CLI: rama de preguntas sobre el modelo
    ├── 05_answer_data.py           # CLI: rama de consultas de datos
    ├── graph/
    │   └── 00_grafo_completo.cypher    # grafo entero; empieza borrando
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

## 5. Requisitos previos

> Detalle operativo en **1.1**. Se resumen aquí para referencia.

- **Python 3.12** (recomendado; probado con 3.12/3.13).
- Una **API key de OpenAI** (la introduce el usuario en la pantalla de conexión del frontend; el
  backend usa la suya propia vía `.env`).
- Para el backend GraphRAG: una instancia de **Neo4j** con el grafo cargado (ver 1.3 y 1.4).
- Un navegador moderno. **No se puede abrir `index.html` con `file://`**: Pyodide y el `fetch` de
  los prompts requieren servirlo por HTTP.

---

## 6. Cómo ejecutar el chatbot

> Versión completa desde cero en la **sección 1**. Esto es la referencia corta del arranque diario.

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
# Esperado: {"ok": true, "neo4j": true, "top_k": 15, "score_threshold": 0.65}
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

## 7. Preparar Neo4j (referencia)

> Guía completa, incluida la creación de la instancia, en **1.3 – 1.5**. Aquí queda la referencia de
> los comandos y las verificaciones.

Desde `graphrag/`, con el `.env` ya configurado.

**Paso 1 — Construye el grafo.** Desde Neo4j Browser, la consola de Aura o `cypher-shell`:

```powershell
cypher-shell -a <NEO4J_URI> -u <USER> -p <PASSWORD> -f graph/00_grafo_completo.cypher
```

**Paso 2 — Verifica que las relaciones de *join* se crearon.** Este chequeo es importante: si alguna
columna referenciada no existe, el `MATCH` no casa, devuelve cero filas y **no se crea ninguna
relación, sin lanzar error**.

```cypher
MATCH ()-[r:RELACIONA]->() RETURN count(r);
// Esperado: 12
```

Si devuelve `0`, revisa que los nombres de columna del bloque de `RELACIONA` coincidan exactamente
con los de las columnas creadas más arriba en el mismo script.

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
mientras depuras, sin lanzar el pipeline completo del frontend. `04_answer_model.py` y
`05_answer_data.py` hacen lo propio con cada rama de respuesta desde la CLI.

---

## 8. Migrar los datos de residencia (referencia)

> Pasos operativos en **1.6**. Aquí queda el detalle del *mojibake*, que es lo que de verdad falla.

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

## 9. El flujo de un mensaje (orquestación por *tool calling*)

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

## 10. Memoria de la conversación

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

## 11. Parámetros de OpenAI por paso

Ya **no** usan todos `gpt-4o`. Cada agente tiene su modelo, centralizado en el objeto `MODELS` de
`index.html` (~línea 580), de modo que cambiarlos es un edit en un único sitio:

```javascript
var MODELS = {
  router:      "gpt-4.1-nano",
  modelQuery:  "gpt-4.1",
  clarify:     "gpt-4.1-mini",
  codeGen:     "gpt-4o",
  explicacion: "gpt-5.4-mini",
  conclusiones:"gpt-4o",
  memoria:     "gpt-4o-mini"
};
```

Los *embeddings* (frontend y backend) usan `text-embedding-3-small`.

| Paso | Modelo (`MODELS`) | System prompt | *Threaded* | Temp. | `max_output_tokens` |
|------|-------------------|---------------|------------|-------|---------------------|
| Router (tool calling) | `router` | `context_router.txt` | no (aislado) | 0.2 | 700 |
| Explicar modelo de datos | `modelQuery` | `context_modelo_datos.txt` | no (aislado) | 0.5 | 1500 |
| Clarify | `clarify` | `context_clarify.txt` | no (aislado) | 0.1 | 500 |
| Generación de código | `codeGen` | `context_general.txt` | **sí** | 0.5 | 1800 |
| Reintento de código | `codeGen` | `context_general.txt` | **sí** | 0.5 | 1800 |
| Explicación de código | `explicacion` | `context_explicacion.txt` | no (aislado) | 0.3 | 700 |
| Conclusión | `conclusiones` | `context_conclusiones.txt` | no (aislado) | 0.6 | 700 |
| Compresión de memoria | `memoria` | — | no (aislado) | — | — |

> `codeGen` se mantiene deliberadamente en `gpt-4o`: es el agente crítico en calidad, y es donde un
> modelo más barato se paga en código Pandas roto.
>
> **Valida los identificadores antes de tocar este mapa.** Un *string* de modelo inválido no lanza un
> error visible: la llamada falla y cae de vuelta en `gpt-4o`, con lo que el dashboard de la
> plataforma miente sobre lo que se está usando. Confírmalos con `GET /v1/models`.

---

## 12. Resolución de problemas frecuentes

### Específicos de esta rama

- **`NameError: economics is not defined`** — la tabla no se cargó porque el código generado no la
  mencionó por su nombre exacto, o el CSV no está en `data/`. `ensureTablesLoaded` carga bajo demanda
  buscando el nombre de la variable en el código.
- **El *join* con `maestro_residencias` no devuelve filas** — las columnas de residencia de
  `Leads_Contacts` siguen conteniendo nombres en vez de códigos. Ejecuta la migración (1.6).
- **El LLM filtra por `codigo_residencia == "As Burgas"`** — el modelo cree que el código *es* el
  nombre. Señal de que la migración no se ha aplicado, o de que el subgrafo recuperado no incluye
  `maestro_residencias`.
- **`MATCH ()-[r:RELACIONA]->() RETURN count(r)` devuelve 0** — algún `MATCH` del bloque `RELACIONA`
  de `00_grafo_completo.cypher` apunta a una columna inexistente, o un `;` intermedio ha roto el
  alcance de las variables. Revisa los nombres exactos (tildes, mayúsculas, espacios).
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

## 13. Mapa de variables globales del frontend

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

