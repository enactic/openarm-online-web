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

from fastapi import Depends, Query, Request, HTTPException
from fastapi.security.api_key import APIKeyHeader
from fastapi_pagination import Params
from sqlmodel import Session
from starlette import status

from app import crud
from app.db import engine
from app.models import ApiKey, Runtime, Task, User
from app.security import get_hex_digest, get_sub
from app.settings import settings

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=True)


class NotLoggedIn(Exception):
    pass


class NotSubmissionAllowed(Exception):
    pass


class NotAdmin(Exception):
    pass


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        with session.begin():
            yield session


SessionDep = Annotated[Session, Depends(get_db)]


def find_current_user_optional(request: Request, session: SessionDep) -> Optional[User]:
    token = request.cookies.get("access_token")
    user_id = get_sub(token)
    if user_id is None:
        return None
    return crud.find_user(session=session, id=user_id)


CurrentUserOptional = Annotated[Optional[User], Depends(find_current_user_optional)]


def find_current_user(user: CurrentUserOptional) -> User:
    if user is None:
        raise NotLoggedIn()
    return user


CurrentUser = Annotated[User, Depends(find_current_user)]


def find_current_api_key(
    session: SessionDep,
    key: str = Depends(api_key_header),
) -> ApiKey:
    api_key = crud.find_api_key_by_hash(session=session, hashed_key=get_hex_digest(key))
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    return api_key


CurrentApiKey = Annotated[ApiKey, Depends(find_current_api_key)]


def get_pagination_params(
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)
) -> Params:
    return Params(page=page, size=size)


PaginationDep = Annotated[Params, Depends(get_pagination_params)]


def is_submission_allowed(user: Optional[User]) -> bool:
    if not user or not user.github:
        return False

    allowed_orgs = settings.submission.allowed_orgs
    allowed_users = settings.submission.allowed_users
    # No settings.
    if not allowed_orgs and not allowed_users:
        return True

    if user.github.login_name and user.github.login_name.lower() in allowed_users:
        return True
    orgs = {org.login.lower() for org in user.github.organizations}
    return bool(orgs & allowed_orgs)


def require_submission_allowed(user: CurrentUser) -> User:
    if not is_submission_allowed(user):
        raise NotSubmissionAllowed()
    return user


SubmissionAllowedUser = Annotated[User, Depends(require_submission_allowed)]


def is_admin(user: Optional[User]) -> bool:
    if not user or not user.github:
        return False

    # Unlike is_submission_allowed(), empty allow lists mean nobody is
    # an admin.
    allowed_users = settings.admin.allowed_users
    if user.github.login_name and user.github.login_name.lower() in allowed_users:
        return True
    orgs = {org.login.lower() for org in user.github.organizations}
    return bool(orgs & settings.admin.allowed_orgs)


def require_admin(user: CurrentUser) -> User:
    if not is_admin(user):
        raise NotAdmin()
    return user


AdminUser = Annotated[User, Depends(require_admin)]


# MuJoCo runs in simulation, so anyone may teleoperate it; every other
# runtime drives a real robot, so only admins may.
def may_teleoperate(task: Task, user: Optional[User]) -> bool:
    return task.runtime == Runtime.MUJOCO or is_admin(user)
