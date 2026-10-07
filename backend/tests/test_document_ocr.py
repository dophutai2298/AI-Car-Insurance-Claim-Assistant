import logging
import sys
from types import SimpleNamespace

import pytest

from app.services.document_ocr import DeepDocOcrAdapter, DocumentOcrError


def test_deepdoc_is_loaded_only_when_extraction_runs(monkeypatch, tmp_path):
    class FakeReader:
        def extract(self, source_path: str):
            return SimpleNamespace(text="Document text", markdown=None)

    monkeypatch.setitem(
        sys.modules, "deepdoc_vietocr", SimpleNamespace(DocumentReader=FakeReader)
    )
    adapter = DeepDocOcrAdapter()
    assert adapter.reader_type is None

    result = adapter.extract(SimpleNamespace(id=1), tmp_path / "document.jpg")

    assert result.raw_text == "Document text"
    assert adapter.reader_type is FakeReader


def test_deepdoc_failure_logs_the_provider_exception_without_exposing_it_to_the_ui(
    caplog: pytest.LogCaptureFixture,
    tmp_path,
):
    class FailingReader:
        def extract(self, source_path: str):
            raise RuntimeError("model cache is temporarily unavailable")

    adapter = DeepDocOcrAdapter.__new__(DeepDocOcrAdapter)
    adapter.reader_type = FailingReader
    adapter.reader = FailingReader()

    with caplog.at_level(logging.ERROR, logger="app.services.document_ocr"):
        with pytest.raises(DocumentOcrError) as captured:
            adapter.extract(None, tmp_path / "document.jpg")

    assert str(captured.value) == "DeepDoc OCR could not process this evidence image."
    assert "model cache is temporarily unavailable" in caplog.text
