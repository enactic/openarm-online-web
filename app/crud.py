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

from sqlalchemy import Select, update
from sqlalchemy.engine.row import Row
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, func, case, cast, Float

from app.models import (
    ApiKey,
    GitHubOrganization,
    JobFailure,
    Rollout,
    RolloutCreate,
    Submission,
    Task,
    User,
    UserGitHub,
)
from app.security import generate_api_key, get_hex_digest


def create_api_key(*, session: Session, name: str) -> str:
    key = generate_api_key()
    api_key = ApiKey(hashed_key=get_hex_digest(key), name=name)
    session.add(api_key)
    session.flush()
    return key


def find_api_key_by_hash(*, session: Session, hashed_key: str) -> ApiKey | None:
    return session.exec(select(ApiKey).where(ApiKey.hashed_key == hashed_key)).first()


def find_user(*, session, id: int) -> User | None:
    return session.get(User, id)


def find_user_by_github_id(*, session: Session, github_id: int) -> User | None:
    return session.exec(
        select(User).join(UserGitHub).where(UserGitHub.github_id == github_id)
    ).first()


def _upsert_organizations(
    *, session: Session, organizations: list[dict] | None
) -> list[GitHubOrganization]:
    if not organizations:
        return []

    organizations_by_github_id = {org["github_id"]: org for org in organizations}
    existing = {
        org.github_id: org
        for org in session.exec(
            select(GitHubOrganization).where(
                GitHubOrganization.github_id.in_(organizations_by_github_id.keys())
            )
        ).all()
    }
    github_organizations = []
    new_organizations = []
    for id, org in organizations_by_github_id.items():
        organization = existing.get(id)
        if organization is None:
            organization = GitHubOrganization(github_id=id, login=org["login"])
            new_organizations.append(organization)
        else:
            # It is updated at commit.
            organization.login = org["login"]
        github_organizations.append(organization)
    session.add_all(new_organizations)
    return github_organizations


def create_user(
    *,
    session: Session,
    github_id: int,
    login_name: str | None = None,
    name: str | None = None,
    organizations: list[dict] | None = None,
) -> User:
    user_github = UserGitHub(
        github_id=github_id,
        login_name=login_name,
        name=name,
    )
    user_github.organizations = _upsert_organizations(
        session=session, organizations=organizations
    )
    user = User(github=user_github)
    session.add(user)
    session.flush()
    return user


def update_user_github(
    *,
    session: Session,
    user: User,
    login_name: str | None = None,
    name: str | None = None,
    organizations: list[dict] | None = None,
):
    user.github.login_name = login_name
    user.github.name = name
    if organizations is not None:
        user.github.organizations = _upsert_organizations(
            session=session, organizations=organizations
        )
    session.add(user)
    session.flush()


def create_tasks(*, session: Session, data: list[dict]):
    tasks = [Task.model_validate(d) for d in data]
    session.add_all(tasks)
    session.flush()


def update_tasks(*, session: Session, data: list[dict]):
    for v in data:
        Task.model_validate(v)
    session.execute(update(Task), data)
    session.flush()


def find_task(*, session, id: int) -> Task | None:
    return session.get(Task, id)


def get_tasks(*, session: Session) -> list[Task]:
    return session.exec(select(Task)).all()


def get_paginated_tasks(*, session: Session, params: Params) -> Page[Task]:
    return model_paginate(session, select(Task).order_by(Task.id), params)


def create_submission(
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


def get_paginated_top_submissions_by_task_id(
    *, session: Session, params: Params, task_id: int
) -> Page[Row]:
    success_rate = cast(
        func.avg(case((Rollout.success == True, 1), else_=0)), Float
    ).label("success_rate")
    count = func.count(Rollout.id).label("count")
    statement = (
        select(
            Submission.id,
            Submission.user_id,
            func.coalesce(UserGitHub.name, UserGitHub.login_name).label("user_name"),
            Submission.docker_tag,
            count,
            success_rate,
        )
        .join(UserGitHub, UserGitHub.user_id == Submission.user_id)
        .join(Rollout, Rollout.submission_id == Submission.id)
        .where(Submission.task_id == task_id)
        .group_by(Submission.id, UserGitHub.name, UserGitHub.login_name)
        .order_by(success_rate.desc(), count.desc(), Submission.id)
    )
    return alchemy_paginate(session, statement, params)


def create_rollout(*, session: Session, rollout_create: RolloutCreate):
    rollout = Rollout.model_validate(rollout_create)
    session.add(rollout)
    session.flush()
    return rollout


def get_paginated_rollouts(
    *, session: Session, params: Params, filter: dict
) -> Page[Rollout]:
    statement = select(Rollout).order_by(Rollout.id)
    if "submission_id" in filter:
        statement = statement.where(Rollout.submission_id == filter["submission_id"])
    return model_paginate(session, statement, params)


def create_job_failure(
    *, session: Session, submission_id: int, reason: str
) -> JobFailure:
    failure = JobFailure(submission_id=submission_id, reason=reason)
    session.add(failure)
    session.flush()
    return failure
