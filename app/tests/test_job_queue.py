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

import pytest
import re

from sqlmodel import Session, select

from app import job_queue
from app.models import (
    ApiKey,
    ClaimedExecution,
    FailedExecution,
    Job,
    ReadyExecution,
    Submission,
)


def test_enqueue(session: Session, submission: Submission):
    job = job_queue.enqueue(session=session, submission_id=submission.id)

    assert (
        session.exec(select(Job).where(Job.submission_id == submission.id)).first()
        == job
    )
    assert session.exec(
        select(ReadyExecution).where(ReadyExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {"job_id": job.id}


def test_claim_next_job(session: Session, submission: Submission, api_key: ApiKey):
    job = job_queue.enqueue(session=session, submission_id=submission.id)

    assert (
        job_queue.claim_next_job(
            session=session, api_key_id=api_key.id, task_id=submission.task_id
        )
        == job
    )
    assert (
        session.exec(
            select(ReadyExecution).where(ReadyExecution.job_id == job.id)
        ).first()
        is None
    )
    assert session.exec(
        select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "job_id": job.id,
        "api_key_id": api_key.id,
    }


def test_claim_next_job_no_jobs(
    session: Session, submission: Submission, api_key: ApiKey
):
    assert (
        job_queue.claim_next_job(
            session=session, api_key_id=api_key.id, task_id=submission.task_id
        )
        is None
    )


def test_claim_next_job_different_task(
    session: Session, submission: Submission, api_key: ApiKey
):
    job_queue.enqueue(session=session, submission_id=submission.id)
    assert (
        job_queue.claim_next_job(session=session, api_key_id=api_key.id, task_id=9999)
        is None
    )


def test_complete_job(session: Session, submission: Submission, api_key: ApiKey):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )

    assert (
        job_queue.complete_job(session=session, job_id=job.id, api_key_id=api_key.id)
        is None
    )
    assert session.get(Job, job.id) is None
    assert (
        session.exec(
            select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
        ).first()
        is None
    )


def test_complete_job_not_found(session: Session, api_key: ApiKey):
    with pytest.raises(ValueError, match=re.escape("Job(9999) not found")):
        job_queue.complete_job(session=session, job_id=9999, api_key_id=api_key.id)


def test_complete_job_no_claimed_raise(
    session: Session, submission: Submission, api_key: ApiKey
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    with pytest.raises(
        ValueError, match=re.escape(f"Job({job.id}) has no claimed execution")
    ):
        job_queue.complete_job(session=session, job_id=job.id, api_key_id=api_key.id)


def test_complete_job_wrong_api_key(
    session: Session, submission: Submission, api_key: ApiKey
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )
    with pytest.raises(
        ValueError, match=re.escape(f"Job({job.id}) is claimed by another runner")
    ):
        job_queue.complete_job(session=session, job_id=job.id, api_key_id=9999)


def test_fail_job(session: Session, submission: Submission, api_key: ApiKey):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )

    assert (
        job_queue.fail_job(
            session=session, job_id=job.id, reason="timeout", api_key_id=api_key.id
        )
        == job
    )
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
        "reason": "timeout",
    }


def test_fail_job_not_found(session: Session, api_key: ApiKey):
    with pytest.raises(ValueError, match=re.escape("Job(9999) not found")):
        job_queue.fail_job(
            session=session, job_id=9999, reason="timeout", api_key_id=api_key.id
        )


def test_fail_job_no_claimed_raise(
    session: Session, submission: Submission, api_key: ApiKey
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    with pytest.raises(
        ValueError, match=re.escape(f"Job({job.id}) has no claimed execution")
    ):
        job_queue.fail_job(
            session=session, job_id=job.id, reason="timeout", api_key_id=api_key.id
        )


def test_fail_job_wrong_api_key(
    session: Session, submission: Submission, api_key: ApiKey
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )
    with pytest.raises(
        ValueError, match=re.escape(f"Job({job.id}) is claimed by another runner")
    ):
        job_queue.fail_job(
            session=session, job_id=job.id, reason="timeout", api_key_id=9999
        )


def test_retry_job(session: Session, submission: Submission, api_key: ApiKey):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )
    job_queue.fail_job(
        session=session, job_id=job.id, reason="timeout", api_key_id=api_key.id
    )

    assert job_queue.retry_job(session=session, job_id=job.id) == job
    assert (
        session.exec(
            select(FailedExecution).where(FailedExecution.job_id == job.id)
        ).first()
        is None
    )
    assert session.exec(
        select(ReadyExecution).where(ReadyExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {"job_id": job.id}


def test_retry_job_not_found(session: Session):
    with pytest.raises(ValueError, match=re.escape("Job(9999) not found")):
        job_queue.retry_job(session=session, job_id=9999)


def test_retry_job_no_failed_raise(session: Session, submission: Submission):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    with pytest.raises(
        ValueError, match=re.escape(f"Job({job.id}) has no failed execution")
    ):
        job_queue.retry_job(session=session, job_id=job.id)
