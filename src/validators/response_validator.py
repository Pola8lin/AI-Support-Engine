"""Generated response validation and mandatory security enforcement."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from pydantic import BaseModel, Field

from src.models.response import AnalysisMode, AnalyzeResponse, Category, Priority


class GenerativeLLMOutput(BaseModel):
    """Esquema estructurado esperado directamente desde el modelo generativo."""

    category: Category
    priority: Priority
    response: str = Field(min_length=1)
    requiresHumanReview: bool


PROMPT_INJECTION_PATTERNS: tuple[str, ...] = (
    r"ignora\s+(?:todas\s+|las\s+|tus\s+)?instrucciones",
    r"ignore\s+(?:all\s+|previous\s+)?instructions",
    r"olvida\s+(?:las\s+reglas|el\s+esquema|todo\s+lo\s+anterior)",
    r"system\s*(?:prompt|override)",
    r"clasific(?:a|alo)\s+.*(?:prioridad\s+baja|\blow\b|\bfeature\b)",
    r"(?:cambia|altera|olvida)\s+(?:el\s+)?(?:formato|esquema)\s+json",
    r"(?:devuelve|responde)\s+(?:solo|unicamente)\s+con",
    r"\bactua\s+como\b",
    r"\bmodo\s+desarrollador\b",
    r"\bbypass\b",
    r"requireshumanreview[\"\'\s:=]+false",
    r"(?:extraigo|exfiltr\w*|dump)\s+.*(?:tabla|usuarios|credenciales|tokens)",
)

SECURITY_SIGNAL_PATTERNS: tuple[str, ...] = (
    r"\bvulnerabilidad(?:es)?\b",
    r"\binyeccion\s+sql\b",
    r"\bsql\s+injection\b",
    r"\bsqli\b",
    r"\bxss\b",
    r"\bbrecha(?:\s+de\s+seguridad)?\b",
    r"\bacceso\s+no\s+autorizado\b",
    r"\bcredenciales\s+expuestas\b",
    r"\btoken(?:s)?\s+(?:jwt\s+)?(?:filtrado|filtrados|expuesto|expuestos)\b",
    r"\b(?:devuelve|expone|filtra)\s+.*(?:tokens|hashes|contrasenas|registros\s+de\s+clientes)\b",
    r"\bransomware\b",
    r"\bphishing\b",
    r"\bexploit\b",
    r"\bcve-\d{4}-\d+\b",
    r"\bsesion\s+abierta\s+desde\s+una\s+ip\b",
    r"\bip\s+en\s+otro\s+pais\s+que\s+no\s+reconozco\b",
    r"\bsin\s+autenticacion\b",
)

_COMPILED_INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in PROMPT_INJECTION_PATTERNS
)
_COMPILED_SECURITY_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in SECURITY_SIGNAL_PATTERNS
)


def _normalize_text(text: str) -> str:
    """Normaliza a minúsculas sin diacríticos para evaluar patrones de seguridad."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents).strip().lower()


def has_prompt_injection_signals(text: str) -> bool:
    """Detecta señales de manipulación o intento de prompt injection."""
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _COMPILED_INJECTION_PATTERNS)


def has_security_incident_signals(text: str) -> bool:
    """Detecta señales explícitas de vulnerabilidad o incidente de seguridad."""
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _COMPILED_SECURITY_PATTERNS)


def _extract_raw_dict(
    raw_response: dict[str, Any] | str | AnalyzeResponse | GenerativeLLMOutput,
) -> dict[str, Any]:
    """Convierte la respuesta cruda a diccionario validando que sea JSON válido."""
    if isinstance(raw_response, str):
        cleaned = raw_response.strip()
        if not cleaned:
            raise ValueError("La respuesta JSON del motor generativo está vacía.")
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"La respuesta generada no es un JSON válido: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("El JSON generado debe ser un objeto con las claves del contrato.")
        return parsed

    if isinstance(raw_response, BaseModel):
        return raw_response.model_dump()

    if isinstance(raw_response, dict):
        return dict(raw_response)

    raise ValueError(
        f"Tipo de respuesta no soportado para validación: {type(raw_response).__name__}."
    )


def validate_and_enforce_response(
    raw_response: dict[str, Any] | str | AnalyzeResponse | GenerativeLLMOutput,
    original_message: str = "",
    mode: AnalysisMode = AnalysisMode.GENERATIVE,
) -> AnalyzeResponse:
    """
    Valida estrictamente el contrato JSON de salida y aplica la regla transversal
    de seguridad (requiresHumanReview=True ante SECURITY o prompt injection).
    """
    data = _extract_raw_dict(raw_response)

    raw_category = data.get("category")
    valid_categories = {item.value for item in Category}
    if not isinstance(raw_category, str) or raw_category not in valid_categories:
        raise ValueError(
            f"Categoría inválida '{raw_category}'. Valores permitidos: {sorted(valid_categories)}."
        )
    category = Category(raw_category)

    raw_priority = data.get("priority")
    valid_priorities = {item.value for item in Priority}
    if not isinstance(raw_priority, str) or raw_priority not in valid_priorities:
        raise ValueError(
            f"Prioridad inválida '{raw_priority}'. Valores permitidos: {sorted(valid_priorities)}."
        )
    priority = Priority(raw_priority)

    raw_text = data.get("response")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("El campo 'response' debe ser una cadena de texto no vacía.")
    cleaned_response = raw_text.strip()

    raw_human_review = data.get("requiresHumanReview")
    if not isinstance(raw_human_review, bool):
        raise ValueError("El campo 'requiresHumanReview' debe ser estrictamente booleano.")
    requires_human_review = raw_human_review

    if "mode" in data and data["mode"] is not None:
        raw_mode = data["mode"]
        valid_modes = {item.value for item in AnalysisMode}
        mode_str = raw_mode.value if isinstance(raw_mode, AnalysisMode) else raw_mode
        if not isinstance(mode_str, str) or mode_str not in valid_modes:
            raise ValueError(
                f"Modo inválido '{raw_mode}'. Valores permitidos: {sorted(valid_modes)}."
            )
    validated_mode = AnalysisMode(mode)

    # Regla transversal de seguridad obligatoria desde código
    if has_prompt_injection_signals(original_message):
        category = Category.SECURITY
        requires_human_review = True
        if priority in (Priority.LOW, Priority.MEDIUM):
            priority = Priority.CRITICAL

    if category == Category.SECURITY or has_security_incident_signals(original_message):
        requires_human_review = True

    return AnalyzeResponse(
        category=category,
        priority=priority,
        response=cleaned_response,
        requiresHumanReview=requires_human_review,
        mode=validated_mode,
    )


validate_response = validate_and_enforce_response


class ResponseValidator:
    """Wrapper orientado a objetos para validar y endurecer respuestas."""

    @staticmethod
    def validate(
        raw_response: dict[str, Any] | str | AnalyzeResponse | GenerativeLLMOutput,
        original_message: str = "",
        mode: AnalysisMode = AnalysisMode.GENERATIVE,
    ) -> AnalyzeResponse:
        return validate_and_enforce_response(
            raw_response=raw_response,
            original_message=original_message,
            mode=mode,
        )
