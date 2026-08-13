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


@router.post("/", response_class=HTMLResponse)
def create_api_key_page(
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
    name: str = Form(),
):
    api_key, key = crud.create_api_key(session=session, name=name)
    return templates.TemplateResponse(
        request,
        "api_key_created.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "api_key": api_key,
            "key": key,
        },
    )


@router.post("/{id}/delete", response_class=HTMLResponse)
def delete_api_key_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: AdminUser,
):
    # Lock the API key row to block concurrent claims. Without this, a
    # claim between requeueing and deleting adds a new claimed
    # execution that makes the delete fail with a foreign key
    # violation.
    api_key = crud.find_api_key(session=session, id=id, for_update=True)
    if api_key is None:
        return not_found(request, current_user)
    # Claimed jobs refer to the API key. Requeue them before deleting
    # the API key. The runner that uses the deleted API key can't
    # complete/fail them because the runner can't use all APIs after
    # this.
    job_queue.release_jobs_claimed_by_api_key_id(session=session, api_key_id=api_key.id)
    crud.delete_api_key(session=session, api_key=api_key)
    return RedirectResponse(
        url=request.url_for("list_api_keys_page"),
        status_code=303,
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
