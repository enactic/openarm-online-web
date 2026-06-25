# OpenEval infrastructure

Build the environment on AWS.

## Setup

### Install the Tool

Please install [OpenTofu](https://opentofu.org/), as it will be used.

Installation document: https://opentofu.org/docs/intro/install/

### Settings

```bash
cd infra
cp environments/staging/backend.hcl.example environments/staging/backend.hcl
cp environments/production/backend.hcl.example environments/production/backend.hcl
# Update `environments/*/backend.hcl` to your environment.
```

Provide variable values via a `terraform.tfvars` file in the environment directory, rather than editing the committed `variables.tf`.
`*.tfvars` files are gitignored, so they stay local to your environment.

See also: https://opentofu.org/docs/language/values/variables/#variable-definitions-tfvars-files

## Usage

Example of execution in the staging environment.
Please move to the `environments/staging` directory and run the command.

```bash
cd infra/environments/staging
tofu init -backend-config=backend.hcl
tofu plan
tofu apply
```
