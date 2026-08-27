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

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.models import Submission, Task, TeleoperationKind, WebRTCAnswer, WebRTCOffer


def test_list_tasks_with_admin_links(admin, tasks: list[Task], client: TestClient):
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert f"/tasks/{tasks[0].id}/edit" in response.text
    assert "/tasks/new" in response.text


def test_list_tasks_without_admin_links(tasks: list[Task], client: TestClient):
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert f"/tasks/{tasks[0].id}/edit" not in response.text
    assert "/tasks/new" not in response.text


# The fixture tasks all use the OpenArm Cell runtime, whose
# teleoperation is admin only, so non-admins get no teleoperation link.
def test_list_tasks_teleoperation_link_for_non_admin(
    tasks: list[Task], client: TestClient
):
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert "teleoperation" not in response.text


def test_list_tasks_teleoperation_link_for_admin(
    admin, tasks: list[Task], client: TestClient
):
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert f"/tasks/{tasks[0].id}/teleoperation/keyboard" in response.text
    assert f"/tasks/{tasks[0].id}/teleoperation/webxr" in response.text


def test_new_task_page_by_non_admin(client: TestClient):
    assert client.get("/tasks/new").status_code == 403


def test_new_task_page(admin, client: TestClient):
    response = client.get("/tasks/new")
    assert response.status_code == 200
    assert "New task" in response.text


def test_create_task_by_non_admin(client: TestClient):
    response = client.post(
        "/tasks/",
        data={
            "name": "new-task",
            "prompt": "Pick up the cube",
            "reset_docker_tag": "reset:latest",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 403


def test_create_task(admin, session: Session, client: TestClient):
    response = client.post(
        "/tasks/",
        data={
            "name": "new-task",
            "prompt": "Pick up the cube",
            "reset_docker_tag": "reset:latest",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 303

    task = session.exec(select(Task).where(Task.name == "new-task")).one()
    assert response.headers["location"] == f"http://testserver/tasks/{task.id}"
    assert task.prompt == "Pick up the cube"
    assert task.reset_docker_tag == "reset:latest"
    assert task.runtime == "MuJoCo"


def test_create_task_with_empty_name(admin, client: TestClient):
    response = client.post(
        "/tasks/",
        data={
            "name": "",
            "prompt": "Pick up the cube",
            "reset_docker_tag": "reset:latest",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")
    assert "<mark>" in response.text
    # The form is re-rendered with the submitted values preserved.
    assert "Pick up the cube" in response.text
    assert 'value="reset:latest"' in response.text


def test_create_mujoco_task_without_reset_docker_tag(
    admin, session: Session, client: TestClient
):
    response = client.post(
        "/tasks/",
        data={
            "name": "sim-task",
            "prompt": "Pick up the cube",
            "reset_docker_tag": "",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 303

    task = session.exec(select(Task).where(Task.name == "sim-task")).one()
    assert task.reset_docker_tag is None


def test_create_openarm_cell_task_without_reset_docker_tag(admin, client: TestClient):
    response = client.post(
        "/tasks/",
        data={
            "name": "real-task",
            "prompt": "Pick up the cube",
            "reset_docker_tag": "",
            "runtime": "OpenArm Cell",
        },
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")
    assert "reset_docker_tag is required for the OpenArm Cell runtime" in response.text


def test_task_model_requires_reset_docker_tag_unless_mujoco():
    with pytest.raises(ValueError):
        Task.model_validate(
            {"name": "real-task", "prompt": "p", "runtime": "OpenArm Cell"}
        )
    task = Task.model_validate({"name": "sim-task", "prompt": "p", "runtime": "MuJoCo"})
    assert task.reset_docker_tag is None


def test_create_task_with_unknown_runtime(admin, client: TestClient):
    response = client.post(
        "/tasks/",
        data={
            "name": "new-task",
            "prompt": "Pick up the cube",
            "reset_docker_tag": "reset:latest",
            "runtime": "Unknown",
        },
    )
    assert response.status_code == 422


def test_edit_task_page_by_non_admin(tasks: list[Task], client: TestClient):
    assert client.get(f"/tasks/{tasks[0].id}/edit").status_code == 403


def test_edit_task_page(admin, tasks: list[Task], client: TestClient):
    response = client.get(f"/tasks/{tasks[0].id}/edit")
    assert response.status_code == 200
    assert tasks[0].name in response.text
    assert tasks[0].prompt in response.text
    assert tasks[0].reset_docker_tag in response.text


def test_edit_task_page_not_found(admin, client: TestClient):
    assert client.get("/tasks/9999/edit").status_code == 404


def test_edit_task_page_with_submissions(
    admin, submission: Submission, client: TestClient
):
    response = client.get(f"/tasks/{submission.task_id}/edit")
    assert response.status_code == 200
    assert "only its name can be edited" in response.text
    assert "readonly" in response.text
    assert "disabled" in response.text


def test_update_task(admin, session: Session, tasks: list[Task], client: TestClient):
    task_id = tasks[0].id
    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "name": "updated-task",
            "prompt": "Open the drawer",
            "reset_docker_tag": "reset:v2",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"http://testserver/tasks/{task_id}"

    session.expire_all()
    task = session.get(Task, task_id)
    assert task.name == "updated-task"
    assert task.prompt == "Open the drawer"
    assert task.reset_docker_tag == "reset:v2"
    assert task.runtime == "MuJoCo"


def test_update_task_with_empty_name(
    admin, session: Session, tasks: list[Task], client: TestClient
):
    task_id = tasks[0].id
    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "name": "",
            "prompt": "Open the drawer",
            "reset_docker_tag": "reset:v2",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")
    assert "<mark>" in response.text

    session.expire_all()
    task = session.get(Task, task_id)
    assert task.name == tasks[0].name


def test_update_task_by_non_admin(tasks: list[Task], client: TestClient):
    response = client.post(
        f"/tasks/{tasks[0].id}/edit",
        data={
            "name": "updated-task",
            "prompt": "Open the drawer",
            "reset_docker_tag": "reset:v2",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 403


def test_update_task_with_submissions(
    admin, session: Session, submission: Submission, client: TestClient
):
    task_id = submission.task_id
    original_prompt = submission.task.prompt
    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "name": "updated-task",
            "prompt": "Open the drawer",
            "reset_docker_tag": "reset:v2",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 409
    assert "only its name can be edited" in response.text

    session.expire_all()
    task = session.get(Task, task_id)
    assert task.prompt == original_prompt
    assert task.name != "updated-task"


def test_update_task_name_with_submissions(
    admin, session: Session, submission: Submission, client: TestClient
):
    task = submission.task
    task_id = task.id
    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "name": "renamed-task",
            "prompt": task.prompt,
            "reset_docker_tag": task.reset_docker_tag,
            "runtime": task.runtime,
        },
    )
    assert response.status_code == 303

    session.expire_all()
    task = session.get(Task, task_id)
    assert task.name == "renamed-task"


def test_update_task_not_found(admin, client: TestClient):
    response = client.post(
        "/tasks/9999/edit",
        data={
            "name": "updated-task",
            "prompt": "Open the drawer",
            "reset_docker_tag": "reset:v2",
            "runtime": "MuJoCo",
        },
    )
    assert response.status_code == 404


def test_delete_task_by_non_admin(tasks: list[Task], client: TestClient):
    assert client.post(f"/tasks/{tasks[0].id}/delete").status_code == 403


def test_delete_task(admin, session: Session, tasks: list[Task], client: TestClient):
    task_id = tasks[0].id
    # WebRTC offers/answers must not block deleting the task.
    offer = crud.create_webrtc_offer(
        session=session,
        task_id=task_id,
        sdp="offer",
        kind=TeleoperationKind.KEYBOARD,
    )
    crud.create_webrtc_answer(session=session, offer_id=offer.id, sdp="answer")
    session.commit()

    response = client.post(f"/tasks/{task_id}/delete")
    assert response.status_code == 303
    assert response.headers["location"] == "http://testserver/tasks/"

    session.expire_all()
    assert session.get(Task, task_id) is None
    assert session.exec(select(WebRTCOffer)).all() == []
    assert session.exec(select(WebRTCAnswer)).all() == []


def test_delete_task_with_submissions(
    admin, session: Session, submission: Submission, client: TestClient
):
    task_id = submission.task_id
    response = client.post(f"/tasks/{task_id}/delete")
    assert response.status_code == 409
    assert "can&#39;t be deleted" in response.text

    session.expire_all()
    assert session.get(Task, task_id) is not None


def test_delete_task_not_found(admin, client: TestClient):
    assert client.post("/tasks/9999/delete").status_code == 404
