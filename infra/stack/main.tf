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

locals {
  name = "${var.project}-${var.environment}"
}

module "ecr" {
  source               = "../modules/ecr"
  name                 = local.name
  image_tag_mutability = var.image_tag_mutability
}

module "logs" {
  source            = "../modules/logs"
  name              = local.name
  retention_in_days = var.log_retention_days
}

module "secrets" {
  source                  = "../modules/secrets"
  prefix                  = "${var.project}/${var.environment}"
  secret_keys             = var.secret_keys
  recovery_window_in_days = var.secret_recovery_window_days
}

module "iam" {
  source             = "../modules/iam"
  name               = local.name
  log_group_arn      = module.logs.arn
  ecr_repository_arn = module.ecr.repository_arn
  secret_arns        = values(module.secrets.secret_arn_map)
}

module "security_group" {
  source         = "../modules/security_group"
  name           = local.name
  vpc_id         = var.vpc_id
  container_port = var.container_port
}

resource "aws_vpc_security_group_ingress_rule" "db_from_task" {
  security_group_id            = var.rds_security_group_id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = module.security_group.task_id
}
