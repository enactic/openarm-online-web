#!/usr/bin/env python3
#
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

"""Set GitHub OAuth secrets in Secrets Manager."""

import getpass
import json
import subprocess
import sys

import boto3

if len(sys.argv) != 2:
    raise SystemExit("usage: put_github_secrets.py <tofu-env-dir>")
env_dir = sys.argv[1]

secret_arns = json.loads(
    subprocess.check_output(
        ["tofu", f"-chdir={env_dir}", "output", "-json", "secret_arn_map"],
        text=True,
    )
)

values = {
    "GITHUB_CLIENT_ID": input("GITHUB_CLIENT_ID: "),
    "GITHUB_CLIENT_SECRET": getpass.getpass("GITHUB_CLIENT_SECRET: "),
}

client = boto3.client("secretsmanager")
for key, value in values.items():
    if not value:
        raise SystemExit(f"error: [{key}] must not be empty")
    client.put_secret_value(SecretId=secret_arns[key], SecretString=value)
    print(f"Put {key}")
