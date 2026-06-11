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

from app.models import Job, ReadyExecution, Submission, Task, User
from app.settings import settings


def test_create_submission_enqueues_jobs(
    session: Session,
    tasks: list[Task],
    user: User,
    client: TestClient,
):
    assert (
        client.post(
            "/submissions/",
            data={"task_id": tasks[0].id, "docker_tag": "test/image:latest"},
        ).status_code
        == 303
    )

    submission = session.exec(
        select(Submission).where(Submission.docker_tag == "test/image:latest")
    ).first()
    assert submission.model_dump(exclude={"id", "created_at"}) == {
        "user_id": user.id,
        "task_id": tasks[0].id,
        "docker_tag": "test/image:latest",
    }

    jobs = session.exec(select(Job).where(Job.submission_id == submission.id)).all()
    assert len(jobs) == settings.JOBS_PER_SUBMISSION
    for job in jobs:
        assert job.model_dump(exclude={"id", "created_at"}) == {
            "submission_id": submission.id
        }
        assert session.exec(
            select(ReadyExecution).where(ReadyExecution.job_id == job.id)
        ).first().model_dump(exclude={"id", "created_at"}) == {"job_id": job.id}
