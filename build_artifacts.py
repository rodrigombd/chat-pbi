import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
PROMPTS_OUT = ROOT / "prompts.json"
TOOLS_OUT = ROOT / "tools.json"

PROMPT_FILES = {
    "router": "context_router.txt",
    "clarify": "context_clarify.txt",
    "modelo_datos": "context_modelo_datos.txt",
    "general": "context_general.txt",
    "conclusiones": "context_conclusiones.txt",
    "explicacion": "context_explicacion.txt",
    "planificador": "context_planificador.txt",
}


def extract_orchestrator_suffix():
    """Lee la constante JS ORCHESTRATOR_SUFFIX de index.html (concatenación de
    literales con +) y la reconstruye como string, para que run_evals.py use
    EXACTAMENTE la misma instrucción que el front sin duplicarla."""
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(r"var\s+ORCHESTRATOR_SUFFIX\s*=\s*(.*?);", html, re.DOTALL)
    if not m:
        return None
    expr = m.group(1)
    # Captura cada literal entre comillas dobles, respetando escapes.
    pieces = re.findall(r'"((?:\\.|[^"\\])*)"', expr)
    if not pieces:
        return None
    decoded = []
    for p in pieces:
        decoded.append(
            p.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        )
    return "".join(decoded)


def build_prompts():
    out = {}
    missing = []
    for key, fname in PROMPT_FILES.items():
        path = ROOT / fname
        if not path.exists():
            missing.append(fname)
            continue
        out[key] = path.read_text(encoding="utf-8")
    suffix = extract_orchestrator_suffix()
    if suffix:
        out["__orchestrator_suffix__"] = suffix
    PROMPTS_OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out, missing


def extract_tools():
    html = INDEX.read_text(encoding="utf-8")
    start = html.find("var TOOLS = [")
    if start < 0:
        raise RuntimeError("No se encontró 'var TOOLS = [' en index.html")
    bracket = html.find("[", start)
    depth = 0
    end = None
    in_str = False
    quote = ""
    i = bracket
    while i < len(html):
        ch = html[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                in_str = False
        else:
            if ch in ('"', "'"):
                in_str = True
                quote = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        i += 1
    if end is None:
        raise RuntimeError("No se pudo delimitar el array TOOLS en index.html")
    literal = html[bracket:end + 1]
    return literal


def js_array_to_json(literal):
    txt = literal
    txt = re.sub(r"//[^\n]*", "", txt)
    txt = re.sub(r",(\s*[\]}])", r"\1", txt)
    txt = re.sub(
        r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)',
        lambda m: f'{m.group(1)}"{m.group(2)}"{m.group(3)}',
        txt,
    )
    txt = txt.replace("'", '"')
    return json.loads(txt)


def build_tools():
    literal = extract_tools()
    tools = js_array_to_json(literal)
    TOOLS_OUT.write_text(
        json.dumps(tools, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tools


def main():
    prompts, missing = build_prompts()
    print(f"prompts.json: {len(prompts)} prompts escritos en {PROMPTS_OUT.name}")
    if missing:
        print(f"  AVISO: faltan archivos de contexto: {', '.join(missing)}")
    tools = build_tools()
    names = [t.get("name") for t in tools]
    print(f"tools.json: {len(tools)} herramientas extraídas: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
