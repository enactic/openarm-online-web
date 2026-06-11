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

from app import crud, job_queue
from app.deps import CurrentUserOptional, PaginationDep, SessionDep
from app.responses import not_found
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/rollouts", include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def list_rollouts_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
    params: PaginationDep,
    submission_id: int = Query(),
):
    submission = crud.find_submission(session=session, id=submission_id)
    if submission is None:
        return not_found(request, current_user)
    paginator = crud.get_paginated_rollouts(
        session=session, params=params, filter={"submission_id": submission_id}
    )
    statistics = crud.get_submission_with_statistics_by_id(
        session=session, id=submission.id
    )
    is_owner = current_user is not None and current_user.id == submission.user_id
    if is_owner:
        jobs = job_queue.find_jobs_by_submission_id(
            session=session, submission_id=submission.id
        )
    else:
        jobs = None
    return templates.TemplateResponse(
        request,
        "rollouts.html",
        {
            "count": statistics.count,
            "current_user": current_user,
            "is_owner": is_owner,
            "jobs": jobs,
            "paginator": paginator,
            "rate": statistics.success_rate,
            "site_name": settings.SITE_NAME,
            "submission": submission,
        },
    )
