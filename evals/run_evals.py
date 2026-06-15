import json
import os
import re
import sys
import unicodedata
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = ROOT / "prompts.json"
TOOLS_PATH = ROOT / "tools.json"
EVALSET_PATH = ROOT / "evals" / "regression_set.json"

OPENAI_URL = "https://api.openai.com/v1/responses"
MODEL = os.environ.get("EVAL_MODEL", "gpt-4o")

ORCH_SUFFIX = (
    "\n\nINSTRUCCIONES DE ORQUESTACIÓN (Tool Calling):"
    "\n- Debes responder SIEMPRE invocando una o más herramientas, nunca con texto libre."
    "\n- Preguntas teóricas sobre tablas, columnas o KPIs, y saludos → explicar_modelo_datos."
    "\n- Consulta de datos con parámetros críticos ausentes que el contexto no resuelve → solicitar_aclaracion (una pregunta a la vez)."
    "\n- Consulta de datos clara y programable → ejecutar_analisis_python."
    "\n- Si el usuario pide varias cosas independientes (distintas métricas o salidas), invoca ejecutar_analisis_python varias veces en paralelo, una por petición. Una comparación de la misma métrica entre categorías es UNA sola llamada."
    "\n- Prioriza usar el contexto ya acotado de la sesión antes de pedir aclaraciones."
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def orchestrator_instructions(prompts):
    base = prompts.get("router") or (
        "Eres el orquestador de un asistente analítico sobre datos de CRM de "
        "residencias de estudiantes. Decides qué herramienta invocar según el "
        "mensaje del usuario y el contexto de la sesión."
    )
    return base + ORCH_SUFFIX


def build_user_content(memory, user_text):
    content = ""
    if memory:
        content += memory + "\n\n"
    content += "MENSAJE DEL USUARIO:\n" + user_text
    return content


def call_orchestrator(api_key, instructions, user_content, tools):
    body = {
        "model": MODEL,
        "instructions": instructions,
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": user_content}]}
        ],
        "max_output_tokens": 700,
        "temperature": 0.2,
        "store": False,
        "truncation": "auto",
        "tools": tools,
        "tool_choice": "required",
        "parallel_tool_calls": True,
    }
    req = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return extract_tool_calls(data)


def extract_tool_calls(data):
    calls = []
    for item in data.get("output", []) or []:
        if item.get("type") == "function_call":
            args = {}
            try:
                args = json.loads(item.get("arguments") or "{}")
            except Exception:
                args = {}
            calls.append({"name": item.get("name"), "args": args})
    return calls


def normalize(text):
    s = str(text or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def text_of_python_call(call):
    return normalize(call.get("args", {}).get("instruccion_enriquecida", ""))


def check_expectation(calls, expect):
    expected_tool = expect["tool"]
    names = [c["name"] for c in calls]

    if expected_tool == "ejecutar_analisis_python":
        py_calls = [c for c in calls if c["name"] == "ejecutar_analisis_python"]
        if not py_calls:
            return False, f"no se invocó ejecutar_analisis_python (se invocó: {names})"

        expected_n = expect.get("n_calls")
        if expected_n is not None and len(py_calls) != expected_n:
            return False, f"se esperaban {expected_n} llamadas, hubo {len(py_calls)}"

        joined = " || ".join(text_of_python_call(c) for c in py_calls)
        missing = []
        for kw in expect.get("filtros_keywords", []):
            variants = kw if isinstance(kw, list) else [kw]
            if not any(normalize(v) in joined for v in variants):
                missing.append(variants[0])
        if missing:
            return False, f"faltan filtros/keywords en la instrucción: {missing}"
        return True, "ok"

    if expected_tool == "solicitar_aclaracion":
        clarify = [c for c in calls if c["name"] == "solicitar_aclaracion"]
        if not clarify:
            return False, f"no se invocó solicitar_aclaracion (se invocó: {names})"
        expected_slot = expect.get("slot")
        if expected_slot:
            got_slot = normalize(clarify[0].get("args", {}).get("slot", ""))
            if normalize(expected_slot) not in got_slot and got_slot not in normalize(expected_slot):
                return False, f"slot esperado '{expected_slot}', se obtuvo '{got_slot}'"
        return True, "ok"

    if expected_tool == "explicar_modelo_datos":
        if "explicar_modelo_datos" not in names:
            return False, f"no se invocó explicar_modelo_datos (se invocó: {names})"
        return True, "ok"

    return False, f"herramienta esperada desconocida: {expected_tool}"


def run():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: define OPENAI_API_KEY en el entorno.", file=sys.stderr)
        return 2

    for p in (PROMPTS_PATH, TOOLS_PATH, EVALSET_PATH):
        if not p.exists():
            print(f"ERROR: falta {p}. Ejecuta build_artifacts.py primero si es prompts/tools.", file=sys.stderr)
            return 2

    prompts = load_json(PROMPTS_PATH)
    tools = load_json(TOOLS_PATH)
    evalset = load_json(EVALSET_PATH)
    instructions = orchestrator_instructions(prompts)

    passed = 0
    failed = 0
    failures = []

    for case in evalset:
        memory = case.get("memory", "")
        user_text = case["query"]
        user_content = build_user_content(memory, user_text)
        try:
            calls = call_orchestrator(api_key, instructions, user_content, tools)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:200]
            ok, reason = False, f"HTTP {e.code}: {detail}"
        except Exception as e:
            ok, reason = False, f"excepción: {e}"
        else:
            ok, reason = check_expectation(calls, case["expect"])

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['id']}: {case['query']}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append((case["id"], reason))
            print(f"        → {reason}")

    total = passed + failed
    print("\n" + "=" * 60)
    print(f"Resultado: {passed}/{total} OK")
    if failures:
        print("Fallos:")
        for cid, reason in failures:
            print(f"  - {cid}: {reason}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
