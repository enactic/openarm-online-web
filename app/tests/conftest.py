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

import json
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, delete

os.environ.setdefault("GITHUB_CLIENT_ID", "test-github-client-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-github-client-secret")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("HMAC_KEY", "test-hmac-key")
os.environ.setdefault("POSTGRES_DB", "openarm_online_test")
os.environ.setdefault("S3_ENDPOINT_URL", "http://s3:9000")
os.environ.setdefault("S3_BUCKET_NAME", "openarm-online-test")
os.environ.setdefault("S3_ACCESS_KEY_ID", "openarm-online-access")
os.environ.setdefault("S3_SECRET_ACCESS_KEY", "openarm-online-secret")


from fastapi.testclient import TestClient

from app.main import app
from app import crud
from app.db import engine
from app.deps import SessionDep, find_current_api_key, find_current_user_optional
from app.models import (
    ApiKey,
    ClaimedExecution,
    FailedExecution,
    GitHubOrganization,
    GitHubOrganizationMembership,
    Job,
    JobFailure,
    ReadyExecution,
    Rollout,
    Submission,
    Task,
    User,
    UserGitHub,
)
from app.s3 import _client
from app.settings import settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> Generator[None, None, None]:
    assert settings.POSTGRES_DB.endswith("_test")
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def create_bucket():
    client = _client()
    client.create_bucket(Bucket=settings.S3_BUCKET_NAME)

    yield

    objects = client.list_objects_v2(Bucket=settings.S3_BUCKET_NAME).get("Contents", [])
    for obj in objects:
        client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=obj["Key"])
    client.delete_bucket(Bucket=settings.S3_BUCKET_NAME)


@pytest.fixture(name="session")
def fixture_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.rollback()
        session.exec(delete(Rollout))
        session.exec(delete(JobFailure))
        session.exec(delete(FailedExecution))
        session.exec(delete(ClaimedExecution))
        session.exec(delete(ReadyExecution))
        session.exec(delete(Job))
        session.exec(delete(Submission))
        session.exec(delete(GitHubOrganizationMembership))
        session.exec(delete(GitHubOrganization))
        session.exec(delete(UserGitHub))
        session.exec(delete(User))
        session.exec(delete(ApiKey))
        session.exec(delete(Task))
        session.commit()


@pytest.fixture(name="client")
def fixture_client(session: Session, user: User, api_key: ApiKey):
    def override_find_current_user_optional(db_session: SessionDep):
        return db_session.get(User, user.id)

    def override_find_current_api_key(db_session: SessionDep):
        return db_session.get(ApiKey, api_key.id)

    app.dependency_overrides[find_current_user_optional] = (
        override_find_current_user_optional
    )
    app.dependency_overrides[find_current_api_key] = override_find_current_api_key
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture(name="tasks")
def fixture_tasks(session: Session) -> list[Task]:
    data = json.loads((FIXTURES_DIR / "task.json").read_text())
    crud.create_tasks(session=session, data=data)
    session.commit()
    return crud.get_tasks(session=session)


@pytest.fixture(name="api_key")
def fixture_api_key(session: Session) -> ApiKey:
    api_key = ApiKey(hashed_key="test_key", name="test")
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return api_key


@pytest.fixture(name="user")
def fixture_user(session: Session) -> User:
    user = crud.create_user(
        session=session,
        github_id=1,
        login_name="testuser",
        organizations=[{"github_id": 10, "login": "testorg"}],
    )
    session.commit()
    return user


@pytest.fixture(name="submission")
def fixture_submission(session: Session, user: User, tasks: list[Task]) -> Submission:
    submission = crud.create_submission(
        session=session, user=user, task_id=tasks[0].id, docker_tag="test/image:latest"
    )
    session.commit()
    return submission
