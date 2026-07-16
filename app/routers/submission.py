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

from app import crud, job_queue
from app.deps import (
    CurrentUserOptional,
    PaginationDep,
    SessionDep,
    SubmissionAllowedUser,
)
from app.responses import not_found
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/submissions", include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def list_submissions_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    params: PaginationDep,
    task_id: int = Query(),
):
    task = crud.find_task(session=session, id=task_id)
    if task is None:
        return not_found(request, current_user)
    paginator = crud.get_paginated_submissions_with_statistics_by_task_id(
        session=session, params=params, task_id=task_id
    )
    return templates.TemplateResponse(
        request,
        "submissions.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "paginator": paginator,
            "task": task,
        },
    )


@router.get("/{id}", response_class=HTMLResponse)
def submission_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    submission = crud.get_submission_with_statistics_by_id(session=session, id=id)
    if submission is None:
        return not_found(request, current_user)
    user = crud.find_user(session=session, id=submission.user_id)
    return templates.TemplateResponse(
        request,
        "submission.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "submission": submission,
            "user": user,
        },
    )


@router.post("/", response_class=HTMLResponse)
def create_submission_page(
    request: Request,
    session: SessionDep,
    current_user: SubmissionAllowedUser,
    task_id: int = Form(),
    docker_tag: str = Form(),
):
    submission = crud.create_submission(
        session=session,
        user=current_user,
        task_id=task_id,
        docker_tag=docker_tag,
    )
    job_queue.bulk_enqueue(
        session=session, submission_id=submission.id, count=settings.JOBS_PER_SUBMISSION
    )
    return RedirectResponse(
        url=request.url_for("list_submissions_by_user_page", id=current_user.id),
        status_code=303,
    )
