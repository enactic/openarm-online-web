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

"""ICE servers for teleoperation WebRTC peers.

Cloudflare Realtime TURN uses short-lived credentials minted through
its API rather than a fixed username and password, so both teleoperation
pages and the runner fetch their ICE servers from this app: it is the
only place that holds the Cloudflare TURN key. Without a configured
key the peers still get the public STUN server, which is enough
whenever a direct connection is possible.
"""

import logging
import time

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

STUN_ICE_SERVERS = [{"urls": ["stun:stun.cloudflare.com:3478"]}]

# Stands in for an unset TURN key value: Secrets Manager cannot store
# an empty value, so a deployment that does not use TURN stores this
# instead (see scripts/put_cloudflare_turn_secrets.py).
DISABLED = "disabled"

CLOUDFLARE_TURN_CREDENTIALS_URL = (
    "https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate"
)

# Minted credentials, kept until half their TTL so that a credential
# handed out here never expires while the connection it was minted for
# is still being set up.
_cache: tuple[float, list[dict]] | None = None


def _mint_ice_servers() -> list[dict]:
    response = httpx.post(
        CLOUDFLARE_TURN_CREDENTIALS_URL.format(key_id=settings.CLOUDFLARE_TURN_KEY_ID),
        headers={"Authorization": f"Bearer {settings.CLOUDFLARE_TURN_API_TOKEN}"},
        json={"ttl": settings.TURN_CREDENTIAL_TTL},
    )
    response.raise_for_status()
    ice_servers = response.json()["iceServers"]
    # The API returns one ICE server entry; RTCPeerConnection takes a
    # list of them.
    if isinstance(ice_servers, dict):
        ice_servers = [ice_servers]
    return ice_servers


def _turn_key_configured() -> bool:
    return all(
        value and value != DISABLED
        for value in (
            settings.CLOUDFLARE_TURN_KEY_ID.strip(),
            settings.CLOUDFLARE_TURN_API_TOKEN.strip(),
        )
    )


def get_ice_servers() -> list[dict]:
    """Return the ICE servers a teleoperation peer should be built with."""
    global _cache
    if not _turn_key_configured():
        return STUN_ICE_SERVERS
    now = time.monotonic()
    if _cache is not None and now < _cache[0]:
        return _cache[1]
    try:
        ice_servers = _mint_ice_servers()
    except (httpx.HTTPError, KeyError, ValueError):
        # A broken TURN setup must not take teleoperation down with it:
        # peers that can connect directly still can, over STUN.
        logger.exception("Cannot mint Cloudflare TURN credentials")
        return STUN_ICE_SERVERS
    _cache = (now + settings.TURN_CREDENTIAL_TTL / 2, ice_servers)
    return ice_servers
