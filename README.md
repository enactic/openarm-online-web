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

For environments launched with Docker Compose, variables starting with `POSTGRES_` and `S3_` can remain unchanged.

#### 3. Initial Setup

```bash
scripts/setup.sh
```

```
...
openeval-key-xxx
Configure 'OPENEVAL_API_KEY' in .env and start it with 'docker compose up -d'.
```

Finally, an API key will be displayed. Set it in the `.env` file.

#### 4. Start up

```bash
docker compose up -d
```

The server has started and can be accessed at http://localhost:8000/ .

#### Generate an API key

```console
$ docker compose exec app /src/scripts/create_api_keys.py demo-key
openeval-key-xxx
```

An API key is generated and displayed on stdout, use it when accessing the API.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

Copyright 2026 Enactic, Inc.

## Code of Conduct

All participation in the OpenArm project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
