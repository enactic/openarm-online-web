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

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import crud
from app.deps import CurrentUser, CurrentUserOptional, PaginationDep, SessionDep
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/jobs")


@router.get("/", response_class=HTMLResponse)
def list_jobs_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    params: PaginationDep,
    task_id: int = Query(),
):
    task = crud.find_task(session=session, id=task_id)
    if task is None:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    paginator = crud.get_paginated_jobs_with_statistics_by_task_id(
        session=session, params=params, task_id=task_id
    )
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "paginator": paginator,
            "task": task,
        },
    )


@router.get("/{id}", response_class=HTMLResponse)
def job_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    job = crud.get_job_with_statistics_by_id(session=session, id=id)
    if job is None:
        return templates.TemplateResponse(request, "404.html", status_code=404)
    user = crud.find_user(session=session, id=job.user_id)
    return templates.TemplateResponse(
        request,
        "job.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "job": job,
            "user": user,
        },
    )


@router.post("/", response_class=HTMLResponse)
def create_job_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    task_id: int = Form(),
    docker_tag: str = Form(),
):
    crud.create_job(
        session=session,
        user=current_user,
        task_id=task_id,
        docker_tag=docker_tag,
    )
    return RedirectResponse(
        url=request.url_for("list_jobs_by_user_page", id=current_user.id),
        status_code=303,
    )
