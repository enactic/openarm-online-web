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
from fastapi.openapi.docs import get_swagger_ui_html

from fastapi_pagination import Page

from typing import Optional

from app import crud
from app.deps import CurrentApiKey, PaginationDep, SessionDep
from app.models import Task, Submission, JobResult, JobResultCreate
from app.settings import settings

router = APIRouter(prefix="/api/v1")


@router.get("/tasks", response_model=Page[Task])
def api_get_tasks(session: SessionDep, api_key: CurrentApiKey, params: PaginationDep):
    return crud.get_paginated_tasks(session=session, params=params)


@router.get("/submissions", response_model=Page[Submission])
def api_get_submissions(
    session: SessionDep,
    api_key: CurrentApiKey,
    params: PaginationDep,
    task_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
):
    return crud.get_paginated_submissions(
        session=session, params=params, filter={"task_id": task_id, "user_id": user_id}
    )


@router.post("/job_results", response_model=JobResult)
def api_post_job_results(
    request: JobResultCreate, session: SessionDep, api_key: CurrentApiKey
):
    return crud.create_job_result(session=session, job_result_create=request)


@router.get("/reference", include_in_schema=False)
def api_reference(request: Request):
    return get_swagger_ui_html(
        openapi_url=request.app.openapi_url,
        title=f"API reference - {settings.SITE_NAME}",
    )
