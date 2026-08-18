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

"""Force a new deployment of the ECS service."""

import json
import subprocess
import sys

import boto3

if len(sys.argv) != 2:
    sys.exit("Usage: deploy.py <tofu-env-dir>")
env_dir = sys.argv[1]

outputs = json.loads(
    subprocess.check_output(["tofu", f"-chdir={env_dir}", "output", "-json"], text=True)
)
cluster = outputs["ecs_cluster"]["value"]
service = outputs["ecs_service"]["value"]

ecs = boto3.client("ecs")
ecs.update_service(cluster=cluster, service=service, forceNewDeployment=True)
print(f"Force new deployment: cluster={cluster}, service={service}")
