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
from fastapi.responses import HTMLResponse

from app import crud
from app.deps import CurrentUserOptional, PaginationDep, SessionDep
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/job_results", include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def list_job_results_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    params: PaginationDep,
    job_id: int = Query(),
):
    job = crud.find_job(session=session, id=job_id)
    paginator = crud.get_paginated_job_results(
        session=session, params=params, filter={"job_id": job_id}
    )
    statistics = crud.get_job_with_statistics_by_id(session=session, id=job.id)
    return templates.TemplateResponse(
        request,
        "job_results.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "job": job,
            "paginator": paginator,
            "count": statistics.count,
            "rate": statistics.success_rate,
        },
    )
