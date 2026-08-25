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

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.main import app
from app.models import ApiKey, Task, WebRTCAnswer, WebRTCOffer


# Teleoperation must be usable without logging in, so use a client
# without the authentication overrides of the `client` fixture.
def _anonymous_client() -> TestClient:
    return TestClient(app, follow_redirects=False)


def _create_offer(
    session: Session,
    task: Task,
    sdp: str = "offer-sdp",
    *,
    age: timedelta | None = None,
) -> WebRTCOffer:
    offer = crud.create_webrtc_offer(session=session, task_id=task.id, sdp=sdp)
    if age is not None:
        offer.created_at = datetime.now(timezone.utc) - age
        session.add(offer)
    session.commit()
    session.refresh(offer)
    return offer


def test_teleoperation_page(session: Session, tasks: list[Task]):
    response = _anonymous_client().get(f"/tasks/{tasks[0].id}/teleoperation")
    assert response.status_code == 200
    assert tasks[0].name in response.text
    assert tasks[0].prompt in response.text
    # The key bindings are filled in over WebRTC after connecting.
    assert 'id="help"' in response.text


def test_teleoperation_page_missing_task(session: Session, tasks: list[Task]):
    response = _anonymous_client().get("/tasks/9999/teleoperation")
    assert response.status_code == 404


def test_create_offer(session: Session, tasks: list[Task]):
    response = _anonymous_client().post(
        f"/tasks/{tasks[0].id}/teleoperation/offers", json={"sdp": "offer-sdp"}
    )
    assert response.status_code == 200

    offer = session.get(WebRTCOffer, response.json()["id"])
    assert offer.task_id == tasks[0].id
    assert offer.sdp == "offer-sdp"


def test_create_offer_missing_task(session: Session, tasks: list[Task]):
    response = _anonymous_client().post(
        "/tasks/9999/teleoperation/offers", json={"sdp": "offer-sdp"}
    )
    assert response.status_code == 404


def test_create_offer_deletes_stale_offers(session: Session, tasks: list[Task]):
    stale_unanswered = _create_offer(session, tasks[0], age=timedelta(minutes=10))
    stale_answered = _create_offer(session, tasks[1], age=timedelta(minutes=10))
    crud.create_webrtc_answer(
        session=session, offer_id=stale_answered.id, sdp="answer-sdp"
    )
    fresh = _create_offer(session, tasks[0], "fresh-sdp")

    response = _anonymous_client().post(
        f"/tasks/{tasks[0].id}/teleoperation/offers", json={"sdp": "new-sdp"}
    )
    assert response.status_code == 200

    session.expire_all()
    offer_ids = session.exec(select(WebRTCOffer.id).order_by(WebRTCOffer.id)).all()
    assert offer_ids == [fresh.id, response.json()["id"]]
    assert session.exec(select(WebRTCAnswer)).all() == []


def test_claim_answer_pending(session: Session, tasks: list[Task]):
    offer = _create_offer(session, tasks[0])
    response = _anonymous_client().post(
        f"/tasks/{tasks[0].id}/teleoperation/offers/{offer.id}/answer/claim"
    )
    assert response.status_code == 204


def test_claim_answer(session: Session, tasks: list[Task]):
    offer = _create_offer(session, tasks[0])
    offer_id = offer.id
    crud.create_webrtc_answer(session=session, offer_id=offer_id, sdp="answer-sdp")
    session.commit()

    response = _anonymous_client().post(
        f"/tasks/{tasks[0].id}/teleoperation/offers/{offer_id}/answer/claim"
    )
    assert response.status_code == 200
    assert response.json() == {"sdp": "answer-sdp"}

    # Signaling is done, so the offer and the answer must be deleted.
    session.expire_all()
    assert session.exec(select(WebRTCOffer)).all() == []
    assert session.exec(select(WebRTCAnswer)).all() == []

    response = _anonymous_client().post(
        f"/tasks/{tasks[0].id}/teleoperation/offers/{offer_id}/answer/claim"
    )
    assert response.status_code == 404


def test_claim_answer_wrong_task(session: Session, tasks: list[Task]):
    offer = _create_offer(session, tasks[0])
    response = _anonymous_client().post(
        f"/tasks/{tasks[1].id}/teleoperation/offers/{offer.id}/answer/claim"
    )
    assert response.status_code == 404


def test_claim_answer_missing_offer(session: Session, tasks: list[Task]):
    response = _anonymous_client().post(
        f"/tasks/{tasks[0].id}/teleoperation/offers/9999/answer/claim"
    )
    assert response.status_code == 404


def test_api_get_pending_offers(
    session: Session, tasks: list[Task], client: TestClient
):
    offer1 = _create_offer(session, tasks[0], "sdp1")
    offer2 = _create_offer(session, tasks[0], "sdp2")
    _create_offer(session, tasks[1], "sdp3")

    response = client.get(f"/api/v1/tasks/{tasks[0].id}/teleoperation/offers")
    assert response.status_code == 200
    assert [
        (o["id"], o["task_id"], o["sdp"], o["runtime"]) for o in response.json()
    ] == [
        (offer1.id, tasks[0].id, "sdp1", "OpenArm Cell"),
        (offer2.id, tasks[0].id, "sdp2", "OpenArm Cell"),
    ]


def test_api_get_pending_offers_excludes_answered(
    session: Session, tasks: list[Task], client: TestClient
):
    offer1 = _create_offer(session, tasks[0], "sdp1")
    offer2 = _create_offer(session, tasks[0], "sdp2")
    crud.create_webrtc_answer(session=session, offer_id=offer1.id, sdp="answer-sdp")
    session.commit()

    response = client.get(f"/api/v1/tasks/{tasks[0].id}/teleoperation/offers")
    assert [o["id"] for o in response.json()] == [offer2.id]


def test_api_get_pending_offers_missing_task(
    session: Session, tasks: list[Task], client: TestClient
):
    response = client.get("/api/v1/tasks/9999/teleoperation/offers")
    assert response.status_code == 404


def test_api_get_pending_offers_requires_api_key(session: Session, tasks: list[Task]):
    response = _anonymous_client().get(
        f"/api/v1/tasks/{tasks[0].id}/teleoperation/offers"
    )
    assert response.status_code == 401


def test_api_create_answer(session: Session, tasks: list[Task], client: TestClient):
    offer = _create_offer(session, tasks[0])

    response = client.post(
        f"/api/v1/teleoperation/offers/{offer.id}/answer", json={"sdp": "answer-sdp"}
    )
    assert response.status_code == 200
    assert response.json()["offer_id"] == offer.id
    assert response.json()["sdp"] == "answer-sdp"

    answer = crud.find_webrtc_answer_by_offer_id(session=session, offer_id=offer.id)
    assert answer.sdp == "answer-sdp"


def test_api_create_answer_duplicate(
    session: Session, tasks: list[Task], client: TestClient
):
    offer = _create_offer(session, tasks[0])
    crud.create_webrtc_answer(session=session, offer_id=offer.id, sdp="answer-sdp")
    session.commit()

    response = client.post(
        f"/api/v1/teleoperation/offers/{offer.id}/answer", json={"sdp": "another-sdp"}
    )
    assert response.status_code == 409


def test_api_create_answer_missing_offer(
    session: Session, tasks: list[Task], client: TestClient
):
    response = client.post(
        "/api/v1/teleoperation/offers/9999/answer", json={"sdp": "answer-sdp"}
    )
    assert response.status_code == 404


def test_api_create_answer_requires_api_key(session: Session, tasks: list[Task]):
    offer = _create_offer(session, tasks[0])
    response = _anonymous_client().post(
        f"/api/v1/teleoperation/offers/{offer.id}/answer", json={"sdp": "answer-sdp"}
    )
    assert response.status_code == 401
