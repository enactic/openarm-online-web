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

from app import crud, job_queue
from app.deps import CurrentApiKey, PaginationDep, SessionDep
from app.models import ClaimedJob, Task, Submission, Rollout, RolloutCreate
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


@router.post("/rollouts", response_model=Rollout)
def api_post_rollouts(
    request: RolloutCreate, session: SessionDep, api_key: CurrentApiKey
):
    return crud.create_rollout(session=session, rollout_create=request)


@router.post("/tasks/{task_id}/jobs/claim", response_model=Optional[ClaimedJob])
def api_claim_job(task_id: int, session: SessionDep, api_key: CurrentApiKey):
    job = job_queue.claim_next_job(
        session=session, api_key_id=api_key.id, task_id=task_id
    )
    if job is None:
        return None
    submission = crud.find_submission(session=session, id=job.submission_id)
    return ClaimedJob(
        job_id=job.id,
        docker_tag=submission.docker_tag,
        reset_docker_tag=submission.task.reset_docker_tag,
        prompt=submission.task.prompt,
    )


@router.get("/reference", include_in_schema=False)
def api_reference(request: Request):
    return get_swagger_ui_html(
        openapi_url=request.app.openapi_url,
        title=f"API reference - {settings.SITE_NAME}",
    )
