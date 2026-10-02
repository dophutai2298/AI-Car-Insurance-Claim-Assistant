import logging
import os
import socket
from collections.abc import Callable
from threading import Event, Thread

from sqlalchemy.orm import Session, sessionmaker

from app.api.composition import build_claim_service
from app.core.config import Settings
from app.models import WorkflowJobStatus, WorkflowJobType
from app.repositories.claims import ClaimRepository
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.workflow_jobs import WorkflowJobRepository

logger = logging.getLogger(__name__)


class WorkflowWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
        service_builder: Callable = build_claim_service,
        worker_id: str | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.service_builder = service_builder
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}-worker"

    def run_once(self) -> bool:
        with self.session_factory() as session:
            jobs = WorkflowJobRepository(session)
            terminal_jobs = jobs.recover_stale(
                self.settings.workflow_job_lease_seconds
            )
            for stale in terminal_jobs:
                if stale.job_type is WorkflowJobType.ANALYSIS:
                    self._fail_analysis_run(
                        session,
                        stale.analysis_run_id,
                        stale.claim_id,
                        "Analysis worker lease expired after the final attempt",
                    )
            job = jobs.claim_next(self.worker_id)
            if job is None:
                return bool(terminal_jobs)
            job_id = job.id
            job_type = job.job_type
            run_id = job.analysis_run_id
            claim_id = job.claim_id
            jobs.mark_progress(
                job,
                "ANALYSIS" if job_type is WorkflowJobType.ANALYSIS else "AI_REVIEW",
                15,
            )
            heartbeat_stop = Event()
            heartbeat = Thread(
                target=self._heartbeat,
                args=(heartbeat_stop, job_id),
                daemon=True,
                name=f"workflow-job-{job_id}-heartbeat",
            )
            heartbeat.start()
            try:
                service = self.service_builder(session, self.settings)
                if job_type is WorkflowJobType.ANALYSIS:
                    service.process_workflow_analysis(run_id)
                else:
                    claim = ClaimRepository(session).find_by_id(claim_id)
                    if claim is None or claim.claim_number is None:
                        raise RuntimeError("Workflow job claim is unavailable")
                    service.run_workflow_ai_review(
                        claim.claim_number, run_id, source_job_id=job_id
                    )
                session.expire_all()
                current = jobs.find(job_id)
                if current is not None and current.status is WorkflowJobStatus.PROCESSING:
                    jobs.complete(current)
                return True
            except Exception as error:
                logger.exception("Workflow job %s failed", job_id)
                session.rollback()
                current = jobs.find(job_id)
                if current is not None:
                    terminal = jobs.retry_or_fail(
                        current, f"{type(error).__name__}: {error}"
                    )
                    if terminal and job_type is WorkflowJobType.ANALYSIS:
                        self._fail_analysis_run(
                            session,
                            run_id,
                            claim_id,
                            "Analysis worker exhausted its retries",
                        )
                return True
            finally:
                heartbeat_stop.set()
                heartbeat.join(timeout=1)

    def _heartbeat(self, stop: Event, job_id: int) -> None:
        interval = max(5.0, self.settings.workflow_job_lease_seconds / 3)
        while not stop.wait(interval):
            try:
                with self.session_factory() as session:
                    if not WorkflowJobRepository(session).refresh_lease(
                        job_id, self.worker_id
                    ):
                        return
            except Exception:
                logger.exception("Workflow job %s heartbeat failed", job_id)

    @staticmethod
    def _fail_analysis_run(
        session: Session,
        run_id: int,
        claim_id: int,
        reason: str,
    ) -> None:
        analysis_runs = AnalysisRunRepository(session)
        run = analysis_runs.find(run_id)
        claim = ClaimRepository(session).find_by_id(claim_id)
        if run is not None and claim is not None:
            analysis_runs.fail(run, claim, reason)
