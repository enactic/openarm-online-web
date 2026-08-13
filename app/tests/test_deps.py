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

from app.deps import NotAdmin, is_admin, require_admin
from app.models import User
from app.settings import AllowListSettings, settings


def test_is_admin_without_user():
    assert not is_admin(None)


def test_is_admin_empty_allow_lists(user: User):
    assert not is_admin(user)


def test_is_admin_allowed_user(monkeypatch, user: User):
    monkeypatch.setattr(
        settings, "admin", AllowListSettings(allowed_users={"TestUser"})
    )
    assert is_admin(user)


def test_is_admin_allowed_org(monkeypatch, user: User):
    monkeypatch.setattr(settings, "admin", AllowListSettings(allowed_orgs={"TestOrg"}))
    assert is_admin(user)


def test_is_admin_not_allowed_user(monkeypatch, user: User):
    monkeypatch.setattr(
        settings, "admin", AllowListSettings(allowed_users={"other-user"})
    )
    assert not is_admin(user)


def test_require_admin_not_allowed(user: User):
    with pytest.raises(NotAdmin):
        require_admin(user)


def test_require_admin_allowed(monkeypatch, user: User):
    monkeypatch.setattr(
        settings, "admin", AllowListSettings(allowed_users={"testuser"})
    )
    assert require_admin(user) is user
