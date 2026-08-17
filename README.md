# OpenEval Web

## Development

### Setup

#### 1. Clone the repository

```bash
git clone git@github.com:enactic/openarm-online-web.git
cd openarm-online-web
```

From here on, work in the `openarm-online-web` directory.

#### 2. Configure

##### `.env`

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

For environments launched with Podman Compose, variables starting with `POSTGRES_` and `S3_` can remain unchanged.

##### `config.yaml`

Please copy the example file.

```bash
cp config.yaml.example config.yaml
```

By default, any logged-in user can register submissions.
To restrict registration to specific GitHub users or organizations, edit `config.yaml` and fill in the allow lists.

By default, nobody can use admin features.
To use admin features, edit `config.yaml` and fill in the `admin` allow lists.

#### 3. Initial Setup

```bash
scripts/setup.sh
```

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

#### 4. Start up

```bash
podman-compose up -d
```

The server has started and can be accessed at http://127.0.0.1:8000/ .

#### 5. Generate an API key

```console
$ podman-compose exec app /src/scripts/create_api_keys.py demo-key
openarm-online-key-xxx
```

An API key is generated and displayed on stdout, use it when accessing the API.

### Before commit

Run pre-commit before committing:

```bash
pre-commit run --show-diff-on-failure --color=always --all-files
```

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

Copyright 2026 Enactic, Inc.

## Code of Conduct

All participation in the OpenArm project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
