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

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app import crud
from app.deps import (
    CurrentUserOptional,
    NotAdmin,
    NotLoggedIn,
    SessionDep,
    may_teleoperate,
)
from app.models import (
    TeleoperationKind,
    WebRTCAnswerResponse,
    WebRTCOfferRequest,
    WebRTCOfferResponse,
)
from app.responses import not_found
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/tasks/{task_id}/teleoperation", include_in_schema=False)


@router.get("/keyboard", response_class=HTMLResponse)
def teleoperation_keyboard_page(
    task_id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    task = crud.find_task(session=session, id=task_id)
    if task is None:
        return not_found(request, current_user)
    if not may_teleoperate(task, current_user):
        if current_user is None:
            raise NotLoggedIn()
        raise NotAdmin()
    return templates.TemplateResponse(
        request,
        "teleoperation/keyboard.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "task": task,
        },
    )


# The WebXR page drives the robot from a VR headset. Its frontend is
# vendored from dora-openarm-webxr (static/webxr/), whose node the
# runner starts in WebRTC-only mode to answer the offer this page makes
# through the same signaling endpoints as the keyboard page.
@router.get("/webxr", response_class=HTMLResponse)
def teleoperation_webxr_page(
    task_id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    task = crud.find_task(session=session, id=task_id)
    if task is None:
        return not_found(request, current_user)
    if not may_teleoperate(task, current_user):
        if current_user is None:
            raise NotLoggedIn()
        raise NotAdmin()
    return templates.TemplateResponse(
        request,
        "teleoperation/webxr.html",
        {
            "site_name": settings.SITE_NAME,
            "current_user": current_user,
            "task": task,
        },
    )


# The kind sits in the path, mirroring the page URLs, so the pages can
# build these URLs from their own path and an offer always says which
# dora node the runner should start to answer it.
@router.post("/{kind}/offers")
def create_webrtc_offer(
    task_id: int,
    kind: TeleoperationKind,
    body: WebRTCOfferRequest,
    session: SessionDep,
    current_user: CurrentUserOptional,
) -> WebRTCOfferResponse:
    task = crud.find_task(session=session, id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not may_teleoperate(task, current_user):
        raise HTTPException(
            status_code=403, detail="Teleoperation of this task is admin only"
        )
    crud.delete_stale_webrtc_offers(
        session=session, ttl=timedelta(seconds=settings.WEBRTC_OFFER_TTL)
    )
    offer = crud.create_webrtc_offer(
        session=session, task_id=task_id, sdp=body.sdp, kind=kind
    )
    return WebRTCOfferResponse(id=offer.id)


# This is not GET even though it retrieves the answer: retrieving also
# deletes the offer and the answer, so it must not be a safe method.
@router.post("/{kind}/offers/{offer_id}/answer/claim")
def claim_webrtc_answer(
    task_id: int,
    kind: TeleoperationKind,
    offer_id: int,
    session: SessionDep,
    current_user: CurrentUserOptional,
):
    offer = crud.find_webrtc_offer(session=session, id=offer_id)
    if offer is None or offer.task_id != task_id or offer.kind != kind:
        raise HTTPException(status_code=404, detail="Offer not found")
    if not may_teleoperate(offer.task, current_user):
        raise HTTPException(
            status_code=403, detail="Teleoperation of this task is admin only"
        )
    answer = crud.find_webrtc_answer_by_offer_id(session=session, offer_id=offer_id)
    if answer is None:
        return Response(status_code=204)
    # Signaling is done once the browser has the answer, so the rows are
    # no longer needed.
    sdp = answer.sdp
    crud.delete_webrtc_offer(session=session, offer=offer)
    return WebRTCAnswerResponse(sdp=sdp)
