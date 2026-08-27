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

import httpx
import pytest

from app import turn
from app.settings import settings


@pytest.fixture(autouse=True)
def reset_ice_server_cache(monkeypatch):
    monkeypatch.setattr(turn, "_cache", None)


@pytest.fixture(name="turn_key")
def fixture_turn_key(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_TURN_KEY_ID", "test-key-id")
    monkeypatch.setattr(settings, "CLOUDFLARE_TURN_API_TOKEN", "test-api-token")


# Empty or "disabled" values mean TURN is off: "disabled" stands in
# for empty in Secrets Manager, which cannot store an empty value.
@pytest.mark.parametrize(
    "key_id,api_token",
    [
        ("", ""),
        ("disabled", "disabled"),
        ("test-key-id", "disabled"),
        ("  ", "test-api-token"),
    ],
)
def test_get_ice_servers_without_turn_key(monkeypatch, key_id, api_token):
    monkeypatch.setattr(settings, "CLOUDFLARE_TURN_KEY_ID", key_id)
    monkeypatch.setattr(settings, "CLOUDFLARE_TURN_API_TOKEN", api_token)
    assert turn.get_ice_servers() == turn.STUN_ICE_SERVERS


def test_get_ice_servers_with_turn_key(turn_key, monkeypatch):
    minted = [
        {
            "urls": ["turn:turn.cloudflare.com:3478?transport=udp"],
            "username": "u",
            "credential": "c",
        }
    ]
    calls = []

    def mint():
        calls.append(1)
        return minted

    monkeypatch.setattr(turn, "_mint_ice_servers", mint)
    assert turn.get_ice_servers() == minted
    # Minted credentials are cached, not minted per request.
    assert turn.get_ice_servers() == minted
    assert len(calls) == 1


def test_get_ice_servers_minting_failure(turn_key, monkeypatch):
    def mint():
        raise httpx.HTTPError("Cloudflare is down")

    monkeypatch.setattr(turn, "_mint_ice_servers", mint)
    # A broken TURN setup must not take teleoperation down: fall back to
    # STUN only.
    assert turn.get_ice_servers() == turn.STUN_ICE_SERVERS
