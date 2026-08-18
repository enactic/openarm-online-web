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

FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /openarm-online

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/openarm-online/app/.venv/bin:$PATH"

# The app is imported as `app.*`, so /openarm-online must be on the path.
ENV PYTHONPATH=/openarm-online

RUN mkdir /openarm-online/app
COPY app /openarm-online/app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv --directory app sync --frozen --no-install-workspace --no-dev
COPY scripts/create_api_keys.py \
     scripts/create_tasks.py \
     scripts/update_tasks.py \
     scripts/setup_db.py \
     /openarm-online/scripts/

# The Git commit ID of the source. .git/ isn't available in the build
# context, so it must be passed explicitly:
#   --build-arg REVISION=$(git rev-parse --short HEAD)
ARG REVISION=
ENV REVISION=$REVISION

CMD ["fastapi", "run", "/openarm-online/app/main.py", "--host", "0.0.0.0", "--port", "8000"]
