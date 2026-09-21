import logging

import pytest

from app.services.document_ocr import DeepDocOcrAdapter, DocumentOcrError


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
