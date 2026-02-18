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

from sqlmodel import Session, select

from app.models import ApiKey, User, UserGitHub
from app.token import generate_api_key, get_hex_digest


def find_user(*, session, user_id: int) -> User | None:
    return session.get(User, user_id)


def find_user_by_github_id(*, session: Session, github_id: int) -> User | None:
    return session.exec(
        select(User).join(UserGitHub).where(UserGitHub.github_id == github_id)
    ).first()


def create_user(
    *,
    session: Session,
    github_id: int,
    login_name: str | None = None,
    name: str | None = None,
) -> User:
    user_github = UserGitHub(
        github_id=github_id,
        login_name=login_name,
        name=name,
    )
    user = User(github=user_github)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_github(
    *,
    session: Session,
    user: User,
    login_name: str | None = None,
    name: str | None = None,
) -> User:
    user.github.login_name = login_name
    user.github.name = name
    session.add(user)
    session.commit()


def create_api_key(*, session: Session, user_id: int, name: str) -> str:
    key = generate_api_key()
    api_key = ApiKey(user_id=user_id, hashed_key=get_hex_digest(key), name=name)
    session.add(api_key)
    session.commit()
    return key


def get_api_keys_by_user(*, session: Session, user: User) -> list[ApiKey]:
    return session.exec(select(ApiKey).where(ApiKey.user_id == user.id)).all()


def find_api_key_by_hash(*, session: Session, hashed_key: str) -> ApiKey | None:
    return session.exec(select(ApiKey).where(ApiKey.hashed_key == hashed_key)).first()


def delete_api_key(*, session: Session, api_key_id: int, user: User) -> bool:
    api_key = session.exec(
        select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.user_id == user.id)
    ).first()
    if api_key is None:
        return False
    session.delete(api_key)
    session.commit()
    return True
