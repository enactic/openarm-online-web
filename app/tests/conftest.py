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

from app import crud
from app.models import Task

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
        session.exec(delete(Task))
        session.commit()


@pytest.fixture(name="tasks")
def fixture_tasks(session: Session) -> list[Task]:
    data = json.loads((FIXTURES_DIR / "task.json").read_text())
    crud.create_tasks(session=session, data=data)
    return crud.get_tasks(session=session)
