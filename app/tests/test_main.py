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

from fastapi.testclient import TestClient

from app.templates import templates


def test_footer_with_revision(monkeypatch, client: TestClient):
    monkeypatch.setitem(templates.env.globals, "revision", "abc1234")
    response = client.get("/")
    assert response.status_code == 200
    assert "Revision: abc1234" in response.text


def test_footer_without_revision(monkeypatch, client: TestClient):
    monkeypatch.setitem(templates.env.globals, "revision", "")
    response = client.get("/")
    assert response.status_code == 200
    assert "Revision:" not in response.text
