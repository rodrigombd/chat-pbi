# PoC GraphRAG semántico sobre Neo4j Aura

Prueba de concepto de *retrieval* GraphRAG para el chatbot analítico: en lugar
de buscar palabras clave (enfoque léxico actual en JS), se vectorizan las
propiedades de los nodos del grafo, se buscan los **puntos de entrada** por
similitud semántica y se **expande el subgrafo** arrastrando dependencias, que
luego se serializa para inyectar en el prompt del LLM.

> **Genérico por diseño:** todo lo específico de un modelo de datos (etiquetas,
> relaciones, propiedades) vive en `config.py`. Para usar otro grafo, solo se
> edita ese fichero — el resto del código no se toca.

---

## Estructura

```
poc_graphrag/
│   .env.example              ← plantilla de credenciales
│   .gitignore
│   requirements.txt
│   config.py                 ← ESQUEMA + credenciales (única zona a tocar)
│   01_populate_embeddings.py ← genera y guarda embeddings en los nodos
│   02_create_vector_index.py ← crea los índices vectoriales
│   03_retrieval_graphrag.py  ← búsqueda + expansión + serialización
│   demo.ipynb                ← notebook narrado para la demo
└───src/
        db.py                 ← conexión Neo4j
        embeddings.py         ← cliente OpenAI
        graph_parser.py       ← genera la query Cypher y serializa el subgrafo
```

---

## Requisitos previos

- El grafo ya cargado en Neo4j Aura (tu `grafo_resa.cypher` ya ejecutado).
- Python 3.10 o superior.
- Una API key de OpenAI con saldo.

---

## Pasos (Windows PowerShell)

### 1. Situarte en la carpeta y crear un entorno virtual

```powershell
cd .\poc_graphrag\
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> Si PowerShell bloquea la activación con un error de *execution policy*, ejecuta
> una vez:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Crear el fichero `.env` con tus credenciales

```powershell
Copy-Item .env.example .env
notepad .env
```

Rellena los 4 valores. La `NEO4J_URI` y el password los copias del panel de
Aura (botón **Connect → Drivers**). Guarda y cierra.

### 4. Generar los embeddings

```powershell
python 01_populate_embeddings.py
```

Recorre los nodos `(:Medida)` y `(:Tabla)`, genera su embedding con OpenAI y lo
guarda. Es **idempotente**: si lo vuelves a lanzar, solo procesa los que falten.

### 5. Crear los índices vectoriales

```powershell
python 02_create_vector_index.py
```

### 6. Probar el retrieval

```powershell
python 03_retrieval_graphrag.py "¿Cuántos leads hubo en 2025 comparado con 2024?"
```

Para buscar sobre tablas en vez de medidas:

```powershell
python 03_retrieval_graphrag.py "¿Qué tablas hay sobre ciudades?" --label Tabla
```

Verás impreso el subgrafo serializado: ese texto es exactamente lo que
inyectarías en el prompt del LLM.

---

## Adaptar a otro modelo de datos

Edita **solo** `config.py`, sección `SCHEMA`. Por cada etiqueta que quieras
indexar, añade un `LabelConfig` con:

- `label`: la etiqueta en Neo4j.
- `name_property`: la propiedad legible (lo que se muestra como nombre).
- `text_properties`: propiedades que se concatenan para el embedding.
- `expansion_relationships`: lista de `(TIPO_RELACION, direccion, saltos)`.
  Usa `1` salto para relaciones directas y `>1` solo para cadenas recursivas.

Vuelve a ejecutar los pasos 4–6. No hay que tocar ningún `.py` más.

---

## Notas para producción (back-end de agosto)

- Los scripts son idempotentes (`IF NOT EXISTS`, `WHERE embedding IS NULL`):
  seguros de re-ejecutar.
- La función `retrieve_context()` de `03_retrieval_graphrag.py` es el único
  punto de integración: el back-end la llama con la pregunta y obtiene el texto
  de contexto para el prompt. Sustituir `sys.argv` por el parámetro del endpoint.
- **Antes de que caduque la prueba de Aura**, exporta un *dump* desde el panel
  (Aura → Export) para conservar el grafo + embeddings.
