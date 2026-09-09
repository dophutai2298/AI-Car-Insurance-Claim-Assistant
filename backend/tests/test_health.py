from fastapi.routing import APIRoute
from pydantic import ValidationError
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def call_registered_route(path: str):
    app = create_app()
    route = next(
        route for route in app.router.routes if isinstance(route, APIRoute) and route.path == path
    )
    return route.endpoint()


def test_health_endpoint_reports_service_and_runtime_config(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-health-tests")
    monkeypatch.setenv("CHECK_DATABASE_ON_HEALTH", "false")
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    response = call_registered_route("/api/health")

    assert response == {
        "status": "ok",
        "service": "ai-car-claim-assistant-api",
        "database": {"status": "not_checked"},
        "runtime": {
                "damage_model_mode": "mock",
                "damage_confidence_threshold": "0.7",
                "part_search_mode": "mock",
            "llm_mode": "mock",
            "upload_root": "uploads",
        },
    }


def test_runtime_config_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "super-secret-value-that-is-long-enough")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    get_settings.cache_clear()

    response = call_registered_route("/api/runtime-config")

    assert "jwt_secret" not in response
    assert "openai_api_key" not in response


def test_swagger_ui_and_openapi_schema_document_the_backend_api(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-documentation-tests")
    get_settings.cache_clear()
    app = create_app()

    client = TestClient(app)
    swagger_response = client.get("/docs")
    schema_response = client.get("/openapi.json")

    assert swagger_response.status_code == 200
    assert "Swagger UI" in swagger_response.text
    schema = schema_response.json()
    assert schema["info"]["title"] == "AI Car Insurance Claim Assistant API"
    assert schema["info"]["version"] == "0.1.0"
    assert {tag["name"] for tag in schema["tags"]} == {"admin", "auth", "claims", "system"}
    assert "/api/claims/{claim_number}/damage-analysis" in schema["paths"]


def test_short_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "too-short")
    get_settings.cache_clear()

    with pytest.raises(ValidationError):
        get_settings()
