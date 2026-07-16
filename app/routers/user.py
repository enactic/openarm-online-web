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

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app import crud
from app.deps import (
    CurrentUserOptional,
    PaginationDep,
    SessionDep,
    is_submission_allowed,
)
from app.responses import not_found
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/users", include_in_schema=False)


@router.get("/{id}", response_class=HTMLResponse)
def user_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    user = crud.find_user(session=session, id=id)
    if user is None:
        return not_found(request, current_user)
    return templates.TemplateResponse(
        request,
        "user.html",
        {"site_name": settings.SITE_NAME, "current_user": current_user, "user": user},
    )


@router.get("/{id}/submissions", response_class=HTMLResponse)
def list_submissions_by_user_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    params: PaginationDep,
):
    user = crud.find_user(session=session, id=id)
    if user is None:
        return not_found(request, current_user)
    paginator = crud.get_paginated_submissions_with_statistics_by_user_id(
        session=session, params=params, user_id=id
    )
    if current_user and id == current_user.id and is_submission_allowed(user):
        tasks = crud.get_tasks(session=session)
    else:
        tasks = None

    return templates.TemplateResponse(
        request,
        "submissions.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "user": user,
            "tasks": tasks,
            "paginator": paginator,
        },
    )
