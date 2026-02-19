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

import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from datetime import datetime, timedelta, timezone

from app.settings import settings

ALGORITHM = "HS256"


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=1)
    payload = {"exp": expire, "sub": subject}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def get_sub(token: str) -> str:
    if token is None:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except (InvalidTokenError, ValidationError) as e:
        return None
