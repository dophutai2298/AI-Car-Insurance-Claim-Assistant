from pathlib import Path

from app.core.config import ROOT_DIR


def test_runtime_configuration_example_is_compact_and_discovers_supported_integrations() -> None:
    example = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

    for key in (
        "DATABASE_URL",
        "JWT_SECRET",
        "UPLOAD_ROOT",
        "DOCUMENT_OCR_MODE",
        "DAMAGE_MODEL_PATH",
        "LLM_MODE",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "LLM_BASE_URL",
        "FRONTEND_ORIGIN",
    ):
        assert f"{key}=" in example

    assert "URL_MODEL=" not in example
    assert "OPENAI_API_KEY=replace-with" not in example
    assert Path(ROOT_DIR / ".env.example").is_file()
