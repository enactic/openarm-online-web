# OpenEval Web

## Development

### Setup

#### 1. Clone the repository

```bash
git clone git@github.com:enactic/openeval-web.git
cd openeval-web
```

From here on, work in the `openeval-web` directory.

#### 2. Configure `.env`

```bash
cp example.env .env
```

Please configure the following variables according to the comments in `.env`.

* `GITHUB_CLIENT_ID`
* `GITHUB_CLIENT_SECRET`
* `SECRET_KEY`
* `HMAC_KEY`

For environments launched with Docker Compose, variables starting with `POSTGRES_` can remain unchanged.

#### 3. Build and Migration

```bash
docker compose run --rm app alembic -c /src/app/alembic.ini upgrade head
```

#### 4. Start up

```bash
docker compose up -d
```

The server has started and can be accessed at http://localhost:8000/ .

#### 5. Load initial data.

##### Task

```bash
docker compose exec app /src/scripts/create_tasks.py /src/app/tests/fixtures/task.json
```

Three tasks for testing will be created.

##### API key

```console
$ docker compose exec app /src/scripts/create_api_keys.py test-key
openeval-key-xxx
```

An API key is generated and displayed on stdout, use it when accessing the API.
