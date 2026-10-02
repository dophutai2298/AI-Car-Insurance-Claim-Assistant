from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine

from app.core.config import Settings
from app.db import create_session_factory, run_database_migrations
from app.models import (
    AnalysisRunStatus,
    Claim,
    ClaimStatus,
    User,
    UserRole,
    WorkflowAnalysisRun,
    WorkflowJobStatus,
)
from app.repositories.workflow_jobs import WorkflowJobRepository
from app.services.workflow_worker import WorkflowWorker


def worker_fixture(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'worker.db').as_posix()}"
    run_database_migrations(database_url)
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    factory = create_session_factory(engine)
    settings = Settings(
        DATABASE_URL=database_url,
        JWT_SECRET="worker-test-secret-long-enough",
        WORKFLOW_JOB_LEASE_SECONDS=30,
    )
    with factory() as session:
        user = User(
            email="admin@example.com",
            full_name="Admin",
            password_hash="unused",
            role=UserRole.ADMIN,
        )
        session.add(user)
        session.flush()
        claim = Claim(
            claim_number="CLM-000001",
            claimant_name="Mai Nguyen",
            vehicle_make="Toyota",
            vehicle_model="Camry",
            vehicle_year=2022,
            status=ClaimStatus.ANALYZING,
            created_by_user_id=user.id,
        )
        session.add(claim)
        session.flush()
        run = WorkflowAnalysisRun(claim_id=claim.id, input_revision=1)
        session.add(run)
        session.commit()
        run_id = run.id
        claim_id = claim.id
    return engine, factory, settings, claim_id, run_id


def test_worker_persists_progress_and_does_not_redeliver_completed_job(tmp_path):
    engine, factory, settings, _claim_id, run_id = worker_fixture(tmp_path)
    calls: list[int] = []
    with factory() as session:
        run = session.get(WorkflowAnalysisRun, run_id)
        job = WorkflowJobRepository(session).enqueue_analysis(run, 3)
        job_id = job.id

    class Service:
        def __init__(self, session):
            self.session = session

        def process_workflow_analysis(self, current_run_id: int) -> None:
            calls.append(current_run_id)
            run = self.session.get(WorkflowAnalysisRun, current_run_id)
            run.status = AnalysisRunStatus.COMPLETED
            self.session.commit()

    worker = WorkflowWorker(factory, settings, lambda session, _settings: Service(session))

    assert worker.run_once() is True
    assert worker.run_once() is False
    with factory() as session:
        job = WorkflowJobRepository(session).find(job_id)
        assert job.status is WorkflowJobStatus.COMPLETED
        assert job.progress_percent == 100
        assert job.attempts == 1
    assert calls == [run_id]
    engine.dispose()


def test_worker_retries_failure_and_recovers_an_expired_lease(tmp_path):
    engine, factory, settings, _claim_id, run_id = worker_fixture(tmp_path)
    attempts = 0
    with factory() as session:
        run = session.get(WorkflowAnalysisRun, run_id)
        job = WorkflowJobRepository(session).enqueue_analysis(run, 3)
        job.status = WorkflowJobStatus.PROCESSING
        run.status = AnalysisRunStatus.PROCESSING
        job.locked_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        job.locked_by = "stopped-worker"
        session.commit()
        job_id = job.id

    class Service:
        def process_workflow_analysis(self, _run_id: int) -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("retryable provider failure")

    worker = WorkflowWorker(factory, settings, lambda _session, _settings: Service())
    assert worker.run_once() is True
    with factory() as session:
        job = WorkflowJobRepository(session).find(job_id)
        assert job.status is WorkflowJobStatus.PENDING
        assert job.attempts == 1
        job.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()

    assert worker.run_once() is True
    with factory() as session:
        job = WorkflowJobRepository(session).find(job_id)
        assert job.status is WorkflowJobStatus.COMPLETED
        assert job.attempts == 2
    engine.dispose()


def test_worker_marks_run_failed_when_final_attempt_lease_expires(tmp_path):
    engine, factory, settings, claim_id, run_id = worker_fixture(tmp_path)
    with factory() as session:
        run = session.get(WorkflowAnalysisRun, run_id)
        run.status = AnalysisRunStatus.PROCESSING
        job = WorkflowJobRepository(session).enqueue_analysis(run, 1)
        job.status = WorkflowJobStatus.PROCESSING
        job.attempts = 1
        job.locked_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        job.locked_by = "stopped-worker"
        session.commit()
        job_id = job.id

    worker = WorkflowWorker(factory, settings, lambda _session, _settings: None)

    assert worker.run_once() is True
    with factory() as session:
        job = WorkflowJobRepository(session).find(job_id)
        run = session.get(WorkflowAnalysisRun, run_id)
        claim = session.get(Claim, claim_id)
        assert job.status is WorkflowJobStatus.FAILED
        assert run.status is AnalysisRunStatus.FAILED
        assert claim.status is ClaimStatus.FAILED
    engine.dispose()
