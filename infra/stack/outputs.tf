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

output "secret_arn_map" {
  value = module.secrets.secret_arn_map
}

output "ecs_cluster" {
  value = module.ecs.cluster_name
}

output "ecs_service" {
  value = module.ecs.service_name
}

output "ecs_run_task_definition" {
  value = module.ecs.run_task_definition_arn
}

output "ecs_run_container_name" {
  value = module.ecs.run_container_name
}

output "ecs_subnet_ids" {
  value = module.ecs.subnet_ids
}

output "ecs_task_security_group_ids" {
  value = module.ecs.security_group_ids
}
