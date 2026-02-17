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

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=DateTime(timezone=True)
    )

    github: "UserGitHub" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "lazy": "joined"},
    )


class UserGitHub(SQLModel, table=True):
    __tablename__ = "user_github"

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    github_id: int = Field(unique=True, index=True)
    login_name: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, max_length=255)

    user: User = Relationship(back_populates="github")
