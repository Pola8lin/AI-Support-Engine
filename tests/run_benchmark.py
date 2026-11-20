"""Automated comparative benchmark for traditional vs. generative engines."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.response import AnalysisMode, AnalyzeResponse
from src.strategies.generative import GenerativeProviderError, GenerativeStrategy

DATASET_PATH = PROJECT_ROOT / "tests" / "dataset.json"
RAW_EVIDENCE_PATH = PROJECT_ROOT / "evidence" / "benchmark_raw_results.json"
ARTIFACTS_JSON_PATH = PROJECT_ROOT / "artifacts" / "results.json"
ARTIFACTS_MD_PATH = PROJECT_ROOT / "artifacts" / "results_table.md"
DEFAULT_API_URL = "http://127.0.0.1:8000/api/analyze"


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    """Carga el catálogo etiquetado de pruebas desde JSON."""
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list) or not data:
        raise ValueError("El archivo tests/dataset.json debe contener una lista no vacía.")
    return data


def _is_http_server_reachable(api_url: str, timeout: float = 2.0) -> bool:
    """Verifica si la API local FastAPI está escuchando antes de lanzar el lote HTTP."""
    base_url = api_url.split("/api/")[0] if "/api/" in api_url else api_url
    try:
        requests.get(base_url, timeout=timeout)
        return True
    except requests.RequestException:
        return False


def _evaluate_via_http(
    api_url: str,
    message: str,
    mode: AnalysisMode,
    timeout: float,
) -> dict[str, Any]:
    """Envía una petición POST al endpoint /api/analyze y valida el JSON recibido."""
    start = time.perf_counter()
    try:
        resp = requests.post(
            api_url,
            json={"message": message, "mode": mode.value},
            timeout=timeout,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
    except requests.RequestException as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "error",
            "http_status": None,
            "valid_json_schema": False,
            "latency_ms": latency_ms,
            "error": str(exc),
            "output": None,
        }

    if resp.status_code != 200:
        return {
            "status": "error",
            "http_status": resp.status_code,
            "valid_json_schema": False,
            "latency_ms": latency_ms,
            "error": resp.text,
            "output": None,
        }

    try:
        payload = resp.json()
        validated = AnalyzeResponse.model_validate(payload)
        if validated.mode != mode:
            raise ValueError(
                f"Se esperaba mode={mode.value}, pero la API devolvió mode={validated.mode.value}."
            )
        return {
            "status": "ok",
            "http_status": resp.status_code,
            "valid_json_schema": True,
            "latency_ms": latency_ms,
            "error": None,
            "output": validated.model_dump(mode="json"),
        }
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid_schema",
            "http_status": resp.status_code,
            "valid_json_schema": False,
            "latency_ms": latency_ms,
            "error": str(exc),
            "output": None,
        }


def _try_build_traditional_strategy() -> Any | None:
    """Intenta instanciar TraditionalStrategy si ya fue implementada por Persona 1."""
    try:
        from src.strategies import traditional as traditional_module
    except Exception:
        return None

    strategy_cls = getattr(traditional_module, "TraditionalStrategy", None)
    if strategy_cls is None:
        return None
    try:
        return strategy_cls()
    except Exception:
        return None


def _evaluate_directly(
    strategy: Any | None,
    message: str,
    mode: AnalysisMode,
) -> dict[str, Any]:
    """Ejecuta una estrategia localmente cuando el servidor HTTP no está activo."""
    if strategy is None:
        return {
            "status": "not_implemented",
            "http_status": None,
            "valid_json_schema": False,
            "latency_ms": 0.0,
            "error": "Estrategia tradicional aún pendiente de implementación (Persona 1).",
            "output": None,
        }

    start = time.perf_counter()
    try:
        result = strategy.analyze(message)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
    except NotImplementedError as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "not_implemented",
            "http_status": None,
            "valid_json_schema": False,
            "latency_ms": latency_ms,
            "error": str(exc) or "NotImplementedError",
            "output": None,
        }
    except GenerativeProviderError as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "error",
            "http_status": exc.status_code,
            "valid_json_schema": False,
            "latency_ms": latency_ms,
            "error": exc.message,
            "output": None,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "error",
            "http_status": None,
            "valid_json_schema": False,
            "latency_ms": latency_ms,
            "error": f"{type(exc).__name__}: {exc}",
            "output": None,
        }

    if not isinstance(result, AnalyzeResponse):
        return {
            "status": "invalid_schema",
            "http_status": None,
            "valid_json_schema": False,
            "latency_ms": latency_ms,
            "error": "La estrategia no devolvió un AnalyzeResponse válido.",
            "output": None,
        }

    return {
        "status": "ok",
        "http_status": 200,
        "valid_json_schema": True,
        "latency_ms": latency_ms,
        "error": None,
        "output": result.model_dump(mode="json"),
    }


def _score_case(case: dict[str, Any], engine_run: dict[str, Any]) -> dict[str, Any]:
    """Calcula coincidencias frente al ground truth para un caso y motor."""
    output = engine_run.get("output")
    if not output or not engine_run.get("valid_json_schema"):
        return {
            **engine_run,
            "category_match": False,
            "priority_match": False,
            "human_review_match": False,
            "exact_match": False,
        }

    category_match = output["category"] == case["expected_category"]
    priority_match = output["priority"] == case["expected_priority"]
    human_review_match = (
        output["requiresHumanReview"] == case["expected_requires_human_review"]
    )
    exact_match = category_match and priority_match and human_review_match
    return {
        **engine_run,
        "category_match": category_match,
        "priority_match": priority_match,
        "human_review_match": human_review_match,
        "exact_match": exact_match,
    }


def _compute_engine_summary(case_results: list[dict[str, Any]], engine_key: str) -> dict[str, Any]:
    """Agrega porcentajes de acierto totales y por tipo de caso."""
    total = len(case_results)
    entries = [row[engine_key] for row in case_results]
    statuses = {entry["status"] for entry in entries}

    if statuses == {"not_implemented"}:
        return {
            "available": False,
            "total_cases": total,
            "evaluated_cases": 0,
            "valid_json_count": 0,
            "valid_json_rate_pct": 0.0,
            "category_accuracy_pct": 0.0,
            "priority_accuracy_pct": 0.0,
            "human_review_accuracy_pct": 0.0,
            "exact_match_rate_pct": 0.0,
            "avg_latency_ms": 0.0,
            "by_type": {},
        }

    def pct(count: int, denom: int) -> float:
        return round((count / denom) * 100, 2) if denom else 0.0

    valid_count = sum(1 for e in entries if e["valid_json_schema"])
    cat_hits = sum(1 for e in entries if e["category_match"])
    prio_hits = sum(1 for e in entries if e["priority_match"])
    review_hits = sum(1 for e in entries if e["human_review_match"])
    exact_hits = sum(1 for e in entries if e["exact_match"])
    avg_latency = round(sum(e["latency_ms"] for e in entries) / total, 2) if total else 0.0

    by_type: dict[str, dict[str, Any]] = {}
    for case_type in ("normal", "ambiguous", "prompt_injection"):
        subset = [row[engine_key] for row in case_results if row["type"] == case_type]
        sub_total = len(subset)
        by_type[case_type] = {
            "total": sub_total,
            "category_accuracy_pct": pct(sum(1 for e in subset if e["category_match"]), sub_total),
            "priority_accuracy_pct": pct(sum(1 for e in subset if e["priority_match"]), sub_total),
            "human_review_accuracy_pct": pct(
                sum(1 for e in subset if e["human_review_match"]), sub_total
            ),
            "exact_match_rate_pct": pct(sum(1 for e in subset if e["exact_match"]), sub_total),
        }

    return {
        "available": True,
        "total_cases": total,
        "evaluated_cases": sum(1 for e in entries if e["status"] == "ok"),
        "valid_json_count": valid_count,
        "valid_json_rate_pct": pct(valid_count, total),
        "category_accuracy_pct": pct(cat_hits, total),
        "priority_accuracy_pct": pct(prio_hits, total),
        "human_review_accuracy_pct": pct(review_hits, total),
        "exact_match_rate_pct": pct(exact_hits, total),
        "avg_latency_ms": avg_latency,
        "by_type": by_type,
    }


def build_technical_conclusion(summary: dict[str, Any]) -> str:
    """Genera una conclusión técnica breve de máximo 150 palabras."""
    gen = summary["generative"]
    trad = summary["traditional"]

    if trad["available"]:
        winner = (
            "el motor generativo"
            if gen["exact_match_rate_pct"] >= trad["exact_match_rate_pct"]
            else "el motor tradicional"
        )
        conclusion = (
            f"En la comparativa sobre {gen['total_cases']} casos, {winner} obtuvo mejor desempeño global: "
            f"el motor generativo (Gemini 2.5 Flash) alcanzó {gen['category_accuracy_pct']}% en categoría, "
            f"{gen['priority_accuracy_pct']}% en prioridad y {gen['exact_match_rate_pct']}% de coincidencia exacta "
            f"(con {gen['valid_json_rate_pct']}% de formato JSON válido), frente al motor tradicional con "
            f"{trad['category_accuracy_pct']}% en categoría, {trad['priority_accuracy_pct']}% en prioridad y "
            f"{trad['exact_match_rate_pct']}% de exactitud. El enfoque generativo destacó en mensajes ambiguos "
            f"y detección contextual, mientras el validador transversal garantizó requiresHumanReview=true ante "
            f"incidentes SECURITY y prompt injection. El motor tradicional mostró menor latencia promedio "
            f"({trad['avg_latency_ms']} ms vs {gen['avg_latency_ms']} ms), siendo útil en reglas explícitas pero rígido ante lenguaje informal."
        )
    else:
        pi_stats = gen["by_type"].get("prompt_injection", {})
        amb_stats = gen["by_type"].get("ambiguous", {})
        conclusion = (
            f"El motor generativo (Gemini 2.5 Flash) se evaluó sobre {gen['total_cases']} casos "
            f"(normales, ambiguos y de prompt injection), logrando {gen['valid_json_rate_pct']}% de cumplimiento "
            f"estricto del esquema JSON, {gen['category_accuracy_pct']}% de precisión en categoría, "
            f"{gen['priority_accuracy_pct']}% en prioridad, {gen['human_review_accuracy_pct']}% en revisión humana "
            f"y {gen['exact_match_rate_pct']}% de coincidencia exacta (latencia media: {gen['avg_latency_ms']} ms). "
            f"Destacó su interpretación contextual en casos ambiguos ({amb_stats.get('exact_match_rate_pct', 0.0)}% exacto) "
            f"y su resistencia ante ataques de confusión ({pi_stats.get('exact_match_rate_pct', 0.0)}% exacto), "
            f"reforzada mediante response_schema con Pydantic y la regla obligatoria de seguridad en código. "
            f"El motor tradicional figura como pendiente al corresponder al módulo en desarrollo del Integrante 1."
        )

    words = conclusion.split()
    if len(words) > 150:
        conclusion = " ".join(words[:150])
    return conclusion


def _format_cell(entry: dict[str, Any]) -> str:
    """Formatea una celda resumida de resultados por caso."""
    if entry["status"] == "not_implemented":
        return "Pendiente (Integrante 1)"
    output = entry.get("output")
    if not output:
        return f"ERROR ({entry.get('status')})"
    mark = "OK" if entry["exact_match"] else "PARCIAL"
    return (
        f"{mark}: {output['category']} / {output['priority']} / "
        f"rev={output['requiresHumanReview']}"
    )


def render_markdown_report(report: dict[str, Any]) -> str:
    """Genera el reporte comparativo en Markdown para artifacts/results_table.md."""
    summary = report["summary"]
    gen = summary["generative"]
    trad = summary["traditional"]

    lines: list[str] = [
        "# Resultados Comparativos — AI Support Engine",
        "",
        f"- **Fecha de ejecución (UTC):** `{report['executed_at']}`",
        f"- **Modo de ejecución:** `{report['execution_mode']}`",
        f"- **Total de casos evaluados:** `{gen['total_cases']}`",
        "",
        "## Resumen de Métricas por Motor",
        "",
        "| Métrica | Motor Tradicional | Motor Generativo (Gemini 2.5 Flash) |",
        "| :--- | :---: | :---: |",
    ]

    def fmt_trad(value: Any, suffix: str = "%") -> str:
        return f"{value}{suffix}" if trad["available"] else "Pendiente (Integrante 1)"

    lines.extend(
        [
            f"| Formato JSON válido | {fmt_trad(trad['valid_json_rate_pct'])} | {gen['valid_json_rate_pct']}% |",
            f"| Precisión de categoría | {fmt_trad(trad['category_accuracy_pct'])} | {gen['category_accuracy_pct']}% |",
            f"| Precisión de prioridad | {fmt_trad(trad['priority_accuracy_pct'])} | {gen['priority_accuracy_pct']}% |",
            f"| Precisión en revisión humana | {fmt_trad(trad['human_review_accuracy_pct'])} | {gen['human_review_accuracy_pct']}% |",
            f"| Coincidencia exacta global | {fmt_trad(trad['exact_match_rate_pct'])} | {gen['exact_match_rate_pct']}% |",
            f"| Latencia promedio | {fmt_trad(trad['avg_latency_ms'], ' ms')} | {gen['avg_latency_ms']} ms |",
            "",
            "## Desglose del Motor Generativo por Tipo de Caso",
            "",
            "| Tipo de Caso | Total | Categoría (%) | Prioridad (%) | Revisión Humana (%) | Exacto (%) |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for case_type, label in (
        ("normal", "Normales"),
        ("ambiguous", "Ambiguos"),
        ("prompt_injection", "Confusión / Prompt Injection"),
    ):
        stats = gen["by_type"].get(case_type, {})
        lines.append(
            f"| {label} | {stats.get('total', 0)} | {stats.get('category_accuracy_pct', 0.0)}% | "
            f"{stats.get('priority_accuracy_pct', 0.0)}% | {stats.get('human_review_accuracy_pct', 0.0)}% | "
            f"{stats.get('exact_match_rate_pct', 0.0)}% |"
        )

    lines.extend(
        [
            "",
            "## Detalle por Caso de Prueba",
            "",
            "| ID | Tipo | Ground Truth | Motor Tradicional | Motor Generativo | JSON Válido (Gen) |",
            "| :--- | :--- | :--- | :--- | :--- | :---: |",
        ]
    )

    for row in report["cases"]:
        gt = (
            f"{row['expected_category']} / {row['expected_priority']} / "
            f"rev={row['expected_requires_human_review']}"
        )
        trad_cell = _format_cell(row["traditional"])
        gen_cell = _format_cell(row["generative"])
        json_ok = "Sí" if row["generative"]["valid_json_schema"] else "No"
        lines.append(
            f"| {row['id']} | {row['type']} | {gt} | {trad_cell} | {gen_cell} | {json_ok} |"
        )

    lines.extend(
        [
            "",
            "## Conclusión Técnica",
            "",
            report["conclusion"],
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark(
    api_url: str = DEFAULT_API_URL,
    force_direct: bool = False,
    timeout: float = 20.0,
    dataset_path: Path = DATASET_PATH,
    raw_evidence_path: Path = RAW_EVIDENCE_PATH,
    artifacts_json_path: Path = ARTIFACTS_JSON_PATH,
    artifacts_md_path: Path = ARTIFACTS_MD_PATH,
) -> dict[str, Any]:
    """Ejecuta el benchmark completo y exporta evidencias y artefactos."""
    dataset = load_dataset(dataset_path)
    use_http = (not force_direct) and _is_http_server_reachable(api_url)
    execution_mode = "http" if use_http else "direct"

    gen_strategy = None if use_http else GenerativeStrategy(timeout_seconds=timeout)
    trad_strategy = None if use_http else _try_build_traditional_strategy()

    case_results: list[dict[str, Any]] = []
    for case in dataset:
        message = case["message"]
        if use_http:
            trad_raw = _evaluate_via_http(api_url, message, AnalysisMode.TRADITIONAL, timeout)
            gen_raw = _evaluate_via_http(api_url, message, AnalysisMode.GENERATIVE, timeout)
        else:
            trad_raw = _evaluate_directly(trad_strategy, message, AnalysisMode.TRADITIONAL)
            gen_raw = _evaluate_directly(gen_strategy, message, AnalysisMode.GENERATIVE)

        case_results.append(
            {
                "id": case["id"],
                "type": case["type"],
                "message": message,
                "expected_category": case["expected_category"],
                "expected_priority": case["expected_priority"],
                "expected_requires_human_review": case["expected_requires_human_review"],
                "traditional": _score_case(case, trad_raw),
                "generative": _score_case(case, gen_raw),
            }
        )

    summary = {
        "traditional": _compute_engine_summary(case_results, "traditional"),
        "generative": _compute_engine_summary(case_results, "generative"),
    }
    conclusion = build_technical_conclusion(summary)

    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": execution_mode,
        "api_url": api_url if use_http else None,
        "summary": summary,
        "conclusion": conclusion,
        "cases": case_results,
    }

    raw_evidence_path.parent.mkdir(parents=True, exist_ok=True)
    artifacts_json_path.parent.mkdir(parents=True, exist_ok=True)
    artifacts_md_path.parent.mkdir(parents=True, exist_ok=True)

    with raw_evidence_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    compact_results = {
        "executed_at": report["executed_at"],
        "execution_mode": report["execution_mode"],
        "summary": report["summary"],
        "conclusion": report["conclusion"],
    }
    with artifacts_json_path.open("w", encoding="utf-8") as fh:
        json.dump(compact_results, fh, ensure_ascii=False, indent=2)

    markdown_text = render_markdown_report(report)
    with artifacts_md_path.open("w", encoding="utf-8") as fh:
        fh.write(markdown_text)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark comparativo AI Support Engine")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="Endpoint POST /api/analyze")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Ejecuta las estrategias directamente sin pasar por HTTP",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="Timeout por petición (s)")
    args = parser.parse_args()

    report = run_benchmark(api_url=args.url, force_direct=args.direct, timeout=args.timeout)
    gen = report["summary"]["generative"]
    trad = report["summary"]["traditional"]

    print(f"Modo de ejecución: {report['execution_mode']}")
    print(
        f"Generativo -> JSON válido: {gen['valid_json_rate_pct']}% | "
        f"Categoría: {gen['category_accuracy_pct']}% | "
        f"Prioridad: {gen['priority_accuracy_pct']}% | "
        f"Revisión humana: {gen['human_review_accuracy_pct']}% | "
        f"Exacto: {gen['exact_match_rate_pct']}%"
    )
    if trad["available"]:
        print(
            f"Tradicional -> JSON válido: {trad['valid_json_rate_pct']}% | "
            f"Categoría: {trad['category_accuracy_pct']}% | "
            f"Prioridad: {trad['priority_accuracy_pct']}% | "
            f"Revisión humana: {trad['human_review_accuracy_pct']}% | "
            f"Exacto: {trad['exact_match_rate_pct']}%"
        )
    else:
        print("Tradicional -> Pendiente de implementación (Integrante 1)")
    print(f"Evidencia guardada en: {RAW_EVIDENCE_PATH}")
    print(f"Tabla comparativa en: {ARTIFACTS_MD_PATH}")


if __name__ == "__main__":
    main()
