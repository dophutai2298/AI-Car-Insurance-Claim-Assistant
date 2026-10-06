import builtins

from sqlalchemy.orm import Session

from app.api.composition import build_claim_service
from app.core.config import Settings


def test_listing_service_does_not_import_analysis_engines(monkeypatch):
    settings = Settings(_env_file=None, JWT_SECRET="unit-test-secret-123456").model_copy(
        update={
            "document_ocr_mode": "deepdoc",
            "llm_mode": "openai",
            "openai_api_key": "test-key",
            "openai_model": "test-model",
        }
    )
    original_import = builtins.__import__

    def reject_analysis_import(name, *args, **kwargs):
        if name.split(".", 1)[0] in {"deepdoc_vietocr", "langchain_openai"}:
            raise AssertionError(f"Analysis engine imported while listing claims: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_analysis_import)
    with Session() as session:
        service = build_claim_service(session, settings)

    assert service is not None
