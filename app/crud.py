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

from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate as alchemy_paginate
from fastapi_pagination.ext.sqlmodel import paginate as model_paginate

from sqlalchemy import Select
from sqlalchemy.engine.row import Row
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, func, case, cast, Float

from app.models import (
    ApiKey,
    Submission,
    Rollout,
    RolloutCreate,
    Task,
    User,
    UserGitHub,
)
from app.job_queue import enqueue
from app.security import generate_api_key, get_hex_digest


def create_api_key(*, session: Session, name: str) -> str:
    key = generate_api_key()
    api_key = ApiKey(hashed_key=get_hex_digest(key), name=name)
    session.add(api_key)
    session.commit()
    return key


def find_api_key_by_hash(*, session: Session, hashed_key: str) -> ApiKey | None:
    return session.exec(select(ApiKey).where(ApiKey.hashed_key == hashed_key)).first()


def find_user(*, session, id: int) -> User | None:
    return session.get(User, id)


def find_user_by_github_id(*, session: Session, github_id: int) -> User | None:
    return session.exec(
        select(User).join(UserGitHub).where(UserGitHub.github_id == github_id)
    ).first()


def create_user(
    *,
    session: Session,
    github_id: int,
    login_name: str | None = None,
    name: str | None = None,
) -> User:
    user_github = UserGitHub(
        github_id=github_id,
        login_name=login_name,
        name=name,
    )
    user = User(github=user_github)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_github(
    *,
    session: Session,
    user: User,
    login_name: str | None = None,
    name: str | None = None,
) -> User:
    user.github.login_name = login_name
    user.github.name = name
    session.add(user)
    session.commit()


def create_tasks(*, session: Session, data: List[dict]):
    tasks = [Task.model_validate(d) for d in data]
    session.add_all(tasks)
    session.commit()


def find_task(*, session, id: int) -> Task | None:
    return session.get(Task, id)


def get_tasks(*, session: Session) -> list[Task]:
    return session.exec(select(Task)).all()


def get_paginated_tasks(*, session: Session, params: Params) -> Page[Task]:
    return model_paginate(session, select(Task).order_by(Task.id), params)


def _create_submission_no_commit(
    *,
    session: Session,
    user: User,
    task_id: int,
    docker_tag: str,
) -> Submission:
    submission = Submission(
        user=user,
        task_id=task_id,
        docker_tag=docker_tag,
    )
    session.add(submission)
    session.flush()
    return submission


def create_submission(
    *,
    session: Session,
    user: User,
    task_id: int,
    docker_tag: str,
) -> Submission:
    submission = _create_submission_no_commit(
        session=session,
        user=user,
        task_id=task_id,
        docker_tag=docker_tag,
    )
    session.commit()
    session.refresh(submission)
    return submission


def create_submission_with_enqueue(
    *,
    session: Session,
    user: User,
    task_id: int,
    docker_tag: str,
) -> Submission:
    # Create a submission and enqueue a job in a single transaction.
    submission = _create_submission_no_commit(
        session=session, user=user, task_id=task_id, docker_tag=docker_tag
    )
    # It is committed within `enqueue()`.
    enqueue(session=session, submission_id=submission.id)
    session.refresh(submission)
    return submission


def find_submission(*, session, id: int) -> Submission | None:
    statement = (
        select(Submission)
        .where(Submission.id == id)
        .options(selectinload(Submission.task))
    )
    return session.exec(statement).first()


def get_submissions(*, session: Session) -> list[Submission]:
    return session.exec(select(Submission)).all()


def get_paginated_submissions(
    *, session: Session, params: Params, filter: dict
) -> Page[Submission]:
    statement = select(Submission).order_by(Submission.id)
    if filter.get("task_id") is not None:
        statement = statement.where(Submission.task_id == filter["task_id"])
    if filter.get("user_id") is not None:
        statement = statement.where(Submission.user_id == filter["user_id"])
    return model_paginate(session, statement, params)


def _get_submissions_with_statistics_statement() -> Select[Row]:
    success_func_avg = func.avg(case((Rollout.success == True, 1), else_=0))
    return (
        select(
            Submission.id,
            Submission.user_id,
            Task.name.label("task_name"),
            Submission.docker_tag,
            Submission.created_at,
            func.count(Rollout.id).label("count"),
            cast(success_func_avg, Float).label("success_rate"),
        )
        .join(Task, Submission.task_id == Task.id)
        .outerjoin(Rollout, Rollout.submission_id == Submission.id)
        .group_by(Submission.id, Task.name)
        .order_by(Submission.id)
    )


def get_paginated_submissions_with_statistics_by_user_id(
    *, session: Session, params: Params, user_id: int
) -> Page[Row]:
    statement = _get_submissions_with_statistics_statement()
    return alchemy_paginate(
        session, statement.where(Submission.user_id == user_id), params
    )


def get_paginated_submissions_with_statistics_by_task_id(
    *, session: Session, params: Params, task_id: int
) -> Page[Row]:
    statement = _get_submissions_with_statistics_statement()
    return alchemy_paginate(
        session, statement.where(Submission.task_id == task_id), params
    )


def get_submission_with_statistics_by_id(*, session: Session, id: int) -> Row:
    statement = _get_submissions_with_statistics_statement()
    return session.exec(statement.where(Submission.id == id)).first()


def create_rollout(*, session: Session, rollout_create: RolloutCreate):
    rollout = Rollout.model_validate(rollout_create)
    session.add(rollout)
    session.commit()
    session.refresh(rollout)
    return rollout


def get_paginated_rollouts(
    *, session: Session, params: Params, filter: dict
) -> Page[Rollout]:
    statement = select(Rollout).order_by(Rollout.id)
    if "submission_id" in filter:
        statement = statement.where(Rollout.submission_id == filter["submission_id"])
    return model_paginate(session, statement, params)
