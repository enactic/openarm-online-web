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

if len(sys.argv) < 2:
    sys.exit("Usage: run_ecs_task.py <tofu-env-dir> [command ...]")
env_dir = sys.argv[1]
command = sys.argv[2:]

outputs = json.loads(
    subprocess.check_output(["tofu", f"-chdir={env_dir}", "output", "-json"], text=True)
)


def value(name):
    return outputs[name]["value"]


cluster = value("ecs_cluster")
ecs = boto3.client("ecs")

run_args = {
    "cluster": cluster,
    "taskDefinition": value("ecs_run_task_definition"),
    "launchType": "FARGATE",
    "networkConfiguration": {
        "awsvpcConfiguration": {
            "subnets": value("ecs_subnet_ids"),
            "securityGroups": value("ecs_task_security_group_ids"),
            "assignPublicIp": "DISABLED",
        }
    },
}
if command:
    run_args["overrides"] = {
        "containerOverrides": [
            {"name": value("ecs_run_container_name"), "command": command}
        ]
    }

response = ecs.run_task(**run_args)
if response["failures"]:
    sys.exit(f"Failed to start task: {response['failures']}")
if not response["tasks"]:
    sys.exit("Failed to start task: no tasks returned")

task_arn = response["tasks"][0]["taskArn"]
print(f"Start task: {task_arn}")

ecs.get_waiter("tasks_stopped").wait(
    cluster=cluster,
    tasks=[task_arn],
    WaiterConfig={"Delay": 10, "MaxAttempts": 60},  # 10 min
)

task = ecs.describe_tasks(cluster=cluster, tasks=[task_arn])["tasks"][0]
containers = task.get("containers")
exit_code = containers[0].get("exitCode") if containers else None
print(f"End exitCode={exit_code}, reason={task.get('stoppedReason')}")

if exit_code is None:
    sys.exit(1)
else:
    sys.exit(exit_code)
