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
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator
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


class GitHubOrganizationMembership(SQLModel, table=True):
    __tablename__ = "github_organization_membership"

    user_github_id: int = Field(foreign_key="user_github.id", primary_key=True)
    organization_id: int = Field(
        foreign_key="github_organization.id", primary_key=True, index=True
    )


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
    organizations: list["GitHubOrganization"] = Relationship(
        back_populates="user_githubs",
        link_model=GitHubOrganizationMembership,
    )


class GitHubOrganization(SQLModel, table=True):
    __tablename__ = "github_organization"

    id: int = Field(primary_key=True)
    github_id: int = Field(unique=True, index=True)
    login: str = Field(max_length=255)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    user_githubs: list["UserGitHub"] = Relationship(
        back_populates="organizations",
        link_model=GitHubOrganizationMembership,
    )


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_key"

    id: int = Field(primary_key=True)
    hashed_key: str = Field(unique=True, index=True)
    name: str = Field(unique=True, index=True, max_length=255)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )


class Runtime(StrEnum):
    """Where a task runs: on a real robot cell or in simulation."""

    OPENARM_CELL = "OpenArm Cell"
    MUJOCO = "MuJoCo"


# MuJoCo runs in simulation, so it doesn't need a Docker image to reset
# the environment; every other runtime does.
def _check_reset_docker_tag(runtime: Runtime, reset_docker_tag: str | None):
    if runtime != Runtime.MUJOCO and reset_docker_tag is None:
        raise ValueError(f"reset_docker_tag is required for the {runtime} runtime")


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=255, description="Human-readable name")
    prompt: str = Field(sa_type=Text, description="The instruction given to the policy")
    reset_docker_tag: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Docker image that resets the environment between runs; "
            "`null` for simulated runtimes"
        ),
    )
    runtime: Runtime = Field(
        default=Runtime.OPENARM_CELL,
        sa_column=Column(
            Text,
            nullable=False,
            server_default=Runtime.OPENARM_CELL,
        ),
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    submissions: list["Submission"] = Relationship(back_populates="task")
    webrtc_offers: list["WebRTCOffer"] = Relationship(back_populates="task")

    # Runs on model_validate() (e.g. scripts/create_tasks.py), not on
    # plain construction: SQLModel table models skip validation there.
    @model_validator(mode="after")
    def _validate_reset_docker_tag(self):
        _check_reset_docker_tag(self.runtime, self.reset_docker_tag)
        return self


class Submission(SQLModel, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(
        foreign_key="user.id", index=True, description="User who registered it"
    )
    task_id: int = Field(
        foreign_key="task.id", index=True, description="Task it is evaluated against"
    )
    docker_tag: str = Field(
        max_length=255, description="Docker image that runs the policy"
    )
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
    jobs: list["Job"] = Relationship(back_populates="submission")


class RolloutCreate(SQLModel):
    submission_id: int = Field(
        foreign_key="submission.id",
        index=True,
        nullable=False,
        description="Submission that was evaluated",
    )
    success: bool = Field(
        nullable=False, description="Whether the policy accomplished the task"
    )
    s3_key: str = Field(
        nullable=False,
        max_length=1024,
        description="Rerun recording of the run, uploaded via the upload URL",
    )


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


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id", index=True)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    submission: Submission = Relationship(back_populates="jobs")
    ready_execution: Optional["ReadyExecution"] = Relationship(
        back_populates="job",
        sa_relationship_kwargs={"uselist": False},
    )
    claimed_execution: Optional["ClaimedExecution"] = Relationship(
        back_populates="job",
        sa_relationship_kwargs={"uselist": False},
    )
    failed_execution: Optional["FailedExecution"] = Relationship(
        back_populates="job",
        sa_relationship_kwargs={"uselist": False},
    )


class ReadyExecution(SQLModel, table=True):
    __tablename__ = "ready_execution"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", unique=True, index=True)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    job: Job = Relationship(back_populates="ready_execution")


class ClaimedExecution(SQLModel, table=True):
    __tablename__ = "claimed_execution"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", unique=True, index=True)
    api_key_id: int = Field(foreign_key="api_key.id", index=True)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    job: Job = Relationship(back_populates="claimed_execution")
    api_key: ApiKey = Relationship()


class FailedExecution(SQLModel, table=True):
    __tablename__ = "failed_execution"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", unique=True, index=True)
    reason: str = Field(sa_type=Text)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    job: Job = Relationship(back_populates="failed_execution")


class JobFailure(SQLModel, table=True):
    __tablename__ = "job_failure"

    id: int | None = Field(default=None, primary_key=True)
    submission_id: int = Field(
        foreign_key="submission.id", index=True, description="Submission of the job"
    )
    reason: str = Field(sa_type=Text, description="Why the job couldn't be run")
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )


# The runner uses the kind to start the matching dora node to answer
# the offer.
class TeleoperationKind(StrEnum):
    """What kind of client made a teleoperation offer."""

    KEYBOARD = "keyboard"
    WEBXR = "webxr"


class WebRTCOffer(SQLModel, table=True):
    __tablename__ = "webrtc_offer"

    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    kind: TeleoperationKind = Field(
        sa_column=Column(
            Text,
            nullable=False,
            # Only for rows that predate the column; new offers must
            # say what kind they are.
            server_default=TeleoperationKind.KEYBOARD,
        ),
    )
    sdp: str = Field(sa_type=Text)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    task: Task = Relationship(back_populates="webrtc_offers")
    answer: Optional["WebRTCAnswer"] = Relationship(
        back_populates="offer",
        sa_relationship_kwargs={"uselist": False},
    )


class WebRTCAnswer(SQLModel, table=True):
    __tablename__ = "webrtc_answer"

    id: int | None = Field(default=None, primary_key=True)
    offer_id: int = Field(foreign_key="webrtc_offer.id", unique=True, index=True)
    sdp: str = Field(sa_type=Text)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    offer: WebRTCOffer = Relationship(back_populates="answer")


class ClaimedJob(BaseModel):
    job_id: int = Field(description="Use this ID to complete or fail the job")
    task_id: int
    docker_tag: str = Field(description="Docker image that runs the policy")
    reset_docker_tag: str | None = Field(
        description=(
            "Docker image that resets the environment between runs; "
            "`null` for simulated runtimes"
        )
    )
    prompt: str = Field(description="The instruction given to the policy")
    runtime: str


class CompleteJobRequest(BaseModel):
    success: bool = Field(description="Whether the policy accomplished the task")
    s3_key: str = Field(
        max_length=1024,
        description="Rerun recording of the run, uploaded via the upload URL",
    )


class FailJobRequest(BaseModel):
    reason: str = Field(description="Why the job couldn't be run")


class UploadUrlResponse(BaseModel):
    url: str = Field(description="Presigned URL to `PUT` the `.rrd` file to")
    s3_key: str = Field(description="Key that references the upload afterwards")


class TaskForm(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=1)
    reset_docker_tag: str | None = Field(default=None, min_length=1, max_length=255)
    runtime: Runtime

    # The form sends an empty string when the field is left blank.
    @field_validator("reset_docker_tag", mode="before")
    @classmethod
    def _empty_reset_docker_tag_to_none(cls, value):
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def _validate_reset_docker_tag(self):
        _check_reset_docker_tag(self.runtime, self.reset_docker_tag)
        return self


class PendingWebRTCOffer(BaseModel):
    id: int = Field(description="Use this ID to answer the offer")
    task_id: int
    kind: TeleoperationKind
    sdp: str = Field(description="The offer's SDP")
    created_at: datetime
    runtime: str


class PendingWebRTCOffers(BaseModel):
    # Handed along with the offers so that the runner builds the node's
    # peer with the same servers (including short-lived TURN credentials
    # when a TURN key is configured) as the page.
    ice_servers: list[dict] = Field(
        description=(
            "RTCIceServer-shaped entries to configure the answering "
            "peer with, including short-lived TURN credentials when a "
            "TURN server is configured"
        )
    )
    offers: list[PendingWebRTCOffer]


# The offer's kind comes from the URL it is posted to, not the body.
class WebRTCOfferRequest(BaseModel):
    sdp: str


class WebRTCOfferResponse(BaseModel):
    id: int


class WebRTCAnswerRequest(BaseModel):
    sdp: str = Field(description="The answer's SDP")


class WebRTCAnswerResponse(BaseModel):
    sdp: str
