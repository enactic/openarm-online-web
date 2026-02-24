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
from app.deps import SessionDep, CurrentUserOptional
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/users")


@router.get("/{user_id}/jobs", response_class=HTMLResponse)
def list_jobs_by_user_page(
    user_id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    jobs = crud.get_jobs_with_statistics_by_user_id(session=session, user_id=user_id)
    user = crud.find_user(session=session, id=user_id)
    if current_user and user_id == current_user.id:
        tasks = crud.get_tasks(session=session)
    else:
        tasks = None

    return templates.TemplateResponse(
        request,
        "jobs.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "user": user,
            "tasks": tasks,
            "jobs": jobs,
        },
    )
