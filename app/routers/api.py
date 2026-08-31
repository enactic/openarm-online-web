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

import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.openapi.docs import get_swagger_ui_html

from fastapi_pagination import Page

from sqlalchemy.exc import IntegrityError

from typing import Optional

from app import crud, job_queue, turn
from app.deps import CurrentApiKey, PaginationDep, SessionDep
from app.models import (
    ClaimedJob,
    CompleteJobRequest,
    FailJobRequest,
    JobFailure,
    PendingWebRTCOffer,
    PendingWebRTCOffers,
    Rollout,
    RolloutCreate,
    Submission,
    Task,
    TeleoperationKind,
    UploadUrlResponse,
    WebRTCAnswer,
    WebRTCAnswerRequest,
)
from app.s3 import generate_presigned_upload_url
from app.settings import settings

# The description and the tag metadata for the generated API
# reference (/api/v1/reference). main.py passes them to the FastAPI
# app because OpenAPI metadata can only be set app-wide.
DESCRIPTION = f"""\
This is the Web API of {settings.SITE_NAME}. It's for runners: programs
that evaluate submissions and drive robots for teleoperation. Browsers
don't need it; they use the web pages instead.

## Authentication

Every endpoint requires an API key sent in the
`{settings.API_KEY_HEADER_NAME}` header:

    {settings.API_KEY_HEADER_NAME}: <your API key>

Administrators issue API keys on the [API keys](/api-keys/) page. A
request without the header gets a `403` response; a request with an
unknown key gets a `401` response.

## Pagination

List endpoints are paginated. Choose a page with the `page` (1-based)
and `size` (at most 100, 20 by default) query parameters. A response
contains the `items` for the page and the `total`/`page`/`size`/`pages`
metadata.

## Evaluating submissions

A runner evaluates submissions like this:

1. Claim the next pending job for a task:
   `POST /api/v1/tasks/{{id}}/jobs/claim`
2. Run the claimed job's Docker image against the task.
3. Get an upload URL with `GET /api/v1/rrd/upload-url` and upload the
   Rerun recording of the run to it.
4. Report the result: `POST /api/v1/jobs/{{id}}/complete` on success or
   failure of the policy, or `POST /api/v1/jobs/{{id}}/fail` when the
   job itself couldn't be run.

A claimed job that is neither completed nor failed within
{settings.CLAIM_TIMEOUT} minutes is failed automatically.

## Answering teleoperation offers

A runner that can be teleoperated does this:

1. Poll `GET /api/v1/tasks/{{id}}/teleoperation/{{kind}}/offers` for
   the kinds of offers it can answer.
2. Answer an offer with
   `POST /api/v1/teleoperation/offers/{{id}}/answer`.
3. Drive the robot with the data received over the established WebRTC
   connection.
"""

TAGS_METADATA = [
    {
        "name": "Tasks",
        "description": "Tasks that submissions are evaluated against.",
    },
    {
        "name": "Submissions",
        "description": "Policies registered by users for a task.",
    },
    {
        "name": "Jobs",
        "description": "The queue of submission evaluation jobs for runners.",
    },
    {
        "name": "Rollouts",
        "description": "Results of evaluation runs.",
    },
    {
        "name": "Teleoperation",
        "description": "WebRTC signaling for teleoperating a robot from a browser.",
    },
    {
        "name": "Recordings",
        "description": "Uploading Rerun recordings (`.rrd` files) of evaluation runs.",
    },
]

router = APIRouter(
    prefix="/api/v1",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid API key"},
        status.HTTP_403_FORBIDDEN: {"description": "Missing API key"},
    },
)


@router.get("/tasks", response_model=Page[Task], tags=["Tasks"], summary="List tasks")
def api_get_tasks(session: SessionDep, api_key: CurrentApiKey, params: PaginationDep):
    """Return all tasks, paginated."""
    return crud.get_paginated_tasks(session=session, params=params)


@router.get(
    "/submissions",
    response_model=Page[Submission],
    tags=["Submissions"],
    summary="List submissions",
)
def api_get_submissions(
    session: SessionDep,
    api_key: CurrentApiKey,
    params: PaginationDep,
    task_id: Optional[int] = Query(None, description="Only submissions for this task"),
    user_id: Optional[int] = Query(None, description="Only submissions by this user"),
):
    """Return all submissions, paginated and optionally filtered."""
    return crud.get_paginated_submissions(
        session=session, params=params, filter={"task_id": task_id, "user_id": user_id}
    )


@router.post(
    "/rollouts",
    response_model=Rollout,
    tags=["Rollouts"],
    summary="Record a rollout",
)
def api_post_rollouts(
    request: RolloutCreate, session: SessionDep, api_key: CurrentApiKey
):
    """Record the result of an evaluation run for a submission.

    Use this only for runs outside the job queue; completing a claimed
    job records its rollout automatically.
    """
    return crud.create_rollout(session=session, rollout_create=request)


@router.post(
    "/tasks/{id}/jobs/claim",
    response_model=Optional[ClaimedJob],
    tags=["Jobs"],
    summary="Claim the next job",
)
def api_claim_job(id: int, session: SessionDep, api_key: CurrentApiKey):
    """Claim the next pending evaluation job for the task.

    Returns `null` when no job is pending. Finish a claimed job with
    the complete or fail endpoint; a job that is neither completed nor
    failed in time is failed automatically.
    """
    job = job_queue.claim_next_job(session=session, api_key_id=api_key.id, task_id=id)
    if job is None:
        return None
    submission = crud.find_submission(session=session, id=job.submission_id)
    return ClaimedJob(
        job_id=job.id,
        task_id=submission.task_id,
        docker_tag=submission.docker_tag,
        reset_docker_tag=submission.task.reset_docker_tag,
        prompt=submission.task.prompt,
        runtime=submission.task.runtime,
    )


@router.post(
    "/jobs/{id}/complete",
    response_model=Rollout,
    tags=["Jobs"],
    summary="Complete a claimed job",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "The job is not claimed by this API key"
        },
        status.HTTP_404_NOT_FOUND: {"description": "No such job"},
    },
)
def api_complete_job(
    id: int, payload: CompleteJobRequest, session: SessionDep, api_key: CurrentApiKey
):
    """Report that a claimed job was run and record its rollout.

    Use this when the submission was evaluated, whether the policy
    succeeded or not; use the fail endpoint when the job itself
    couldn't be run. Only the API key that claimed the job may complete
    it.
    """
    try:
        job = job_queue.complete_job(session=session, job_id=id, api_key_id=api_key.id)
    except job_queue.JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job({id}) not found"
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    return crud.create_rollout(
        session=session,
        rollout_create=RolloutCreate(
            submission_id=job.submission_id,
            success=payload.success,
            s3_key=payload.s3_key,
        ),
    )


@router.post(
    "/jobs/{id}/fail",
    response_model=JobFailure,
    tags=["Jobs"],
    summary="Fail a claimed job",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "The job is not claimed by this API key"
        },
        status.HTTP_404_NOT_FOUND: {"description": "No such job"},
    },
)
def api_fail_job(
    id: int, payload: FailJobRequest, session: SessionDep, api_key: CurrentApiKey
):
    """Report that a claimed job couldn't be run and record why.

    Only the API key that claimed the job may fail it.
    """
    try:
        job = job_queue.fail_job(
            session=session,
            job_id=id,
            reason=payload.reason,
            api_key_id=api_key.id,
        )
    except job_queue.JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job({id}) not found"
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    return crud.create_job_failure(
        session=session,
        submission_id=job.submission_id,
        reason=payload.reason,
    )


# The kind is part of the path, mirroring the browser-facing signaling
# endpoints: a runner polls for the kinds it can answer.
@router.get(
    "/tasks/{id}/teleoperation/{kind}/offers",
    response_model=PendingWebRTCOffers,
    tags=["Teleoperation"],
    summary="List pending teleoperation offers",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such task"},
    },
)
def api_get_pending_webrtc_offers(
    id: int, kind: TeleoperationKind, session: SessionDep, api_key: CurrentApiKey
):
    """Return the unanswered WebRTC offers of the given kind for the task.

    The response also carries the ICE servers to use when answering,
    including short-lived TURN credentials when a TURN server is
    configured. Poll this endpoint for the kinds you can answer.
    """
    task = crud.find_task(session=session, id=id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task({id}) not found"
        )
    offers = crud.get_pending_webrtc_offers(session=session, task_id=id, kind=kind)
    return PendingWebRTCOffers(
        ice_servers=turn.get_ice_servers(),
        offers=[
            PendingWebRTCOffer(
                id=offer.id,
                task_id=offer.task_id,
                kind=offer.kind,
                sdp=offer.sdp,
                created_at=offer.created_at,
                runtime=task.runtime,
            )
            for offer in offers
        ],
    )


@router.post(
    "/teleoperation/offers/{id}/answer",
    response_model=WebRTCAnswer,
    tags=["Teleoperation"],
    summary="Answer a teleoperation offer",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such offer"},
        status.HTTP_409_CONFLICT: {"description": "The offer is already answered"},
    },
)
def api_create_webrtc_answer(
    id: int, payload: WebRTCAnswerRequest, session: SessionDep, api_key: CurrentApiKey
):
    """Answer a pending WebRTC offer to start a teleoperation session.

    Each offer can be answered only once, even by concurrent runners;
    the loser gets a `409` response.
    """
    offer = crud.find_webrtc_offer(session=session, id=id)
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WebRTC offer({id}) not found",
        )
    try:
        return crud.create_webrtc_answer(session=session, offer_id=id, sdp=payload.sdp)
    except IntegrityError as err:
        # The unique index on offer_id rejects a second answer, including
        # one from a concurrent runner.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"WebRTC offer({id}) is already answered",
        ) from err


@router.get(
    "/rrd/upload-url",
    response_model=UploadUrlResponse,
    tags=["Recordings"],
    summary="Get a recording upload URL",
)
def api_get_upload_url(api_key: CurrentApiKey):
    """Return a presigned URL for uploading a Rerun recording.

    `PUT` the `.rrd` file to the URL before it expires, then reference
    the upload by its `s3_key`, e.g. when completing a job.
    """
    s3_key = f"rrd/{uuid.uuid4()}.rrd"
    return UploadUrlResponse(url=generate_presigned_upload_url(s3_key), s3_key=s3_key)


@router.get("/reference", include_in_schema=False)
def api_reference(request: Request):
    return get_swagger_ui_html(
        openapi_url=request.app.openapi_url,
        title=f"API reference - {settings.SITE_NAME}",
    )
