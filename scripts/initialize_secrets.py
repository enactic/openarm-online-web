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

"""Initialize auto-generated secrets in Secrets Manager."""

import json
import secrets
import subprocess
import sys

import boto3

if len(sys.argv) != 2:
    raise SystemExit("usage: initialize_secrets.py <tofu-env-dir>")
env_dir = sys.argv[1]

secret_arns = json.loads(
    subprocess.check_output(
        ["tofu", f"-chdir={env_dir}", "output", "-json", "secret_arn_map"],
        text=True,
    )
)

client = boto3.client("secretsmanager")
for key in ["SECRET_KEY", "HMAC_KEY", "POSTGRES_PASSWORD"]:
    client.put_secret_value(
        SecretId=secret_arns[key],
        SecretString=secrets.token_urlsafe(32),
    )
    print(f"Put {key}")
