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

import re
import requests

from collections.abc import Generator
from contextlib import contextmanager
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.main import app
from app.deps import SessionDep, find_current_api_key
from app.models import (
    ApiKey,
    ClaimedExecution,
    FailedExecution,
    Job,
    JobFailure,
    Rollout,
    Submission,
    Task,
)
from app.settings import settings
from app.s3 import _client as s3client


@contextmanager
def _other_client(session: Session) -> Generator[TestClient, None, None]:
    other_api_key = ApiKey(hashed_key="other_key", name="other")
    session.add(other_api_key)
    session.commit()
    session.refresh(other_api_key)

    def _find_other_api_key(db_session: SessionDep) -> ApiKey | None:
        return db_session.get(ApiKey, other_api_key.id)

    previous_override = app.dependency_overrides.get(find_current_api_key)
    app.dependency_overrides[find_current_api_key] = _find_other_api_key
    try:
        with TestClient(app, follow_redirects=False) as other_client:
            yield other_client
    finally:
        if previous_override is not None:
            app.dependency_overrides[find_current_api_key] = previous_override
        else:
            app.dependency_overrides.pop(find_current_api_key, None)


def test_claim_job(
    session: Session, tasks: list[Task], api_key: ApiKey, client: TestClient
):
    client.post(
        "/submissions/",
        data={"task_id": tasks[0].id, "docker_tag": "test/image:latest"},
    )

    response = client.post(f"/api/v1/tasks/{tasks[0].id}/jobs/claim")
    assert response.status_code == 200

    submission = session.exec(
        select(Submission).where(Submission.docker_tag == "test/image:latest")
    ).first()
    job = session.exec(select(Job).where(Job.submission_id == submission.id)).first()
    assert response.json() == {
        "job_id": job.id,
        "docker_tag": "test/image:latest",
        "reset_docker_tag": tasks[0].reset_docker_tag,
        "prompt": tasks[0].prompt,
        "runtime": "OpenArm Cell",
    }

    assert session.exec(
        select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "job_id": job.id,
        "api_key_id": api_key.id,
    }


def test_claim_job_different_task(
    session: Session, tasks: list[Task], client: TestClient
):
    client.post(
        "/submissions/",
        data={"task_id": tasks[0].id, "docker_tag": "test/image:latest"},
    )

    response = client.post("/api/v1/tasks/9999/jobs/claim")
    assert response.status_code == 200
    assert response.json() is None


def test_claim_job_no_jobs(session: Session, client: TestClient):
    response = client.post("/api/v1/tasks/1/jobs/claim")

    assert response.status_code == 200
    assert response.json() is None


def _setup_claimed_job(tasks: list[Task], client: TestClient) -> int:
    client.post(
        "/submissions/",
        data={"task_id": tasks[0].id, "docker_tag": "test/image:latest"},
    )
    claim_response = client.post(f"/api/v1/tasks/{tasks[0].id}/jobs/claim")
    assert claim_response.status_code == 200
    claim_response_json = claim_response.json()
    assert claim_response_json is not None
    return claim_response_json["job_id"]


def test_complete_job_success(session: Session, tasks: list[Task], client: TestClient):
    job_id = _setup_claimed_job(tasks, client)

    response = client.post(
        f"/api/v1/jobs/{job_id}/complete",
        json={"success": True, "s3_key": "rrd/dummy.rrd"},
    )
    assert response.status_code == 200
    submission = session.exec(
        select(Submission).where(Submission.docker_tag == "test/image:latest")
    ).first()
    assert response.json()["submission_id"] == submission.id
    assert response.json()["success"] is True

    assert session.get(Job, job_id) is None
    assert (
        session.exec(
            select(ClaimedExecution).where(ClaimedExecution.job_id == job_id)
        ).first()
        is None
    )

    assert session.exec(
        select(Rollout).where(Rollout.submission_id == submission.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "submission_id": submission.id,
        "success": True,
        "s3_key": "rrd/dummy.rrd",
    }


def test_complete_job_fail(session: Session, tasks: list[Task], client: TestClient):
    job_id = _setup_claimed_job(tasks, client)

    response = client.post(
        f"/api/v1/jobs/{job_id}/complete",
        json={"success": False, "s3_key": "rrd/dummy.rrd"},
    )
    assert response.status_code == 200
    submission = session.exec(
        select(Submission).where(Submission.docker_tag == "test/image:latest")
    ).first()
    assert response.json()["submission_id"] == submission.id
    assert response.json()["success"] is False

    assert session.get(Job, job_id) is None
    assert (
        session.exec(
            select(ClaimedExecution).where(ClaimedExecution.job_id == job_id)
        ).first()
        is None
    )

    assert session.exec(
        select(Rollout).where(Rollout.submission_id == submission.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "submission_id": submission.id,
        "success": False,
        "s3_key": "rrd/dummy.rrd",
    }


def test_complete_job_not_found(session: Session, client: TestClient):
    response = client.post(
        f"/api/v1/jobs/9999/complete", json={"success": True, "s3_key": "rrd/dummy.rrd"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Job(9999) not found"}


def test_complete_job_no_claimed(
    session: Session, tasks: list[Task], client: TestClient
):
    client.post(
        "/submissions/",
        data={"task_id": tasks[0].id, "docker_tag": "test/image:latest"},
    )
    job = session.exec(select(Job)).first()
    response = client.post(
        f"/api/v1/jobs/{job.id}/complete",
        json={"success": True, "s3_key": "rrd/dummy.rrd"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": f"Job({job.id}) has no claimed execution"}


def test_complete_job_wrong_api_key(
    session: Session, tasks: list[Task], client: TestClient
):
    job_id = _setup_claimed_job(tasks, client)
    with _other_client(session) as other:
        response = other.post(
            f"/api/v1/jobs/{job_id}/complete",
            json={"success": True, "s3_key": "rrd/dummy.rrd"},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": f"Job({job_id}) is claimed by another runner"}


def test_fail_job(session: Session, tasks: list[Task], client: TestClient):
    job_id = _setup_claimed_job(tasks, client)

    response = client.post(f"/api/v1/jobs/{job_id}/fail", json={"reason": "timeout"})
    assert response.status_code == 200

    submission = session.exec(
        select(Submission).where(Submission.docker_tag == "test/image:latest")
    ).first()
    assert response.json()["submission_id"] == submission.id
    assert response.json()["reason"] == "timeout"

    assert session.get(Job, job_id) is not None
    assert (
        session.exec(
            select(ClaimedExecution).where(ClaimedExecution.job_id == job_id)
        ).first()
        is None
    )
    assert session.exec(
        select(FailedExecution).where(FailedExecution.job_id == job_id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "job_id": job_id,
        "reason": "timeout",
    }

    assert session.exec(
        select(JobFailure).where(JobFailure.submission_id == submission.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {
        "submission_id": submission.id,
        "reason": "timeout",
    }


def test_fail_job_not_found(session: Session, client: TestClient):
    response = client.post("/api/v1/jobs/9999/fail", json={"reason": "timeout"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Job(9999) not found"}


def test_fail_job_no_claimed_execution(
    session: Session, tasks: list[Task], client: TestClient
):
    client.post(
        "/submissions/",
        data={"task_id": tasks[0].id, "docker_tag": "test/image:latest"},
    )
    job = session.exec(select(Job)).first()
    response = client.post(f"/api/v1/jobs/{job.id}/fail", json={"reason": "timeout"})
    assert response.status_code == 400
    assert response.json() == {"detail": f"Job({job.id}) has no claimed execution"}


def test_fail_job_wrong_api_key(
    session: Session, tasks: list[Task], client: TestClient
):
    job_id = _setup_claimed_job(tasks, client)
    with _other_client(session) as other:
        response = other.post(f"/api/v1/jobs/{job_id}/fail", json={"reason": "timeout"})

    assert response.status_code == 400
    assert response.json() == {"detail": f"Job({job_id}) is claimed by another runner"}


def test_get_upload_url(client: TestClient, create_bucket):
    response = client.get(f"/api/v1/rrd/upload-url")
    assert response.status_code == 200

    s3_key = response.json()["s3_key"]
    assert re.fullmatch(r"rrd/[0-9a-f-]{36}\.rrd", s3_key)

    s3_response = requests.put(response.json()["url"], data=b"test content", timeout=5)
    assert s3_response.status_code == 200
    assert (
        s3client().get_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)["Body"].read()
        == b"test content"
    )
