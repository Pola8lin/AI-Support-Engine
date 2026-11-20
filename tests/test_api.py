from fastapi.testclient import TestClient

from src.app import app


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


def test_generative_mode_not_configured_returns_503():
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
