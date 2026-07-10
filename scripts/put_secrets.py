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

import json
import subprocess
import sys

import boto3

from app.settings import Settings

if len(sys.argv) != 3:
    raise SystemExit("usage: put_secrets.py <tofu-env-dir> <env-file>")
env_dir = sys.argv[1]
env_file = sys.argv[2]


secret_arns = json.loads(
    subprocess.check_output(
        ["tofu", f"-chdir={env_dir}", "output", "-json", "secret_arn_map"],
        text=True,
    )
)

client = boto3.client("secretsmanager")
settings = Settings(_env_file=env_file)
for key, secret_id in secret_arns.items():
    # Avoid uploading default values when a key isn't present in the provided env file.
    if key not in settings.model_fields_set:
        print(f"skip: [{key}] not set in [{env_file}]")
        continue
    value = getattr(settings, key, None)
    if value is None:
        print(f"skip: [{key}] value is None in [{env_file}]")
        continue
    client.put_secret_value(SecretId=secret_id, SecretString=value)
    print(f"Put {key}")
