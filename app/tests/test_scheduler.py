# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app import job_queue
from app.models import (
    ApiKey,
    ClaimedExecution,
    FailedExecution,
    Job,
    JobFailure,
    Submission,
)
from app.scheduler import timeout_claimed_jobs
from app.settings import settings


def test_timeout_claimed_jobs(
    session: Session, submission: Submission, api_key: ApiKey
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )
    claimed = session.exec(
        select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
    ).first()
    claimed.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session.add(claimed)
    session.commit()

    timeout_claimed_jobs()
    session.expire_all()

    assert session.get(Job, job.id).model_dump(exclude={"id", "created_at"}) == {
        "submission_id": job.submission_id
    }
    assert (
        session.exec(
            select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
        ).first()
        is None
    )
    assert session.exec(
        select(FailedExecution).where(FailedExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "job_id": job.id,
        "reason": f"[server] Job timed out after {settings.CLAIM_TIMEOUT} minutes",
    }
    assert session.exec(
        select(JobFailure).where(JobFailure.submission_id == submission.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "submission_id": job.submission_id,
        "reason": f"[server] Job timed out after {settings.CLAIM_TIMEOUT} minutes",
    }


def test_timeout_claimed_jobs_no_expired(
    session: Session, submission: Submission, api_key: ApiKey
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )
    session.commit()

    timeout_claimed_jobs()
    session.expire_all()

    assert session.get(Job, job.id).model_dump(exclude={"id", "created_at"}) == {
        "submission_id": job.submission_id
    }
    assert session.exec(
        select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "job_id": job.id,
        "api_key_id": api_key.id,
    }
    assert (
        session.exec(
            select(FailedExecution).where(FailedExecution.job_id == job.id)
        ).first()
        is None
    )
