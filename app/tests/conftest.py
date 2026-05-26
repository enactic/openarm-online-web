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
from sqlmodel import Session, SQLModel, create_engine, delete

os.environ.setdefault("GITHUB_CLIENT_ID", "test-github-client-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-github-client-secret")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("HMAC_KEY", "test-hmac-key")

from fastapi.testclient import TestClient

from app.main import app
from app import crud
from app.deps import find_current_user_optional, get_db
from app.models import (
    ApiKey,
    ClaimedExecution,
    FailedExecution,
    Job,
    ReadyExecution,
    Rollout,
    Submission,
    Task,
    User,
    UserGitHub,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://openeval:openeval@localhost:5432/openeval_test",
)

test_engine = create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> Generator[None, None, None]:
    SQLModel.metadata.create_all(test_engine)
    yield


@pytest.fixture(name="session")
def fixture_session() -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session
        session.rollback()
        session.exec(delete(Rollout))
        session.exec(delete(FailedExecution))
        session.exec(delete(ClaimedExecution))
        session.exec(delete(ReadyExecution))
        session.exec(delete(Job))
        session.exec(delete(Submission))
        session.exec(delete(UserGitHub))
        session.exec(delete(User))
        session.exec(delete(ApiKey))
        session.exec(delete(Task))
        session.commit()


@pytest.fixture(name="client")
def fixture_client(session: Session, user: User):
    def override_get_db():
        return session

    def override_find_current_user_optional():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[find_current_user_optional] = (
        override_find_current_user_optional
    )
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture(name="tasks")
def fixture_tasks(session: Session) -> list[Task]:
    data = json.loads((FIXTURES_DIR / "task.json").read_text())
    crud.create_tasks(session=session, data=data)
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
    return crud.create_user(session=session, github_id=1, login_name="testuser")


@pytest.fixture(name="submission")
def fixture_submission(session: Session, user: User, tasks: list[Task]) -> Submission:
    return crud.create_submission(
        session=session, user=user, task_id=tasks[0].id, docker_tag="test/image:latest"
    )
