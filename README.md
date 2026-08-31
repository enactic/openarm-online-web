# OpenArm Online Web

## Web API

Runners talk to the server through the Web API under `/api/v1/`. Its
reference, generated from the code, is served by the server itself at
`/api/v1/reference` (also linked from the footer of every page): see
https://online.openarm.dev/api/v1/reference for the production
service, or [http://127.0.0.1:8000/api/v1/reference](http://127.0.0.1:8000/api/v1/reference)
for a local one. It documents authentication, all endpoints, and their
request/response schemas, and lets you try requests with your API key
via the "Authorize" button.

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

### HTTPS for WebXR testing

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
