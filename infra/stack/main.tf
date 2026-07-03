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
  secret_arns = concat(
    values(module.secrets.secret_arn_map),
    [var.rds_master_secret_arn],
  )
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

module "certificate" {
  source      = "../modules/certificate"
  domain_name = var.domain_name
  zone_id     = var.route53_zone_id
}

module "alb" {
  source            = "../modules/alb"
  name              = local.name
  vpc_id            = var.vpc_id
  public_subnet_ids = var.public_subnet_ids
  security_group_id = module.security_group.alb_id
  container_port    = var.container_port
  certificate_arn   = module.certificate.arn
}

locals {
  container_environment = [
    { name = "POSTGRES_DB",     value = var.db_name },
    { name = "POSTGRES_PORT",   value = "5432" },
    { name = "POSTGRES_SERVER", value = var.rds_host },
    { name = "POSTGRES_USER",   value = var.db_username },
    { name = "S3_BUCKET_NAME",  value = var.s3_bucket_name },
    { name = "S3_ENDPOINT_URL", value = var.s3_endpoint_url },
  ]
  container_secrets = [
    for key, arn in module.secrets.secret_arn_map : { name = key, value_from = arn }
  ]
}

module "ecs" {
  source             = "../modules/ecs"
  name               = local.name
  image              = "${module.ecr.repository_url}:${var.image_tag}"
  container_port     = var.container_port
  environment        = local.container_environment
  secrets            = local.container_secrets
  run_extra_secrets = [
    { name = "POSTGRES_MASTER_USER",     value_from = "${var.rds_master_secret_arn}:username::" },
    { name = "POSTGRES_MASTER_PASSWORD", value_from = "${var.rds_master_secret_arn}:password::" },
  ]
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [module.security_group.task_id]
  target_group_arn   = module.alb.target_group_arn
  execution_role_arn = module.iam.execution_role_arn
  log_group_name     = module.logs.name
  cpu                = var.task_cpu
  memory             = var.task_memory
  desired_count      = var.desired_count

  depends_on = [module.alb]
}
