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

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud, job_queue
from app.models import ApiKey, FailedExecution, ReadyExecution, Submission, Task


def _fail_job(session: Session, submission: Submission, api_key: ApiKey):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )
    job_queue.fail_job(
        session=session, job_id=job.id, reason="dummy", api_key_id=api_key.id
    )
    session.commit()
    return job


def test_retry_job(
    session: Session,
    submission: Submission,
    api_key: ApiKey,
    client: TestClient,
):
    job = _fail_job(session, submission, api_key)

    assert client.post(f"/jobs/{job.id}/retry").status_code == 303
    assert (
        session.exec(
            select(FailedExecution).where(FailedExecution.job_id == job.id)
        ).first()
        is None
    )
    assert session.exec(
        select(ReadyExecution).where(ReadyExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {"job_id": job.id}


def test_retry_job_not_found(client: TestClient):
    assert client.post("/jobs/9999/retry").status_code == 404


def test_retry_job_by_non_owner(
    session: Session,
    tasks: list[Task],
    api_key: Apache,
    client: TestClient,
):
    other = crud.create_user(session=session, github_id=2, login_name="other")
    other_submission = crud.create_submission(
        session=session,
        user=other,
        task_id=tasks[0].id,
        docker_tag="other/image:latest",
    )
    session.commit()
    job = _fail_job(session, other_submission, api_key)

    assert client.post(f"/jobs/{job.id}/retry").status_code == 404
    assert session.exec(
        select(FailedExecution).where(FailedExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "job_id": job.id,
        "reason": "dummy",
    }


def test_retry_job_do_nothing(
    session: Session,
    submission: Submission,
    client: TestClient,
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    session.commit()
    assert client.post(f"/jobs/{job.id}/retry").status_code == 303
