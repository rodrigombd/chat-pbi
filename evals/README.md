# Evals y artefactos compartidos

## Flujo

1. Edita los `context_*.txt` y/o el array `TOOLS` en `index.html` (fuentes canónicas).
2. Regenera los artefactos derivados:

   ```bash
   python3 build_artifacts.py
   ```

   Produce `prompts.json` (bundle de los `.txt`) y `tools.json` (extracción del array `TOOLS`).
   Estos JSON son **derivados**: no se editan a mano.

3. Ejecuta las evaluaciones de regresión:

   ```bash
   export OPENAI_API_KEY="sk-..."
   python3 run_evals.py
   ```

   `run_evals.py` simula la función `orchestrate()` del front: construye las mismas
   instrucciones de orquestación (router + bloque de tool calling), llama al endpoint
   `/v1/responses` con `tools.json` y `tool_choice: "required"`, y verifica para cada
   pregunta del set fijo que (a) se invoca la herramienta esperada y (b) los slots /
   filtros clave aparecen en los argumentos.

## El set de regresión

`evals/regression_set.json` contiene casos con esta forma:

```json
{
  "id": "datos_conversion_curso",
  "query": "¿Cuál es la tasa de conversión del curso 2025/2026?",
  "memory": "(opcional) bloque de contexto de sesión inyectado",
  "expect": {
    "tool": "ejecutar_analisis_python",
    "n_calls": 1,
    "filtros_keywords": [["conversion", "conversión"], "2025/2026"]
  }
}
```

- `tool`: una de `ejecutar_analisis_python`, `solicitar_aclaracion`, `explicar_modelo_datos`.
- `n_calls` (solo python): número exacto de invocaciones esperadas. Protege la regla
  "una comparación de la misma métrica es UNA sola llamada".
- `filtros_keywords` (solo python): cada elemento debe aparecer en alguna de las
  instrucciones generadas (comparación insensible a tildes/mayúsculas). Una lista
  anidada significa "cualquiera de estas variantes vale".
- `slot` (solo clarify): identificador del parámetro ausente esperado.

El proceso devuelve código de salida `0` si pasan todos los casos y `1` si falla alguno,
apto para integrarlo en CI.

## Variables de entorno

- `OPENAI_API_KEY` (obligatoria).
- `EVAL_MODEL` (opcional, por defecto `gpt-4o`).
