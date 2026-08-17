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

variable "name" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "log_group_name" {
  type = string
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "execution_role_arn" {
  type = string
}

variable "image" {
  type = string
}

variable "environment" {
  type = list(object({ name = string, value = string }))
}

variable "secrets" {
  type = list(object({ name = string, value_from = string }))
}

variable "run_extra_secrets" {
  type = list(object({ name = string, value_from = string }))
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "target_group_arn" {
  type = string
}

variable "run_command" {
  type    = list(string)
  default = ["alembic", "-c", "/openarm-online/app/alembic.ini", "upgrade", "head"]
}
