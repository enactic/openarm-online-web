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

from urllib.parse import quote

from pydantic import BaseModel, Field, PostgresDsn, computed_field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class AllowListSettings(BaseModel):
    allowed_orgs: set[str] = Field(default_factory=set)
    allowed_users: set[str] = Field(default_factory=set)

    @field_validator("allowed_orgs", "allowed_users", mode="after")
    @classmethod
    def _to_lower(cls, value: set[str]) -> set[str]:
        return {v.lower() for v in value}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        yaml_file="config.yaml",
    )

    # These are the default values.
    # They are overridden by the values of environment variables.
    SITE_NAME: str = "OpenEval"

    # Deployed application version shown in the footer. Normally a Git
    # commit ID baked into the production image via the REVISION build
    # argument. Empty means the footer shows no version (e.g. in
    # development).
    REVISION: str = ""

    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "openeval"
    POSTGRES_USER: str = "openeval"
    POSTGRES_PASSWORD: str = "openeval"

    GITHUB_AUTHORIZE_URL: str = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL: str = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL: str = "https://api.github.com/user"

    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str

    SECRET_KEY: str

    API_KEY_PREFIX: str = "openeval-key-"
    HMAC_KEY: str

    API_KEY_HEADER_NAME: str = "X-API-KEY"

    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "openeval"

    # Base URL of the Rerun web viewer.
    # The version should match the Rerun SDK version used by
    # the runner (openarm_dataset converter) to record the RRD file.
    # See also: https://rerun.io/docs/howto/integrations/embed-web
    RERUN_VIEWER_URL: str = "https://app.rerun.io/version/0.33.0/index.html"

    JOBS_PER_SUBMISSION: int = Field(default=3, ge=1)
    CLAIM_TIMEOUT: int = Field(default=30, ge=1)  # minutes
    CLAIM_TIMEOUT_CHECK_INTERVAL: int = Field(default=5, ge=1)  # minutes

    # Allow list for who may register submissions.
    # When both are empty, every logged-in user is allowed.
    submission: AllowListSettings = Field(default_factory=AllowListSettings)

    # Allow list for who may use admin features.
    # When both are empty, nobody is allowed.
    admin: AllowListSettings = Field(default_factory=AllowListSettings)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=quote(self.POSTGRES_PASSWORD, safe=""),
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
