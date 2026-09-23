import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisSnapshotStatus,
    ConfirmedAnalysisSnapshot,
    DocumentExtractedField,
    WorkflowAnalysisRun,
)


class AnalysisSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_for_run(self, run_id: int) -> ConfirmedAnalysisSnapshot | None:
        return self.session.scalar(
            select(ConfirmedAnalysisSnapshot).where(
                ConfirmedAnalysisSnapshot.analysis_run_id == run_id
            )
        )

    def save_ready(
        self,
        run: WorkflowAnalysisRun,
        fields: list[DocumentExtractedField],
        values_by_id: dict[int, str],
        payload: dict[str, object],
    ) -> ConfirmedAnalysisSnapshot:
        for field in fields:
            field.confirmed_value = values_by_id[field.id]

        snapshot = self.find_for_run(run.id)
        if snapshot is None:
            snapshot = ConfirmedAnalysisSnapshot(
                analysis_run_id=run.id,
                input_revision=run.input_revision,
                status=AnalysisSnapshotStatus.READY,
                payload_json=json.dumps(payload, ensure_ascii=False),
            )
            self.session.add(snapshot)
        else:
            snapshot.input_revision = run.input_revision
            snapshot.status = AnalysisSnapshotStatus.READY
            snapshot.payload_json = json.dumps(payload, ensure_ascii=False)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def mark_stale(self, run_id: int) -> None:
        snapshot = self.find_for_run(run_id)
        if snapshot is not None and snapshot.status is not AnalysisSnapshotStatus.STALE:
            snapshot.status = AnalysisSnapshotStatus.STALE
            self.session.commit()
