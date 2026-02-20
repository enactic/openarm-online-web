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

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import crud
from app.deps import SessionDep, CurrentUser
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/jobs")


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
        url=request.url_for("list_jobs_by_user_page", user_id=current_user.id),
        status_code=303,
    )
