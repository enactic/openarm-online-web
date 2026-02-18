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

from collections.abc import Generator
from typing import Annotated, Optional

from fastapi import Depends, Header, Request, HTTPException
from sqlmodel import Session

from app.crud import find_api_key_by_hash, find_user
from app.db import engine
from app.models import User
from app.settings import settings
from app.token import get_sub, get_hex_digest


class NotLoggedIn(Exception):
    pass


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]


def find_current_user_optional(request: Request, session: SessionDep) -> Optional[User]:
    token = request.cookies.get("access_token")
    user_id = get_sub(token)
    if user_id is None:
        return None
    return find_user(session=session, user_id=user_id)


CurrentUserOptional = Annotated[Optional[User], Depends(find_current_user_optional)]


def find_current_user(user: CurrentUserOptional) -> User:
    if user is None:
        raise NotLoggedIn()
    return user


CurrentUser = Annotated[User, Depends(find_current_user)]


def find_api_user(
    session: SessionDep,
    authorization: str = Header(),
) -> User:
    if not authorization.startswith("Bearer " + settings.API_KEY_PREFIX):
        raise HTTPException(status_code=401, detail="Invalid API key")

    key = authorization.removeprefix("Bearer ")
    hashed_key = get_hex_digest(key)
    api_key = find_api_key_by_hash(session=session, hashed_key=hashed_key)
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = find_user(session=session, user_id=api_key.user_id)
    if user is None or user.github is None:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


ApiUser = Annotated[User, Depends(find_api_user)]
