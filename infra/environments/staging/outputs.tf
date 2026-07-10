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

# It outputs key + ARN pairs, not the secret values.
output "secret_arn_map" {
  value = module.stack.secret_arn_map
}

output "ecs_cluster" {
  value = module.stack.ecs_cluster
}

output "ecs_run_task_definition" {
  value = module.stack.ecs_run_task_definition
}

output "ecs_run_container_name" {
  value = module.stack.ecs_run_container_name
}

output "ecs_subnet_ids" {
  value = module.stack.ecs_subnet_ids
}

output "ecs_task_security_group_ids" {
  value = module.stack.ecs_task_security_group_ids
}
