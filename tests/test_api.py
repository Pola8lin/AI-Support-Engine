import os

from dotenv import load_dotenv
from fastapi.testclient import TestClient
import pytest

from src.app import app

load_dotenv()


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "AI Support Engine está funcionando."
    }


def test_analyze_access():
    response = client.post(
        "/api/analyze",
        json={
            "message": "No puedo iniciar sesión",
            "mode": "traditional"
        }
    )

    assert response.status_code == 200
    assert response.json()["category"] == "ACCESS"
    assert response.json()["priority"] == "HIGH"
    assert response.json()["mode"] == "traditional"


def test_analyze_security():
    response = client.post(
        "/api/analyze",
        json={
            "message": "Detectamos una filtración de datos",
            "mode": "traditional"
        }
    )

    assert response.status_code == 200
    assert response.json()["category"] == "SECURITY"
    assert response.json()["priority"] == "CRITICAL"
    assert response.json()["requiresHumanReview"] is True


def test_empty_message_returns_400():
    response = client.post(
        "/api/analyze",
        json={
            "message": "   ",
            "mode": "traditional"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "El mensaje no puede estar vacío."
    )


def test_generative_mode_not_configured_returns_503(monkeypatch):
    monkeypatch.setattr("src.api.routes.analyzer.generative_strategy", None)
    response = client.post(
        "/api/analyze",
        json={
            "message": "No puedo iniciar sesión",
            "mode": "generative"
        }
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El motor generativo no está configurado."
    )


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Se requiere GEMINI_API_KEY en .env para probar el endpoint generativo.",
)
def test_analyze_generative_mode():
    response = client.post(
        "/api/analyze",
        json={
            "message": "No puedo iniciar sesión en mi cuenta corporativa",
            "mode": "generative"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "ACCESS"
    assert data["priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert isinstance(data["response"], str) and data["response"].strip()
    assert isinstance(data["requiresHumanReview"], bool)
    assert data["mode"] == "generative"
