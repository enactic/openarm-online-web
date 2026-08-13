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
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import job_queue
from app.models import ApiKey, Submission
from app.settings import AllowListSettings, settings


@pytest.fixture(name="admin")
def fixture_admin(monkeypatch):
    monkeypatch.setattr(
        settings, "admin", AllowListSettings(allowed_users={"testuser"})
    )


def test_list_api_keys_by_non_admin(client: TestClient):
    assert client.get("/api-keys/").status_code == 403


def test_list_api_keys(admin, api_key: ApiKey, client: TestClient):
    response = client.get("/api-keys/")
    assert response.status_code == 200
    assert f"/api-keys/{api_key.id}" in response.text


def test_api_key_by_non_admin(api_key: ApiKey, client: TestClient):
    assert client.get(f"/api-keys/{api_key.id}").status_code == 403


def test_api_key_not_found(admin, client: TestClient):
    assert client.get("/api-keys/9999").status_code == 404


def test_api_key(admin, api_key: ApiKey, client: TestClient):
    response = client.get(f"/api-keys/{api_key.id}")
    assert response.status_code == 200
    assert "No running jobs." in response.text


def test_api_key_with_running_job(
    admin,
    session: Session,
    submission: Submission,
    api_key: ApiKey,
    client: TestClient,
):
    job = job_queue.enqueue(session=session, submission_id=submission.id)
    job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=submission.task_id
    )
    session.commit()

    response = client.get(f"/api-keys/{api_key.id}")
    assert response.status_code == 200
    assert f"<td>{job.id}</td>" in response.text
    assert f"/submissions/{submission.id}" in response.text
