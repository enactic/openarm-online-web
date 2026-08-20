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

variable "project" {
  type = string
}

variable "environment" {
  type = string
}

# Logs
variable "log_retention_days" {
  type    = number
  default = 30
}

# Secrets
variable "secret_keys" {
  type = set(string)
  default = [
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "SECRET_KEY",
    "HMAC_KEY",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "POSTGRES_PASSWORD",
  ]
}

variable "secret_recovery_window_days" {
  type    = number
  default = 0
}

# Security Group
variable "vpc_id" {
  type = string
}

variable "rds_security_group_id" {
  type = string
}

variable "container_port" {
  type    = number
  default = 8000
}

# Certificate
variable "domain_name" {
  type = string
}

variable "route53_zone_id" {
  type = string
}

# ALB
variable "public_subnet_ids" {
  type = list(string)
}

# ECS
variable "private_subnet_ids" {
  type = list(string)
}

variable "forwarded_allow_ips" {
  type = list(string)
}

variable "rds_host" {
  type = string
}

variable "rds_master_secret_arn" {
  type = string
}

variable "image_name" {
  type = string
  default = "ghcr.io/enactic/openarm-online-web"
}

variable "image_tag" {
  type = string
  default = "main"
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "s3_bucket_name" {
  type = string
}

variable "s3_endpoint_url" {
  type = string
}

variable "task_cpu" {
  type    = number
  default = 256
}

variable "task_memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "submission_allowlist" {
  type = object({
    allowed_orgs  = list(string)
    allowed_users = list(string)
  })
  default = {
    allowed_orgs  = []
    allowed_users = []
  }
}

variable "admin_allowlist" {
  type = object({
    allowed_orgs  = list(string)
    allowed_users = list(string)
  })
  default = {
    allowed_orgs  = []
    allowed_users = []
  }
}
