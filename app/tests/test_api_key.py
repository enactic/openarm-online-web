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

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app import crud, job_queue
from app.deps import find_current_api_key
from app.models import ApiKey, ClaimedExecution, ReadyExecution, Submission
from app.security import get_hex_digest
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


def test_create_api_key_by_non_admin(client: TestClient):
    assert client.post("/api-keys/", data={"name": "runner-1"}).status_code == 403


def test_create_api_key(admin, session: Session, client: TestClient):
    response = client.post("/api-keys/", data={"name": "runner-1"})
    assert response.status_code == 200
    key = re.search(r"openarm-online-key-[\w-]+", response.text).group(0)
    created = session.exec(select(ApiKey).where(ApiKey.name == "runner-1")).first()
    assert created.hashed_key == get_hex_digest(key)


def test_create_api_key_with_empty_name(admin, client: TestClient):
    assert client.post("/api-keys/", data={"name": ""}).status_code == 422


def test_create_api_key_with_too_long_name(admin, client: TestClient):
    assert client.post("/api-keys/", data={"name": "x" * 256}).status_code == 422


def test_create_api_key_with_duplicated_name(
    admin, session: Session, api_key: ApiKey, client: TestClient
):
    response = client.post("/api-keys/", data={"name": api_key.name})
    assert response.status_code == 422
    assert "already exists" in response.text
    assert (
        len(session.exec(select(ApiKey).where(ApiKey.name == api_key.name)).all()) == 1
    )


def test_create_api_key_with_duplicated_name_in_db(session: Session, api_key: ApiKey):
    with pytest.raises(IntegrityError):
        crud.create_api_key(session=session, name=api_key.name)
    session.rollback()


def test_delete_api_key_by_non_admin(api_key: ApiKey, client: TestClient):
    assert client.post(f"/api-keys/{api_key.id}/delete").status_code == 403


def test_delete_api_key_not_found(admin, client: TestClient):
    assert client.post("/api-keys/9999/delete").status_code == 404


def test_delete_api_key(admin, session: Session, api_key: ApiKey, client: TestClient):
    response = client.post(f"/api-keys/{api_key.id}/delete")
    assert response.status_code == 303
    assert session.exec(select(ApiKey).where(ApiKey.id == api_key.id)).first() is None


def test_delete_api_key_with_running_job(
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

    assert client.post(f"/api-keys/{api_key.id}/delete").status_code == 303
    assert session.exec(select(ApiKey).where(ApiKey.id == api_key.id)).first() is None
    assert (
        session.exec(
            select(ClaimedExecution).where(ClaimedExecution.job_id == job.id)
        ).first()
        is None
    )
    assert session.exec(
        select(ReadyExecution).where(ReadyExecution.job_id == job.id)
    ).first().model_dump(exclude={"id", "created_at"}) == {"job_id": job.id}


def test_deleted_api_key_is_rejected(session: Session):
    api_key, key = crud.create_api_key(session=session, name="deleted")
    session.commit()
    assert find_current_api_key(session=session, key=key).id == api_key.id

    crud.delete_api_key(session=session, api_key=api_key)
    session.commit()
    with pytest.raises(HTTPException) as exc_info:
        find_current_api_key(session=session, key=key)
    assert exc_info.value.status_code == 401


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
