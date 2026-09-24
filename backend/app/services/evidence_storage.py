from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings

CHUNK_SIZE = 1024 * 1024
logger = logging.getLogger(__name__)

SAFE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
}


def detect_safe_media_type(path: Path, filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    expected = SAFE_MEDIA_TYPES.get(suffix)
    if expected is None:
        return None
    with path.open("rb") as stream:
        header = stream.read(16)
    signatures = {
        "image/jpeg": header.startswith(b"\xff\xd8\xff"),
        "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
        "image/bmp": header.startswith(b"BM"),
        "image/tiff": header.startswith((b"II*\x00", b"MM\x00*")),
        "application/pdf": header.startswith(b"%PDF-"),
    }
    return expected if signatures[expected] else None


class EvidenceStorageError(Exception):
    pass


class EvidenceValidationError(EvidenceStorageError):
    pass


@dataclass(frozen=True)
class StoredEvidence:
    relative_path: str
    original_filename: str
    content_type: str | None
    file_size: int


class EvidenceStorage(Protocol):
    max_files: int

    def save_all(self, claim_number: str, files: list[UploadFile]) -> list[StoredEvidence]: ...

    def resolve_path(self, relative_path: str) -> Path: ...

    def delete_stored(self, uploads: list[StoredEvidence]) -> None: ...

    def delete(self, relative_path: str) -> None: ...


class LocalEvidenceStorage:
    def __init__(self, settings: Settings):
        self.root = settings.upload_root_path().resolve()
        self.max_files = settings.max_evidence_files
        self.max_file_size_bytes = settings.max_evidence_file_size_bytes

    def save_all(self, claim_number: str, files: list[UploadFile]) -> list[StoredEvidence]:
        if len(files) > self.max_files:
            raise EvidenceValidationError(f"A maximum of {self.max_files} evidence files can be uploaded at once")

        directory = (self.root / claim_number).resolve()
        if not directory.is_relative_to(self.root):
            raise EvidenceStorageError("Stored evidence path is invalid")
        written_paths: list[Path] = []
        saved: list[StoredEvidence] = []

        try:
            directory.mkdir(parents=True, exist_ok=True)
            for upload in files:
                original_filename = (upload.filename or "").replace("\\", "/").split("/")[-1]
                if not original_filename or len(original_filename) > 255 or any(
                    ord(character) < 32 for character in original_filename
                ):
                    raise EvidenceValidationError("Each uploaded file must have a safe filename")
                expected_type = SAFE_MEDIA_TYPES.get(Path(original_filename).suffix.lower())
                if expected_type is None:
                    raise EvidenceValidationError("Only supported images and PDF documents can be uploaded")
                if upload.content_type not in {None, "application/octet-stream", expected_type}:
                    raise EvidenceValidationError("File extension and content type do not match")

                destination = directory / f"{uuid4().hex}{Path(original_filename).suffix.lower()}"
                written_paths.append(destination)
                file_size = self._write_upload(upload, destination)
                if detect_safe_media_type(destination, original_filename) != expected_type:
                    raise EvidenceValidationError("File content does not match a supported image or PDF")
                saved.append(
                    StoredEvidence(
                        relative_path=destination.relative_to(self.root).as_posix(),
                        original_filename=original_filename,
                        content_type=expected_type,
                        file_size=file_size,
                    )
                )
        except EvidenceValidationError:
            self.delete_paths(written_paths)
            raise
        except Exception:
            self.delete_paths(written_paths)
            logger.exception("Unable to store uploaded evidence")
            raise EvidenceStorageError("Unable to store uploaded evidence") from None

        return saved

    def _write_upload(self, upload: UploadFile, destination: Path) -> int:
        file_size = 0
        with destination.open("xb") as output:
            while chunk := upload.file.read(CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > self.max_file_size_bytes:
                    raise EvidenceValidationError(
                        f"Evidence files must not exceed {self.max_file_size_bytes} bytes"
                    )
                output.write(chunk)
        return file_size

    def resolve_path(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if not path.is_relative_to(self.root):
            raise EvidenceStorageError("Stored evidence path is invalid")
        return path

    def delete_stored(self, uploads: list[StoredEvidence]) -> None:
        self.delete_paths([self.resolve_path(upload.relative_path) for upload in uploads])

    def delete(self, relative_path: str) -> None:
        self.delete_paths([self.resolve_path(relative_path)])

    @staticmethod
    def delete_paths(paths: list[Path]) -> None:
        for path in paths:
            path.unlink(missing_ok=True)
