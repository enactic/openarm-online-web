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

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import crud
from app.deps import AdminUser, CurrentUserOptional, PaginationDep, SessionDep
from app.models import Runtime, TaskForm
from app.responses import not_found
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/tasks", include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def list_tasks_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    params: PaginationDep,
):
    paginator = crud.get_paginated_tasks(session=session, params=params)
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "paginator": paginator,
        },
    )


# Registered before "/{id}" so that "new" isn't parsed as an id.
@router.get("/new", response_class=HTMLResponse)
def new_task_page(
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
):
    return templates.TemplateResponse(
        request,
        "task_form.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "task": None,
            "runtimes": list(Runtime),
            "locked": False,
        },
    )


@router.post("/", response_class=HTMLResponse)
def create_task_page(
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
    form: Annotated[TaskForm, Form()],
):
    task = crud.create_task(
        session=session,
        name=form.name,
        prompt=form.prompt,
        reset_docker_tag=form.reset_docker_tag,
        runtime=form.runtime,
    )
    return RedirectResponse(
        url=request.url_for("task_page", id=task.id),
        status_code=303,
    )


# Submissions and their jobs/rollouts are historical records evaluated
# against the task as it was, so the fields that define the evaluation
# (prompt, reset_docker_tag and runtime) must stay unchanged once the
# task has submissions. The name is just a label, so it stays editable.
def _is_task_locked(*, session, task) -> bool:
    return crud.task_has_submissions(session=session, task_id=task.id)


def _changes_locked_fields(task, form: TaskForm) -> bool:
    return (
        form.prompt != task.prompt
        or form.reset_docker_tag != task.reset_docker_tag
        or form.runtime != task.runtime
    )


def _reject_locked_task(request, current_user, task, error):
    return templates.TemplateResponse(
        request,
        "task.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "task": task,
            "error": error,
        },
        status_code=409,
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
def edit_task_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
):
    task = crud.find_task(session=session, id=id)
    if task is None:
        return not_found(request, current_user)
    return templates.TemplateResponse(
        request,
        "task_form.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "task": task,
            "runtimes": list(Runtime),
            "locked": _is_task_locked(session=session, task=task),
        },
    )


@router.post("/{id}/edit", response_class=HTMLResponse)
def update_task_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
    form: Annotated[TaskForm, Form()],
):
    task = crud.find_task(session=session, id=id)
    if task is None:
        return not_found(request, current_user)
    if _is_task_locked(session=session, task=task) and _changes_locked_fields(
        task, form
    ):
        return _reject_locked_task(
            request,
            current_user,
            task,
            "This task has submissions, so only its name can be edited.",
        )
    crud.update_task(
        session=session,
        task=task,
        name=form.name,
        prompt=form.prompt,
        reset_docker_tag=form.reset_docker_tag,
        runtime=form.runtime,
    )
    return RedirectResponse(
        url=request.url_for("task_page", id=task.id),
        status_code=303,
    )


@router.post("/{id}/delete", response_class=HTMLResponse)
def delete_task_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
):
    task = crud.find_task(session=session, id=id)
    if task is None:
        return not_found(request, current_user)
    if _is_task_locked(session=session, task=task):
        return _reject_locked_task(
            request,
            current_user,
            task,
            "This task has submissions, so it can't be deleted.",
        )
    crud.delete_task(session=session, task=task)
    return RedirectResponse(
        url=request.url_for("list_tasks_page"),
        status_code=303,
    )


@router.get("/{id}", response_class=HTMLResponse)
def task_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    task = crud.find_task(session=session, id=id)
    if task is None:
        return not_found(request, current_user)
    return templates.TemplateResponse(
        request,
        "task.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "task": task,
        },
    )
