# Development

This document is for developers working on OpenArm Online Web itself.
For what the service does and the Web API, see the top-level
[README](../README.md).

Run all commands below from the repository root.

## Overview

The server is a [FastAPI](https://fastapi.tiangolo.com/) application
living in this `app/` directory:

* `main.py`: Assembles the application and starts the background
  timeout worker.
* `routers/`: Page and API endpoints. `routers/api.py` is the
  versioned Web API under `/api/v1/` used by runners; the other
  routers serve the server-rendered pages.
* `models.py`, `crud.py`, `db.py`: SQLModel models and database
  access. Schema migrations live under `alembic/`.
* `job_queue.py`, `scheduler.py`: The submission evaluation job queue
  and the background worker that fails claimed jobs that time out.
* `s3.py`: Presigned uploads of Rerun recordings to S3-compatible
  storage.
* `turn.py`: Mints short-lived Cloudflare TURN credentials for
  teleoperation WebRTC peers.
* `templates/`, `static/`: Jinja2 templates for the server-rendered
  pages and browser-side JavaScript, including the keyboard and WebXR
  teleoperation clients.
* `tests/`: The pytest suite.

The local environment is run with Podman Compose (`compose.yaml` at
the repository root) and consists of these services:

* `app`: The FastAPI development server. `app/`, `scripts/` and
  `config.yaml` are bind-mounted, so code changes reload
  automatically.
* `db`: PostgreSQL.
* `s3`: [RustFS](https://rustfs.com/), an S3-compatible object store
  for Rerun recordings.
* `runner`: An end-to-end test runner that claims and evaluates jobs.
* `https`: An optional TLS-terminating reverse proxy (see
  [HTTPS for WebXR testing](#https-for-webxr-testing)).

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:enactic/openarm-online-web.git
cd openarm-online-web
```

From here on, work in the `openarm-online-web` directory.

### 2. Configure

#### `.env`

```bash
cp .env.example .env
```

Please configure the following variables according to the comments in `.env`.

* `GITHUB_CLIENT_ID`
* `GITHUB_CLIENT_SECRET`
* `SECRET_KEY`
* `HMAC_KEY`

To get the values for `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`,
you need to [create a GitHub OAuth
app](https://docs.github.com/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app).
Here are the recommended OAuth app settings for the local environment:

* Application name: `OpenArm Online local`
* Homepage URL: `http://127.0.0.1:8000/`
* Authorization callback URL: `http://127.0.0.1:8000/login/github/callback`

For environments launched with Podman Compose, variables starting with
`POSTGRES_` and `S3_` can remain unchanged.

#### `config.yaml`

Please copy the example file.

```bash
cp config.yaml.example config.yaml
```

By default, any logged-in user can register submissions.
To restrict registration to specific GitHub users or organizations, edit `config.yaml` and fill in the allow lists.

By default, nobody can use admin features.
To use admin features, edit `config.yaml` and fill in the `admin` allow lists.

### 3. Initial Setup

```bash
scripts/setup.sh
```

This applies the database migrations, creates the storage bucket,
registers the example tasks and creates an API key for the local
runner:

```
...
openarm-online-key-xxx
Configure 'OPENARM_ONLINE_API_KEY' in .env.runner and start it with 'podman-compose up -d'.
```

Finally, an API key will be displayed. Set it in the `.env.runner` file.

```bash
cp .env.runner.example .env.runner
editor .env.runner
```

### 4. Start up

```bash
podman-compose up -d
```

The server has started and can be accessed at http://127.0.0.1:8000/ .

### 5. Generate an API key

```console
$ podman-compose exec app /src/scripts/create_api_keys.py demo-key
openarm-online-key-xxx
```

An API key is generated and displayed on stdout, use it when accessing the API.

## Running tests

```bash
scripts/run-tests.sh
```

This creates the `openarm_online_test` database if needed and runs the
pytest suite in the `app` container. To run a subset:

```bash
podman-compose exec --env POSTGRES_DB=openarm_online_test \
  --workdir /src/app app uv run pytest tests/test_api.py
```

## Database migrations

The schema is managed with [Alembic](https://alembic.sqlalchemy.org/).
After changing `models.py`, generate a migration:

```bash
podman-compose run --rm app alembic -c /src/app/alembic.ini \
  revision --autogenerate -m "Describe the change"
```

Review the generated file under `app/alembic/versions/`, then apply it:

```bash
podman-compose run --rm app alembic -c /src/app/alembic.ini upgrade head
```

`scripts/setup.sh` also applies pending migrations.

## Dependencies

Python dependencies are managed with [uv](https://docs.astral.sh/uv/)
in `app/pyproject.toml` and `app/uv.lock`. They are installed into the
container image at build time, so after changing them rebuild the
image:

```bash
podman-compose up -d --build app
```

## HTTPS for WebXR testing

WebXR only runs in a secure context, so testing the VR teleoperation
page from a VR device needs HTTPS. An optional TLS-terminating reverse
proxy is provided as the `https` compose service.

Generate a self-signed certificate for a host name that the VR device
can resolve. A `.local` host name configured automatically by Avahi is
a convenient choice:

```bash
scripts/prepare_tls.sh $(hostname).local
```

Then start the proxy:

```bash
podman-compose --profile https up -d
```

The server can now be accessed at `https://$(hostname).local:8443/`
from the VR device. The certificate is self-signed, so the browser
shows a warning to step through once.

Note that logging in over HTTPS needs the GitHub OAuth app's callback
URL to match, so use a MuJoCo runtime task, whose teleoperation needs
no login, unless you have set that up.

## Before commit

Run pre-commit before committing:

```bash
pre-commit run --show-diff-on-failure --color=always --all-files
```

## Release

See [dev/README.md](../dev/README.md).

## Infrastructure

The AWS infrastructure is managed with OpenTofu: see
[infra/README.md](../infra/README.md).
