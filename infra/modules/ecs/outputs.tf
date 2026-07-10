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

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "run_task_definition_arn" {
  value = aws_ecs_task_definition.run.arn
}

output "run_container_name" {
  value = local.run_container_name
}

output "subnet_ids" {
  value = var.subnet_ids
}

output "security_group_ids" {
  value = var.security_group_ids
}
