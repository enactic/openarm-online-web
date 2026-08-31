# OpenArm Online Web

The web part of OpenArm Online, an evaluation service for
[OpenArm](https://openarm.dev/) robot arms: submit your policy, run it
against OpenArm tasks, and compare results with everyone else's. The
production service runs at https://online.openarm.dev/ .

## What you can do

### Submit a policy

Log in with your GitHub account, pick a task and register a
submission: a Docker image that runs your policy. Runners connected to
real or simulated OpenArm hardware pick up your submission, evaluate
it against the task and report the results. Depending on the server's
configuration, registration may be limited to specific GitHub users or
organizations.

### Watch and compare results

Each evaluation run appears as a rollout with a
[Rerun](https://rerun.io/) recording you can replay in the browser,
and the leaderboard ranks submissions by their results per task.

### Teleoperate a robot

Some tasks can be driven live from the browser over WebRTC — with the
keyboard, or in VR through WebXR on a headset.

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

Want to run the service locally or contribute? See
[app/README.md](app/README.md) for the developer documentation,
including setup, tests and database migrations.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

Copyright 2026 Enactic, Inc.

## Code of Conduct

All participation in the OpenArm project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
