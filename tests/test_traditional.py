import pytest

from src.models.response import (
    AnalyzeResponse,
    Category,
    Priority,
    AnalysisMode,
)
from src.strategies.traditional import TraditionalStrategy


@pytest.fixture
def strategy():
    return TraditionalStrategy()


def test_classifies_access(strategy):
    result = strategy.analyze("No puedo iniciar sesión")

    assert result.category == Category.ACCESS
    assert result.priority == Priority.HIGH
    assert result.mode == AnalysisMode.TRADITIONAL


def test_classifies_security(strategy):
    result = strategy.analyze(
        "Detectamos una filtración de datos"
    )

    assert result.category == Category.SECURITY
    assert result.priority == Priority.CRITICAL
    assert result.requiresHumanReview is True


def test_classifies_bug(strategy):
    result = strategy.analyze("La aplicación no funciona")

    assert result.category == Category.BUG
    assert result.priority == Priority.MEDIUM


def test_classifies_feature(strategy):
    result = strategy.analyze(
        "Me gustaría agregar una nueva función"
    )

    assert result.category == Category.FEATURE
    assert result.priority == Priority.LOW


def test_unknown_message_uses_default_category(strategy):
    result = strategy.analyze("Hola, necesito información")

    assert result.category == Category.BUG


def test_response_has_correct_structure(strategy):
    result = strategy.analyze("No puedo iniciar sesión")

    assert isinstance(result, AnalyzeResponse)
    assert result.response
    assert isinstance(result.requiresHumanReview, bool)
