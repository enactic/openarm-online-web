# OpenEval infrastructure

Build the environment on AWS.

## Setup

### Install the Tool

Please install [OpenTofu](https://opentofu.org/), as it will be used.

Installation document: https://opentofu.org/docs/intro/install/

### Settings

```bash
cd infra
cp environments/shared/backend.hcl.example environments/shared/backend.hcl
cp environments/staging/backend.hcl.example environments/staging/backend.hcl
cp environments/production/backend.hcl.example environments/production/backend.hcl
# Update `environments/*/backend.hcl` to your environment.
```

Provide variable values via a `terraform.tfvars` file in the environment directory, rather than editing the committed `variables.tf`.
`*.tfvars` files are gitignored, so they stay local to your environment.

See also: https://opentofu.org/docs/language/values/variables/#variable-definitions-tfvars-files

## Usage

### Create AWS resources

First, create the shared resources.

```bash
cd infra/environments/shared
tofu init -backend-config=backend.hcl
tofu plan
tofu apply
```

After that, create the resources for each environment.

Example of execution in the staging environment.
Please move to the `environments/staging` directory and run the command.

```bash
cd infra/environments/staging
tofu init -backend-config=backend.hcl
tofu plan
tofu apply
```

### Set the Secrets Manager values

Initialize the auto-generated secrets (`SECRET_KEY`, `HMAC_KEY` and
`POSTGRES_PASSWORD`). This generates a sufficiently secure random
string for each of them.

Example of running in the staging environment:

```bash
scripts/initialize_secrets.py infra/environments/staging
```

Set the GitHub OAuth secrets (`GITHUB_CLIENT_ID` and
`GITHUB_CLIENT_SECRET`). This prompts for each value.

Example of running in the staging environment:

```bash
scripts/put_github_secrets.py infra/environments/staging
```

Set the S3 access key secrets (`S3_ACCESS_KEY_ID` and
`S3_SECRET_ACCESS_KEY`). This prompts for each value.

Example of running in the staging environment:

```bash
scripts/put_s3_secrets.py infra/environments/staging
```

### Create the database and user for each environment

Create the database and user for the target environment with the RDS admin user.

Example of running in the staging environment:

```bash
scripts/run_ecs_task.py infra/environments/staging scripts/setup_db.py
```

### Database migration

If you omit the command option of `run_ecs_task.py`, the task definition's default command runs, which is the database migration.

Example of running in the staging environment:

```bash
scripts/run_ecs_task.py infra/environments/staging
```

### Deploy the image

The Docker image is built and pushed by GitHub Actions. To deploy the
latest image, force a new deployment of the ECS service. It restarts
the ECS tasks with the latest image.

Example of running in the staging environment:

```bash
scripts/deploy.py infra/environments/staging
```
