from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings

CHUNK_SIZE = 1024 * 1024


class EvidenceStorageError(Exception):
    pass


@dataclass(frozen=True)
class StoredEvidence:
    relative_path: str
    original_filename: str
    content_type: str | None
    file_size: int


class EvidenceStorage(Protocol):
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
            raise EvidenceStorageError(f"A maximum of {self.max_files} evidence files can be uploaded at once")

        directory = self.root / claim_number
        written_paths: list[Path] = []
        saved: list[StoredEvidence] = []

        try:
            directory.mkdir(parents=True, exist_ok=True)
            for upload in files:
                original_filename = Path(upload.filename or "").name
                if not original_filename:
                    raise EvidenceStorageError("Each uploaded file must have a filename")

                destination = directory / f"{uuid4().hex}{Path(original_filename).suffix.lower()}"
                written_paths.append(destination)
                file_size = self._write_upload(upload, destination)
                saved.append(
                    StoredEvidence(
                        relative_path=destination.relative_to(self.root).as_posix(),
                        original_filename=original_filename,
                        content_type=upload.content_type,
                        file_size=file_size,
                    )
                )
        except Exception as error:
            self.delete_paths(written_paths)
            raise EvidenceStorageError("Unable to store uploaded evidence") from error

        return saved

    def _write_upload(self, upload: UploadFile, destination: Path) -> int:
        file_size = 0
        with destination.open("xb") as output:
            while chunk := upload.file.read(CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > self.max_file_size_bytes:
                    raise EvidenceStorageError(
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
