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

from sqlalchemy.engine.row import Row
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, func, case, cast, Float

from app.models import ApiKey, Job, JobResult, JobResultCreate, Task, User, UserGitHub
from app.security import generate_api_key, get_hex_digest
from app.schemas import JobWithTask


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


def create_job(
    *,
    session: Session,
    user: User,
    task_id: int,
    docker_tag: str,
) -> User:
    job = Job(
        user=user,
        task_id=task_id,
        docker_tag=docker_tag,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def find_job(*, session, id: int) -> Job | None:
    statement = select(Job).where(Job.id == id).options(selectinload(Job.task))
    return session.exec(statement).first()


def get_jobs(*, session: Session) -> list[Job]:
    return session.exec(select(Job)).all()


def get_next_job(*, session: Session) -> JobWithTask | None:
    statement = (
        select(Job)
        .outerjoin(JobResult, JobResult.job_id == Job.id)
        .where(JobResult.id == None)
        .options(selectinload(Job.task))
        .order_by(Job.id)
        .limit(1)
    )
    return session.exec(statement).first()


def get_paginated_jobs(*, session: Session, params: Params, filter: dict) -> Page[Job]:
    statement = select(Job).order_by(Job.id)
    if filter.get("task_id") is not None:
        statement = statement.where(Job.task_id == filter["task_id"])
    if filter.get("user_id") is not None:
        statement = statement.where(Job.user_id == filter["user_id"])
    return model_paginate(session, statement, params)


def _get_jobs_with_statistics_statement() -> Select[Row]:
    success_func_avg = func.avg(case((JobResult.success == True, 1), else_=0))
    return (
        select(
            Job.id,
            Job.user_id,
            Task.name.label("task_name"),
            Job.docker_tag,
            Job.created_at,
            func.count(JobResult.id).label("count"),
            cast(success_func_avg, Float).label("success_rate"),
        )
        .join(Task, Job.task_id == Task.id)
        .outerjoin(JobResult, JobResult.job_id == Job.id)
        .group_by(Job.id, Task.name)
        .order_by(Job.id)
    )


def get_paginated_jobs_with_statistics_by_user_id(
    *, session: Session, params: Params, user_id: int
) -> Page[Row]:
    statement = _get_jobs_with_statistics_statement()
    return alchemy_paginate(session, statement.where(Job.user_id == user_id), params)


def get_paginated_jobs_with_statistics_by_task_id(
    *, session: Session, params: Params, task_id: int
) -> Page[Row]:
    statement = _get_jobs_with_statistics_statement()
    return alchemy_paginate(session, statement.where(Job.task_id == task_id), params)


def get_job_with_statistics_by_id(*, session: Session, id: int) -> Row:
    statement = _get_jobs_with_statistics_statement()
    return session.exec(statement.where(Job.id == id)).first()


def create_job_result(*, session: Session, job_result_create: JobResultCreate):
    job_result = JobResult.model_validate(job_result_create)
    session.add(job_result)
    session.commit()
    session.refresh(job_result)
    return job_result


def get_paginated_job_results(
    *, session: Session, params: Params, filter: dict
) -> Page[JobResult]:
    statement = select(JobResult).order_by(JobResult.id)
    if "job_id" in filter:
        statement = statement.where(JobResult.job_id == filter["job_id"])
    return paginate(session, statement, params)
