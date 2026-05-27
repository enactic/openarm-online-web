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

from app.models import ApiKey, ClaimedExecution, Job, Submission, Task


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
