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

from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app import crud
from app.deps import CurrentUserOptional, SessionDep
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/tasks")


@router.get("/", response_class=HTMLResponse)
def list_tasks_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    page: Optional[int] = Query(default=1),
):
    offset = (page - 1) * settings.PAGE_LIMIT
    tasks = crud.get_tasks(session=session, offset=offset, limit=settings.PAGE_LIMIT)
    total = crud.get_tasks_count(session=session)
    have_next_page = (page * settings.PAGE_LIMIT) < total
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "tasks": tasks,
            "page": page,
            "have_next_page": have_next_page,
        },
    )
