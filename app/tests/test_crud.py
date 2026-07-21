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

from fastapi_pagination import Params
from sqlmodel import Session

from app import crud
from app.models import RolloutCreate, Task


def test_find_task(session: Session, tasks: list[Task]):
    assert crud.find_task(session=session, id=tasks[0].id) == tasks[0]


def test_find_task_not_found(session: Session):
    assert crud.find_task(session=session, id=9999) is None


def _add_rollouts(
    session: Session, submission_id: int, n_successes: int, n_failures: int
):
    for _ in range(n_successes):
        crud.create_rollout(
            session=session,
            rollout_create=RolloutCreate(
                submission_id=submission_id, success=True, s3_key="rrd/x.rrd"
            ),
        )
    for _ in range(n_failures):
        crud.create_rollout(
            session=session,
            rollout_create=RolloutCreate(
                submission_id=submission_id, success=False, s3_key="rrd/x.rrd"
            ),
        )


def test_top_submissions_order_by_success_rate(
    session: Session, user: User, tasks: list[Task]
):
    task = tasks[0]
    # success_rate: 100%
    high = crud.create_submission(
        session=session, user=user, task_id=task.id, docker_tag="high"
    )
    _add_rollouts(session, high.id, n_successes=3, n_failures=0)

    # success_rate: 33%
    low = crud.create_submission(
        session=session, user=user, task_id=task.id, docker_tag="low"
    )
    _add_rollouts(session, low.id, n_successes=1, n_failures=2)

    # no rollouts
    crud.create_submission(
        session=session, user=user, task_id=task.id, docker_tag="none"
    )
    session.commit()

    page = crud.get_paginated_top_submissions_by_task_id(
        session=session, params=Params(page=1, size=20), task_id=task.id
    )
    assert page.items == [
        (high.id, user.id, "testuser", "high", 3, 1.0),
        (low.id, user.id, "testuser", "low", 3, pytest.approx(1 / 3)),
    ]


def test_top_submissions_filter_by_task(
    session: Session, user: User, tasks: list[Task]
):
    target = crud.create_submission(
        session=session, user=user, task_id=tasks[0].id, docker_tag="target"
    )
    _add_rollouts(session, target.id, n_successes=3, n_failures=0)

    other = crud.create_submission(
        session=session, user=user, task_id=tasks[1].id, docker_tag="other"
    )
    _add_rollouts(session, other.id, n_successes=3, n_failures=0)
    session.commit()

    page = crud.get_paginated_top_submissions_by_task_id(
        session=session, params=Params(page=1, size=20), task_id=tasks[0].id
    )
    assert page.items == [
        (target.id, user.id, "testuser", "target", 3, 1.0),
    ]


def test_create_user_with_organizations(session: Session):
    user = crud.create_user(
        session=session,
        github_id=100,
        login_name="dummy-login_name",
        name="dummy-name",
        organizations=[
            {"github_id": 10, "login": "org-a"},
            {"github_id": 20, "login": "org-b"},
        ],
    )
    session.commit()

    assert user.github.model_dump(
        exclude={"id", "user_id", "created_at", "updated_at"}
    ) == {
        "github_id": 100,
        "login_name": "dummy-login_name",
        "name": "dummy-name",
    }
    assert [
        org.model_dump(exclude={"id", "created_at"})
        for org in user.github.organizations
    ] == [
        {"github_id": 10, "login": "org-a"},
        {"github_id": 20, "login": "org-b"},
    ]


def test_create_user_no_organizations(session: Session):
    user = crud.create_user(
        session=session,
        github_id=100,
        login_name="dummy-login_name",
        name="dummy-name",
    )
    session.commit()

    assert user.github.model_dump(
        exclude={"id", "user_id", "created_at", "updated_at"}
    ) == {
        "github_id": 100,
        "login_name": "dummy-login_name",
        "name": "dummy-name",
    }
    assert user.github.organizations == []


def test_update_user_github_with_organizations(session: Session, user: User):
    crud.update_user_github(
        session=session,
        user=user,
        login_name="update-login_name",
        name="update-name",
        organizations=[{"github_id": 100, "login": "org-a"}],
    )
    session.commit()

    assert user.github.model_dump(
        exclude={"id", "user_id", "created_at", "updated_at"}
    ) == {
        "github_id": 1,
        "login_name": "update-login_name",
        "name": "update-name",
    }
    assert [
        org.model_dump(exclude={"id", "created_at"})
        for org in user.github.organizations
    ] == [
        {"github_id": 100, "login": "org-a"},
    ]


def test_update_user_github_no_organizations(session: Session, user: User):
    crud.update_user_github(
        session=session,
        user=user,
        login_name="update-login_name",
        name="update-name",
    )
    session.commit()

    assert user.github.model_dump(
        exclude={"id", "user_id", "created_at", "updated_at"}
    ) == {
        "github_id": 1,
        "login_name": "update-login_name",
        "name": "update-name",
    }
    assert [
        org.model_dump(exclude={"id", "created_at"})
        for org in user.github.organizations
    ] == [
        {"github_id": 10, "login": "testorg"},
    ]
