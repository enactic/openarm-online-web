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

from sqlmodel import Session, select

from app.models import (
    ClaimedExecution,
    FailedExecution,
    Job,
    ReadyExecution,
    Submission,
)


def enqueue(*, session: Session, submission_id: int) -> Job:
    job = Job(submission_id=submission_id)
    session.add(job)
    session.flush()
    session.add(ReadyExecution(job_id=job.id))
    session.flush()
    session.refresh(job)
    return job


def claim_next_job(*, session: Session, api_key_id: int, task_id: int) -> Job | None:
    statement = (
        select(ReadyExecution)
        .join(Job, ReadyExecution.job_id == Job.id)
        .join(Submission, Job.submission_id == Submission.id)
        .where(Submission.task_id == task_id)
        .order_by(ReadyExecution.id)
        .with_for_update(of=ReadyExecution, skip_locked=True)
        .limit(1)
    )
    ready = session.exec(statement).first()
    if ready is None:
        return None
    job = session.get(Job, ready.job_id)
    session.delete(ready)
    session.add(ClaimedExecution(job_id=job.id, api_key_id=api_key_id))
    session.flush()
    return job


def complete_job(*, session: Session, job_id: int, api_key_id: int) -> None:
    job = session.get(Job, job_id)
    if job is None:
        raise ValueError(f"Job({job_id}) not found")
    claimed = session.exec(
        select(ClaimedExecution).where(ClaimedExecution.job_id == job_id)
    ).first()
    if claimed is None:
        raise ValueError(f"Job({job.id}) has no claimed execution")
    if claimed.api_key_id != api_key_id:
        raise ValueError(f"Job({job.id}) is claimed by another runner")
    session.delete(claimed)
    session.delete(job)
    session.flush()


def fail_job(*, session: Session, job_id: int, reason: str, api_key_id: int) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise ValueError(f"Job({job_id}) not found")
    claimed = session.exec(
        select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
    ).first()
    if claimed is None:
        raise ValueError(f"Job({job.id}) has no claimed execution")
    if claimed.api_key_id != api_key_id:
        raise ValueError(f"Job({job.id}) is claimed by another runner")
    session.delete(claimed)
    session.add(FailedExecution(job_id=job_id, reason=reason))
    session.flush()
    return job


def retry_job(*, session: Session, job_id: int) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise ValueError(f"Job({job_id}) not found")
    failed = session.exec(
        select(FailedExecution).where(FailedExecution.job_id == job.id)
    ).first()
    if failed is None:
        raise ValueError(f"Job({job.id}) has no failed execution")
    session.delete(failed)
    session.add(ReadyExecution(job_id=job.id))
    session.flush()
    return job
