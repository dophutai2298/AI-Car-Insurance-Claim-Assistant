from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import (
    WorkflowAnalysisRun,
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)


class WorkflowJobRepository:
    def __init__(self, session: Session):
        self.session = session

    def enqueue_analysis(self, run: WorkflowAnalysisRun, max_attempts: int) -> WorkflowJob:
        return self._enqueue(
            run,
            WorkflowJobType.ANALYSIS,
            f"analysis:{run.id}",
            max_attempts,
        )

    def enqueue_ai_review(self, run: WorkflowAnalysisRun, max_attempts: int) -> WorkflowJob:
        return self._enqueue(
            run,
            WorkflowJobType.AI_REVIEW,
            f"ai-review:{run.id}:{uuid4().hex}",
            max_attempts,
        )

    def _enqueue(
        self,
        run: WorkflowAnalysisRun,
        job_type: WorkflowJobType,
        dedupe_key: str,
        max_attempts: int,
    ) -> WorkflowJob:
        existing = self.session.scalar(
            select(WorkflowJob).where(WorkflowJob.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return existing
        job = WorkflowJob(
            job_type=job_type,
            claim_id=run.claim_id,
            analysis_run_id=run.id,
            dedupe_key=dedupe_key,
            max_attempts=max_attempts,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def recover_stale(self, lease_seconds: int) -> list[WorkflowJob]:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(seconds=lease_seconds)
        stale_jobs = list(
            self.session.scalars(
                select(WorkflowJob)
                .where(
                    WorkflowJob.status == WorkflowJobStatus.PROCESSING,
                    WorkflowJob.locked_at < stale_before,
                )
                .with_for_update(skip_locked=True)
            )
        )
        terminal: list[WorkflowJob] = []
        for stale in stale_jobs:
            stale.locked_at = None
            stale.locked_by = None
            if stale.attempts >= stale.max_attempts:
                stale.status = WorkflowJobStatus.FAILED
                stale.progress_stage = "FAILED"
                stale.completed_at = now
                stale.failure_reason = "Worker lease expired after the final attempt"
                terminal.append(stale)
            else:
                stale.status = WorkflowJobStatus.PENDING
                stale.available_at = now
                stale.progress_stage = "RECOVERED"
        self.session.commit()
        return terminal

    def claim_next(self, worker_id: str) -> WorkflowJob | None:
        now = datetime.now(timezone.utc)
        statement = (
            select(WorkflowJob)
            .where(
                WorkflowJob.status == WorkflowJobStatus.PENDING,
                WorkflowJob.available_at <= now,
                WorkflowJob.attempts < WorkflowJob.max_attempts,
            )
            .order_by(WorkflowJob.available_at, WorkflowJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = self.session.scalar(statement)
        if job is None:
            return None
        job.status = WorkflowJobStatus.PROCESSING
        job.attempts += 1
        job.locked_at = now
        job.locked_by = worker_id
        job.progress_stage = "STARTING"
        job.progress_percent = max(job.progress_percent, 5)
        self.session.commit()
        self.session.refresh(job)
        return job

    def refresh_lease(self, job_id: int, worker_id: str) -> bool:
        result = self.session.execute(
            update(WorkflowJob)
            .where(
                WorkflowJob.id == job_id,
                WorkflowJob.status == WorkflowJobStatus.PROCESSING,
                WorkflowJob.locked_by == worker_id,
            )
            .values(locked_at=datetime.now(timezone.utc))
        )
        self.session.commit()
        return bool(result.rowcount)

    def mark_progress(self, job: WorkflowJob, stage: str, percent: int) -> None:
        job.progress_stage = stage
        job.progress_percent = max(0, min(100, percent))
        self.session.commit()

    def complete(self, job: WorkflowJob) -> None:
        job.status = WorkflowJobStatus.COMPLETED
        job.progress_stage = "COMPLETED"
        job.progress_percent = 100
        job.completed_at = datetime.now(timezone.utc)
        job.locked_at = None
        job.locked_by = None
        job.failure_reason = None
        self.session.commit()

    def retry_or_fail(self, job: WorkflowJob, reason: str) -> bool:
        job.failure_reason = reason[:2000]
        job.locked_at = None
        job.locked_by = None
        if job.attempts < job.max_attempts:
            job.status = WorkflowJobStatus.PENDING
            job.progress_stage = "RETRY_SCHEDULED"
            job.available_at = datetime.now(timezone.utc) + timedelta(
                seconds=min(60, 2 ** job.attempts)
            )
        else:
            job.status = WorkflowJobStatus.FAILED
            job.progress_stage = "FAILED"
            job.completed_at = datetime.now(timezone.utc)
        self.session.commit()
        return job.status is WorkflowJobStatus.FAILED

    def find(self, job_id: int) -> WorkflowJob | None:
        return self.session.get(WorkflowJob, job_id)

    def latest_for_run(
        self, run_id: int, job_type: WorkflowJobType
    ) -> WorkflowJob | None:
        return self.session.scalar(
            select(WorkflowJob)
            .where(
                WorkflowJob.analysis_run_id == run_id,
                WorkflowJob.job_type == job_type,
            )
            .order_by(WorkflowJob.id.desc())
        )
