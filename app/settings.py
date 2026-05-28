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

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # These are the default values.
    # They are overridden by the values of environment variables.
    SITE_NAME: str = "OpenEval"

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

    CLAIM_TIMEOUT: int = Field(default=30, ge=1)  # minutes
    CLAIM_TIMEOUT_CHECK_INTERVAL: int = Field(default=5, ge=1)  # minutes

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )


settings = Settings()
