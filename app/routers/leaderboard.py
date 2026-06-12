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

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app import crud
from app.deps import CurrentUserOptional, PaginationDep, SessionDep
from app.responses import not_found
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/leaderboard", include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def list_leaderboard_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    params: PaginationDep,
    task_id: int = Query(),
):
    task = crud.find_task(session=session, id=task_id)
    if task is None:
        return not_found(request, current_user)
    paginator = crud.get_paginated_top_submissions_by_task_id(
        session=session, params=params, task_id=task.id
    )
    return templates.TemplateResponse(
        request,
        "leaderboard.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "task": task,
            "paginator": paginator,
        },
    )
