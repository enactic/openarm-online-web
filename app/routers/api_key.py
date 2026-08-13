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

from app import crud, job_queue
from app.deps import AdminUser, PaginationDep, SessionDep
from app.responses import not_found
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/api-keys", include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def list_api_keys_page(
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
    params: PaginationDep,
):
    paginator = crud.get_paginated_api_keys(session=session, params=params)
    return templates.TemplateResponse(
        request,
        "api_keys.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "paginator": paginator,
        },
    )


@router.get("/{id}", response_class=HTMLResponse)
def api_key_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
):
    api_key = crud.find_api_key(session=session, id=id)
    if api_key is None:
        return not_found(request, current_user)
    claimed_executions = job_queue.find_claimed_executions_by_api_key_id(
        session=session, api_key_id=api_key.id
    )
    return templates.TemplateResponse(
        request,
        "api_key.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "api_key": api_key,
            "claimed_executions": claimed_executions,
        },
    )
