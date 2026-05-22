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

from sqlalchemy import DateTime, Text
from sqlmodel import Column, Field, Relationship, SQLModel, func


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    github: "UserGitHub" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "lazy": "joined"},
    )
    submissions: list["Submission"] = Relationship(back_populates="user")


class UserGitHub(SQLModel, table=True):
    __tablename__ = "user_github"

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    github_id: int = Field(unique=True, index=True)
    login_name: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )

    user: User = Relationship(back_populates="github")


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_key"

    id: int = Field(primary_key=True)
    hashed_key: str = Field(unique=True, index=True)
    name: str = Field(max_length=255)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None = Field(default=None, max_length=255)
    prompt: str = Field(sa_type=Text)
    reset_docker_tag: str = Field(max_length=255)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    submissions: list["Submission"] = Relationship(back_populates="task")


class Submission(SQLModel, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    docker_tag: str = Field(max_length=255)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    user: User = Relationship(back_populates="submissions")
    task: Task = Relationship(back_populates="submissions")
    rollouts: list["Rollout"] = Relationship(back_populates="submission")


class RolloutCreate(SQLModel):
    submission_id: int = Field(foreign_key="submission.id", index=True, nullable=False)
    success: bool = Field(nullable=False)


class Rollout(RolloutCreate, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    submission: Submission = Relationship(back_populates="rollouts")
