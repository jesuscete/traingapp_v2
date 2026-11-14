"""Batería QA de extremo a extremo (M10): modo reglas frente a modo IA, con juez a ciegas.

Usa la app REAL por HTTP contra una base de datos de pruebas. Entorno esperado (ver README):
    gateway reglas  :8001  (APP_DATABASE_URL=…/traingapp_qa, APP_REDIS_URL=…/1)
    gateway IA      :8002  (igual + APP_CHAT_RULE_NODES=guided, APP_PLAN_ENGINE=llm)
    ai-parser Claude:8101  (con medidor de uso -> --meter-log)
    ai-parser stub  :8102  (APP_LLM_PROVIDER=stub: referencia determinista)

Ejecutar con el venv del api-gateway desde la raíz del repo:
    services/api-gateway/.venv/Scripts/python scripts/qa/battery.py --out <dir>
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
GATEWAY_DIR = ROOT / "services" / "api-gateway"
sys.path.insert(0, str(GATEWAY_DIR))

PASSWORD = "QaTraingapp#2026"
LEG_GROUPS = ("quadriceps", "hamstrings", "glutes")


# --- Personas -----------------------------------------------------------------------------


@dataclass
class Persona:
    key: str
    name: str
    profile: dict[str, Any]
    history: list[dict[str, Any]]
    plan_answers: list[str]
    goal_question: str
    missing_question: str | None
    open_question: str
    full: bool = True  # False = solo objetivo y plan (mapas nuevos)
    token: str = ""
    allowed: set[str] | None = None


def _days_ago(n: int, hour: int = 18) -> str:
    return (datetime.now(UTC) - timedelta(days=n)).replace(hour=hour, minute=0).isoformat()


def _gym(day: int, exercises: list[tuple[str, int, int, float | None]], minutes: int = 60) -> dict[str, Any]:
    return {
        "discipline": "gym",
        "rawText": "sesión de gimnasio",
        "performedAt": _days_ago(day),
        "durationMinutes": minutes,
        "intensity": 7,
        "exercises": [{"name": n, "sets": s, "reps": r, "weightKg": w} for n, s, r, w in exercises],
    }


def _sport(discipline: str, day: int, minutes: int, distance: float | None = None) -> dict[str, Any]:
    return {
        "discipline": discipline,
        "rawText": f"{discipline} {minutes} min",
        "performedAt": _days_ago(day),
        "durationMinutes": minutes,
        "distanceMeters": distance,
        "intensity": 7,
    }


BASE_PROFILE = {"heightCm": 178, "birthDate": "1994-05-10", "sex": "male", "goal": "performance"}

PERSONAS = [
    Persona(
        key="runner",
        name="QA Runner",
        profile={**BASE_PROFILE, "weightKg": 68, "sports": ["running"], "primarySport": "running",
                 "fitnessLevel": "intermediate",
                 "equipment": {"preset": "casa", "extra": [], "missing": []}},
        history=[
            _sport("running", 1, 50, 10000), _sport("running", 3, 40, 8000),
            _sport("running", 6, 75, 16000), _sport("running", 8, 45, 9000),
            _gym(4, [("Sentadilla goblet", 3, 10, 20), ("Zancadas", 3, 10, None), ("Plancha", 3, 1, None)], 40),
        ],
        plan_answers=["quiero crear una rutina", "corro", "martes, jueves y domingo", "1 hora",
                      "para mejorar en correr", "2", "me da igual"],
        goal_question="Quiero mejorar mi marca en 10k",
        missing_question="No tengo kettlebell, ¿qué hago en lugar del peso muerto a una pierna con kettlebell?",
        open_question="¿Me conviene hacer pesas el mismo día que hago series en pista?",
    ),
    Persona(
        key="boxer",
        name="QA Boxer",
        profile={**BASE_PROFILE, "weightKg": 75, "sports": ["boxeo"], "primarySport": "boxeo",
                 "fitnessLevel": "intermediate",
                 "equipment": {"preset": "gimnasio", "extra": [], "missing": ["medicine ball"]}},
        history=[
            _sport("boxing", 1, 60), _sport("boxing", 3, 60), _sport("boxing", 6, 75),
            _gym(2, [("Press banca", 4, 6, 70), ("Dominadas", 4, 6, None), ("Sentadilla", 4, 5, 90)]),
            _gym(5, [("Peso muerto rumano", 3, 8, 80), ("Remo con barra", 4, 8, 60), ("Press militar", 3, 8, 40)]),
        ],
        plan_answers=["quiero crear una rutina", "boxeo", "lunes, miércoles y viernes", "1 hora",
                      "para mejorar en boxeo", "3", "me da igual"],
        goal_question="Quiero mejorar mi pegada",
        missing_question="No tengo balón medicinal",
        open_question="Tengo sparring el sábado, ¿qué hago en el gimnasio el jueves y el viernes?",
    ),
    Persona(
        key="gym",
        name="QA Gym",
        profile={**BASE_PROFILE, "weightKg": 80, "goal": "maintenance", "sports": [],
                 "fitnessLevel": "beginner",
                 "equipment": {"preset": "gimnasio", "extra": [], "missing": []}},
        history=[
            _gym(1, [("Press banca", 3, 10, 50), ("Curl bíceps", 3, 12, 12), ("Elevaciones laterales", 3, 12, 8)]),
            _gym(3, [("Sentadilla", 3, 10, 60), ("Prensa", 3, 12, 120), ("Curl femoral", 3, 12, 30)]),
            _gym(5, [("Jalón al pecho", 3, 10, 50), ("Remo sentado", 3, 10, 45), ("Curl martillo", 3, 12, 12)]),
        ],
        plan_answers=["quiero crear una rutina", "no", "general", "4", "me da igual"],
        goal_question="Quiero ganar músculo, sobre todo brazos y hombros",
        missing_question="No tengo polea, ¿qué hago en vez del jalón al pecho?",
        open_question="Soy principiante, ¿cuántas series por músculo a la semana debería hacer?",
    ),
    Persona(
        key="football",
        name="QA Futbolista",
        profile={**BASE_PROFILE, "weightKg": 72, "sports": ["futbol"], "primarySport": "futbol",
                 "fitnessLevel": "intermediate",
                 "equipment": {"preset": "gimnasio", "extra": [], "missing": []}},
        history=[_sport("football", 2, 90), _sport("football", 4, 90), _sport("football", 7, 90)],
        plan_answers=["quiero crear una rutina", "futbol", "martes, jueves y sábado", "90 minutos",
                      "para mejorar en futbol", "2", "me da igual"],
        goal_question="Quiero ser más rápido en el sprint",
        missing_question=None,
        open_question="",
        full=False,
    ),
    Persona(
        key="hyrox",
        name="QA Hyrox",
        profile={**BASE_PROFILE, "weightKg": 78, "sports": ["hyrox"], "primarySport": "hyrox",
                 "fitnessLevel": "intermediate",
                 "equipment": {"preset": "gimnasio", "extra": [], "missing": []}},
        history=[_sport("hyrox", 2, 70), _sport("running", 4, 45, 9000), _sport("hyrox", 7, 60)],
        plan_answers=["quiero crear una rutina", "hyrox", "sábado", "1 hora",
                      "para mejorar en hyrox", "3", "me da igual"],
        goal_question="Quiero mejorar en hyrox",
        missing_question=None,
        open_question="",
        full=False,
    ),
]


# --- Infraestructura -----------------------------------------------------------------------


@dataclass
class Env:
    rules: str
    llm: str
    parser_llm: str
    parser_stub: str
    meter: Path
    internal_token: str
    judge_model: str
    client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=400))


def _internal_token() -> str:
    for line in (GATEWAY_DIR / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("APP_INTERNAL_TOKEN="):
            return line.split("=", 1)[1].strip()
    return "internal-dev-token"


def meter_mark(env: Env) -> int:
    return len(env.meter.read_text(encoding="utf-8").splitlines()) if env.meter.exists() else 0


def meter_since(env: Env, mark: int) -> dict[str, Any]:
    if not env.meter.exists():
        return {"ai_calls": 0, "tokens_in": 0, "tokens_out": 0, "ai_seconds": 0.0}
    calls = [json.loads(x) for x in env.meter.read_text(encoding="utf-8").splitlines()[mark:]]
    return {
        "ai_calls": len(calls),
        "tokens_in": sum(
            (c.get("input_tokens") or 0)
            + (c.get("cache_creation_input_tokens") or 0)
            + (c.get("cache_read_input_tokens") or 0)
            for c in calls
        ),
        "tokens_out": sum(c.get("output_tokens") or 0 for c in calls),
        "ai_seconds": round(sum(c.get("seconds") or 0 for c in calls), 1),
        "paths": [c.get("path") for c in calls],
    }


def auth(p: Persona) -> dict[str, str]:
    return {"Authorization": f"Bearer {p.token}"}


def timed(env: Env, fn: Any) -> tuple[Any, dict[str, Any]]:
    mark = meter_mark(env)
    start = time.perf_counter()
    result = fn()
    usage = meter_since(env, mark)
    usage["wall_seconds"] = round(time.perf_counter() - start, 2)
    return result, usage


# --- Preparación ---------------------------------------------------------------------------


def setup_persona(env: Env, p: Persona, suffix: str) -> None:
    email = f"qa-{p.key}-{suffix}@qa.traingapp.dev"
    r = env.client.post(f"{env.rules}/auth/register", json={"email": email, "password": PASSWORD, "name": p.name})
    r.raise_for_status()
    p.token = r.json()["access_token"]
    env.client.put(f"{env.rules}/profile", json=p.profile, headers=auth(p)).raise_for_status()
    for session in p.history:
        env.client.post(f"{env.rules}/sessions", json=session, headers=auth(p)).raise_for_status()
    eq = p.profile.get("equipment") or {}
    if eq.get("preset") == "casa":
        p.allowed = {"dumbbell", "kettlebells", "bands", "exercise ball", "foam roll", "body only"}
    else:
        p.allowed = None
    missing = set(eq.get("missing") or [])
    if missing:
        p.allowed = (p.allowed or set(ALL_EQUIPMENT)) - missing


ALL_EQUIPMENT = ("barbell", "e-z curl bar", "dumbbell", "kettlebells", "cable", "machine", "bands",
                 "medicine ball", "exercise ball", "foam roll", "body only", "other")


def catalog_index(env: Env, p: Persona) -> dict[str, list[dict[str, Any]]]:
    rows = env.client.get(f"{env.rules}/catalog/exercises", headers=auth(p)).json()
    index: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        names = {row["name"].lower()}
        name_es = (row.get("details") or {}).get("nameEs")
        if name_es:
            names.add(str(name_es).lower())
        for n in names:
            index.setdefault(n, []).append(row)
    return index


# --- Escenarios ----------------------------------------------------------------------------


def chat(env: Env, base: str, p: Persona, text: str) -> dict[str, Any]:
    env.client.delete(f"{base}/agent/conversation", headers=auth(p))
    r = env.client.post(f"{base}/agent/message", json={"text": text}, headers=auth(p))
    r.raise_for_status()
    data = r.json()
    if data.get("handoff") == "guided":
        draft = env.client.post(f"{base}/chat/draft", json={"text": text}, headers=auth(p)).json()
        return {"reply": draft.get("message"), "cards": [], "source": "guided", "tools": []}
    return {"reply": data["reply"], "cards": data.get("cards", []), "source": data["source"],
            "tools": data.get("toolsUsed", []), "actions": data.get("actions", [])}


def render_chat(out: dict[str, Any]) -> str:
    lines = [str(out.get("reply") or "")]
    for card in out.get("cards") or []:
        lines.append(f"[Tarjeta: {card['title']}]")
        for section in card.get("sections", []):
            if section.get("title"):
                lines.append(f"  {section['title']}")
            for item in section.get("items", []):
                extra = " · ".join(x for x in (item.get("subtitle"), item.get("badge"), item.get("detail")) if x)
                lines.append(f"  - {item['title']}" + (f" ({extra})" if extra else ""))
    for action in out.get("actions") or []:
        lines.append(f"[Propuesta: {action.get('summary')}]")
    return "\n".join(lines)


def guided_plan(env: Env, base: str, p: Persona, save: bool) -> dict[str, Any]:
    env.client.post(f"{base}/chat/plan/cancel", json={}, headers=auth(p))
    last: dict[str, Any] = {}
    for answer in p.plan_answers:
        last = env.client.post(f"{base}/chat/draft", json={"text": answer}, headers=auth(p)).json()
    if last.get("planStatus") != "ready":
        return {"error": f"el asistente no llegó al resumen: {last.get('message')}", "raw": last}
    final = env.client.post(
        f"{base}/chat/draft", json={"text": "sí" if save else "no"}, headers=auth(p)
    ).json()
    return {"plan": last.get("plan"), "message": last.get("message"), "final": final.get("message")}


def render_plan(result: dict[str, Any]) -> str:
    plan = result.get("plan")
    if not plan:
        return f"(sin plan) {result.get('error')}"
    lines = [f"Plan: {plan.get('name')}"]
    names = {1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb", 7: "Dom"}
    for day in plan.get("days", []):
        head = f"{names[day['dayOfWeek']]} · {day['dayType']}"
        if day["dayType"] == "deporte":
            lines.append(f"{head}: {day.get('disciplineName')} {day.get('durationMin') or ''} min")
        elif day["dayType"] == "gimnasio":
            exs = []
            for ex in day.get("exercises", []):
                sets = ex.get("sets") or []
                rng = f"{sets[0]['targetRepsMin']}-{sets[0].get('targetRepsMax') or ''}" if sets else ""
                exs.append(f"{ex['name']} {len(sets)}x{rng}")
            lines.append(f"{head} ({day.get('label') or ''}): " + " | ".join(exs))
        else:
            lines.append(f"{head}")
    return "\n".join(lines)


def plan_checks(result: dict[str, Any], p: Persona, index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    plan = result.get("plan")
    if not plan:
        return {"ok": False, "motivo": "sin plan"}
    days = plan.get("days", [])
    sport_days = {d["dayOfWeek"] for d in days if d["dayType"] == "deporte"}
    equipment_violations: list[str] = []
    eve_leg_heavy: list[str] = []
    exercises_per_day: list[int] = []
    for day in days:
        if day["dayType"] != "gimnasio":
            continue
        exercises_per_day.append(len(day.get("exercises", [])))
        eve = (day["dayOfWeek"] % 7) + 1 in sport_days
        for ex in day.get("exercises", []):
            rows = index.get(ex["name"].lower(), [])
            if p.allowed is not None and rows and all(r.get("equipment") not in p.allowed for r in rows):
                equipment_violations.append(ex["name"])
            heavy = any(
                max((r.get("muscleMap") or {}).get(g, 0) for g in LEG_GROUPS) >= 0.5 for r in rows
            )
            if eve and heavy:
                eve_leg_heavy.append(f"{ex['name']} (día {day['dayOfWeek']})")
    return {
        "ok": not equipment_violations,
        "material_no_disponible": equipment_violations,
        "pierna_vispera_deporte": eve_leg_heavy,
        "ejercicios_por_dia": exercises_per_day,
        "dias_gimnasio": len(exercises_per_day),
    }


# --- Juez ----------------------------------------------------------------------------------

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "a": {"type": "object", "properties": {
            "puntuacion": {"type": "integer", "minimum": 0, "maximum": 10},
            "valida": {"type": "boolean"},
            "problemas": {"type": "array", "items": {"type": "string"}}},
            "required": ["puntuacion", "valida", "problemas"]},
        "b": {"type": "object", "properties": {
            "puntuacion": {"type": "integer", "minimum": 0, "maximum": 10},
            "valida": {"type": "boolean"},
            "problemas": {"type": "array", "items": {"type": "string"}}},
            "required": ["puntuacion", "valida", "problemas"]},
        "ganador": {"type": "string", "enum": ["a", "b", "empate"]},
        "motivo": {"type": "string"},
    },
    "required": ["a", "b", "ganador", "motivo"],
}

JUDGE_SYSTEM = """Eres un preparador físico titulado y evaluador imparcial. Comparas dos respuestas
(A y B) de una app de entrenamiento a la MISMA petición de un usuario. No sabes cómo se ha
generado cada una. Puntúa de 0 a 10 cada respuesta según esta rúbrica, en este orden de peso:
1) Correcta según la ciencia del entrenamiento (ejercicios, series, repeticiones, descansos, orden).
2) Segura (riesgo de lesión, carga razonable para el nivel, nada de pierna pesada justo antes de competir).
3) Adaptada a ESTE usuario (deporte, nivel, material disponible, objetivo, historial).
4) Útil y accionable (se puede hacer hoy en el gimnasio tal cual).
"valida" = una persona razonable podría seguirla sin perjuicio y responde a lo pedido.
No premies la longitud ni el estilo: valora el contenido. Una respuesta breve y correcta puede
ganar a una larga. Lista problemas concretos (no genéricos). Responde en español."""


def judge(env: Env, context: str, request: str, out_rules: str, out_ai: str, rng: random.Random) -> dict[str, Any]:
    swap = rng.random() < 0.5
    a, b = (out_ai, out_rules) if swap else (out_rules, out_ai)
    prompt = (
        f"PERFIL DEL USUARIO:\n{context}\n\nPETICIÓN:\n{request}\n\n"
        f"RESPUESTA A:\n{a}\n\nRESPUESTA B:\n{b}"
    )
    with tempfile.TemporaryDirectory(prefix="qa-judge-") as workdir:
        system_file = Path(workdir) / "system.txt"
        system_file.write_text(JUDGE_SYSTEM, encoding="utf-8")
        cmd = ["claude", "-p", "--model", env.judge_model, "--output-format", "json",
               "--json-schema", json.dumps(JUDGE_SCHEMA), "--system-prompt-file", str(system_file),
               "--tools", "", "--no-session-persistence"]
        proc = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, cwd=workdir, timeout=300, check=False)
    try:
        verdict = json.loads(proc.stdout)["structured_output"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return {"error": proc.stdout.decode("utf-8", "replace")[:300]}
    rules_key, ai_key = ("b", "a") if swap else ("a", "b")
    winner = verdict["ganador"]
    return {
        "reglas": verdict[rules_key],
        "ia": verdict[ai_key],
        "ganador": "empate" if winner == "empate" else ("reglas" if winner == rules_key else "ia"),
        "motivo": verdict["motivo"],
    }


def persona_context(p: Persona) -> str:
    prof = p.profile
    eq = prof.get("equipment") or {}
    sports = ", ".join(prof.get("sports") or []) or "ninguno (solo gimnasio)"
    return (
        f"Deporte: {sports}. Nivel: {prof.get('fitnessLevel')}. Objetivo general: {prof.get('goal')}. "
        f"Material: {eq.get('preset')}" + (f", le falta: {', '.join(eq.get('missing'))}" if eq.get("missing") else "")
        + f". Peso {prof.get('weightKg')} kg, {prof.get('heightCm')} cm."
    )


# --- Ejecución -----------------------------------------------------------------------------


PREV: dict[tuple[str, str], dict[str, Any]] = {}


def run(env: Env, out_dir: Path) -> list[dict[str, Any]]:
    rng = random.Random(14)
    suffix = datetime.now(UTC).strftime("%m%d%H%M")
    results: list[dict[str, Any]] = []

    def record(**entry: Any) -> None:
        results.append(entry)
        (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), "utf-8")
        print(f"- {entry.get('persona')} · {entry.get('escenario')} · {entry.get('veredicto', {}).get('ganador', '')}", flush=True)

    for p in PERSONAS:
        setup_persona(env, p, suffix)
        index = catalog_index(env, p)
        ctx = persona_context(p)

        # 1) Crear plan de cero con el asistente guiado (reglas guarda; IA solo se compara).
        plan_rules, use_r = timed(env, lambda: guided_plan(env, env.rules, p, save=True))
        prev = PREV.get((p.key, "crear plan"))
        if prev:
            ai_text, use_a, ai_checks = prev["salida"], prev["uso"], prev.get("checks")
        else:
            plan_ai, use_a = timed(env, lambda: guided_plan(env, env.llm, p, save=False))
            ai_text, ai_checks = render_plan(plan_ai), plan_checks(plan_ai, p, index)
        verdict = judge(env, ctx, "Crea mi plan semanal de entrenamiento con el asistente guiado "
                        f"(respuestas: {' / '.join(p.plan_answers[1:])}).",
                        render_plan(plan_rules), ai_text, rng)
        record(persona=p.key, escenario="crear plan", reglas={"salida": render_plan(plan_rules), "uso": use_r,
               "checks": plan_checks(plan_rules, p, index)},
               ia={"salida": ai_text, "uso": use_a, "checks": ai_checks},
               veredicto=verdict)

        # 2) Chat: objetivo, material que falta, consulta de datos y pregunta abierta.
        questions = [("objetivo", p.goal_question)]
        if p.full:
            questions += [("qué me toca", "¿Qué me toca el jueves?"), ("fatiga", "¿Cómo voy de fatiga?")]
            if p.missing_question:
                questions.append(("material que falta", p.missing_question))
            if p.open_question:
                questions.append(("pregunta abierta", p.open_question))
        for name, text in questions:
            out_r, use_r = timed(env, lambda t=text: chat(env, env.rules, p, t))
            prev = PREV.get((p.key, f"chat: {name}"))
            if prev:
                out_a, use_a = {"reply": prev["salida"], "source": prev.get("fuente")}, prev["uso"]
                ai_text = prev["salida"]
            else:
                out_a, use_a = timed(env, lambda t=text: chat(env, env.llm, p, t))
                ai_text = render_chat(out_a)
            verdict = judge(env, ctx, text, render_chat(out_r), ai_text, rng)
            record(persona=p.key, escenario=f"chat: {name}", pregunta=text,
                   reglas={"salida": render_chat(out_r), "fuente": out_r.get("source"), "uso": use_r},
                   ia={"salida": ai_text, "fuente": out_a.get("source"), "uso": use_a},
                   veredicto=verdict)

        if not p.full:
            continue

        # 3) Analizar la rutina: análisis determinista + redacción sin IA vs redacción de Claude.
        from app.api.analysis import narrative_payload
        from app.schemas.sport_analysis import SportAnalysisOut

        raw, use_base = timed(env, lambda: env.client.get(
            f"{env.rules}/analysis/sport", params={"basis": "rutina"}, headers=auth(p)).json())
        analysis = SportAnalysisOut.model_validate(raw)
        payload = narrative_payload(analysis)
        stub, use_r = timed(env, lambda: env.client.post(
            f"{env.parser_stub}/analyze/sport", json={"sportLabel": analysis.label, "analysis": payload},
            headers={"X-Internal-Token": env.internal_token}).json())
        prev = PREV.get((p.key, "analizar rutina"))
        ai, use_a = ({"narrative": {"source": prev.get("fuente")}}, prev["uso"]) if prev else timed(env, lambda: env.client.get(
            f"{env.rules}/analysis/sport", params={"basis": "rutina", "narrative": "true"}, headers=auth(p)).json())
        gaps = "\n".join(f"- {g.message}" for g in analysis.gaps[:6])
        rules_text = (f"Puntuación {analysis.score}/100.\nCarencias:\n{gaps}\n" + stub.get("resumen", "")
                      + "\nPrioridades: " + "; ".join(stub.get("prioridades", [])))
        narrative = ai.get("narrative") or {}
        ai_text = prev["salida"] if prev else (
            f"Puntuación {analysis.score}/100.\n{narrative.get('resumen', '')}\nPrioridades: "
            + "; ".join(narrative.get("prioridades", [])))
        verdict = judge(env, ctx, "Analiza mi rutina actual frente a lo que pide mi deporte.", rules_text, ai_text, rng)
        record(persona=p.key, escenario="analizar rutina", reglas={"salida": rules_text, "uso": use_r},
               ia={"salida": ai_text, "uso": use_a, "fuente": narrative.get("source")}, veredicto=verdict)

    # 4) Registrar entrenos: lista estructurada (sin IA) vs IA, y texto libre.
    boxer = next(x for x in PERSONAS if x.key == "boxer")
    structured = "press banca 4x8 70kg, dominadas 4x6, remo con barra 3x10 60kg"
    out_r, use_r = timed(env, lambda: env.client.post(
        f"{env.parser_llm}/parse", json={"requestId": "qa", "rawText": structured},
        headers={"X-Internal-Token": env.internal_token}).json())
    out_a, use_a = timed(env, lambda: env.client.post(
        f"{env.parser_llm}/parse", json={"requestId": "qa", "rawText": "Entreno de hoy: " + structured},
        headers={"X-Internal-Token": env.internal_token}).json())

    def render_draft(d: dict[str, Any]) -> str:
        exs = "; ".join(f"{e['name']} {e['sets']}x{e['reps']}" + (f" {e['weightKg']} kg" if e.get("weightKg") else "")
                        for e in d.get("exercises", []))
        return f"[{d.get('source')}] {d.get('discipline')}: {exs}"

    same = [(e["name"].lower(), e["sets"], e["reps"], e.get("weightKg")) for e in out_r.get("exercises", [])] == [
        (e["name"].lower(), e["sets"], e["reps"], e.get("weightKg")) for e in out_a.get("exercises", [])]
    record(persona="boxer", escenario="registrar entreno (lista)", pregunta=structured,
           reglas={"salida": render_draft(out_r), "uso": use_r}, ia={"salida": render_draft(out_a), "uso": use_a},
           veredicto={"ganador": "empate" if same else "revisar", "motivo": "mismo resultado ejercicio a ejercicio" if same else "difieren"})
    free = "Hoy he hecho 5 rounds de saco de 3 minutos, 15 minutos de comba y luego sentadilla 4x6 con 100 kilos"
    out_f, use_f = timed(env, lambda: env.client.post(
        f"{env.parser_llm}/parse", json={"requestId": "qa", "rawText": free},
        headers={"X-Internal-Token": env.internal_token}).json())
    record(persona="boxer", escenario="registrar entreno (texto libre)", pregunta=free,
           ia={"salida": json.dumps({k: out_f.get(k) for k in ("source", "discipline", "exercises", "metrics", "durationMinutes")}, ensure_ascii=False), "uso": use_f},
           veredicto={"ganador": "ia", "motivo": "texto libre: debe ir a la IA (esperado)"})

    # 5) Comidas: diccionario que aprende.
    runner = next(x for x in PERSONAS if x.key == "runner")
    meal = "un café con leche y una tostada con tomate y aceite"

    def parse_meal(person: Persona, text: str) -> dict[str, Any]:
        return env.client.post(f"{env.rules}/nutrition/meals/parse", json={"text": text}, headers=auth(person)).json()

    def kcal(res: dict[str, Any]) -> float:
        return round(sum(i["kcal100g"] * i["grams"] / 100 for i in res.get("items", [])), 1)

    first, use1 = timed(env, lambda: parse_meal(runner, meal))
    again, use2 = timed(env, lambda: parse_meal(runner, meal))
    other, use3 = timed(env, lambda: parse_meal(boxer, "café con leche, tostada con tomate y aceite"))
    items = first.get("items", [])
    coffee = next((i for i in again.get("items", []) if "caf" in i["name"].lower()), None)
    corrected_ok = None
    if coffee:
        bigger = {**coffee, "grams": round(coffee["grams"] * 1.5, 1)}
        env.client.post(f"{env.rules}/nutrition/meals/batch",
                        json={"eatenOn": datetime.now(UTC).date().isoformat(), "meal": "desayuno", "items": [bigger]},
                        headers=auth(runner)).raise_for_status()
        mine = parse_meal(runner, "café con leche")
        theirs = parse_meal(boxer, "café con leche")
        corrected_ok = {
            "mi_racion": mine["items"][0]["grams"] if mine.get("items") else None,
            "racion_guardada": bigger["grams"],
            "racion_de_otro": theirs["items"][0]["grams"] if theirs.get("items") else None,
        }
    record(persona="runner+boxer", escenario="comidas: diccionario que aprende", pregunta=meal,
           reglas={"salida": json.dumps({
               "1a_vez": {"fuente": first.get("source"), "kcal": kcal(first), "items": [(i["name"], i["grams"]) for i in items], "uso": use1},
               "2a_vez_mismo_usuario": {"fuente": again.get("source"), "kcal": kcal(again), "uso": use2},
               "otro_usuario": {"fuente": other.get("source"), "kcal": kcal(other), "uso": use3},
               "correccion_de_racion": corrected_ok,
           }, ensure_ascii=False, default=str)},
           veredicto={"ganador": "reglas" if again.get("source") == "rules" and use2["ai_calls"] == 0 else "revisar",
                      "motivo": "la segunda vez debe salir del diccionario sin IA y con las mismas kcal"})
    meal_chat = "He desayunado un café con leche y una tostada con tomate y aceite, apúntalo"
    out_r, use_r = timed(env, lambda: chat(env, env.rules, boxer, meal_chat))
    prev = PREV.get(("boxer", "chat: apuntar comida"))
    if prev:
        out_a, use_a, meal_ai_text = {"source": prev.get("fuente")}, prev["uso"], prev["salida"]
    else:
        out_a, use_a = timed(env, lambda: chat(env, env.llm, boxer, meal_chat))
        meal_ai_text = render_chat(out_a)
    verdict = judge(env, persona_context(boxer), meal_chat, render_chat(out_r), meal_ai_text, rng)
    record(persona="boxer", escenario="chat: apuntar comida", pregunta=meal_chat,
           reglas={"salida": render_chat(out_r), "fuente": out_r.get("source"), "uso": use_r},
           ia={"salida": meal_ai_text, "fuente": out_a.get("source"), "uso": use_a}, veredicto=verdict)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="http://127.0.0.1:8001")
    ap.add_argument("--llm", default="http://127.0.0.1:8002")
    ap.add_argument("--parser-llm", default="http://127.0.0.1:8101")
    ap.add_argument("--parser-stub", default="http://127.0.0.1:8102")
    ap.add_argument("--meter-log", required=True)
    ap.add_argument("--judge-model", default="sonnet")
    ap.add_argument("--out", required=True)
    ap.add_argument("--reuse-ai", help="results.json previo: reutiliza las respuestas del modo IA (ahorra llamadas)")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = Env(args.rules, args.llm, args.parser_llm, args.parser_stub, Path(args.meter_log),
              _internal_token(), args.judge_model)
    if args.reuse_ai:
        for entry in json.loads(Path(args.reuse_ai).read_text(encoding="utf-8")):
            if isinstance(entry.get("ia"), dict):
                PREV[(entry["persona"], entry["escenario"])] = entry["ia"]
    run(env, out_dir)


if __name__ == "__main__":
    main()
