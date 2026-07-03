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

data "terraform_remote_state" "shared" {
  backend = "s3"
  config  = var.shared_state_config
}

module "stack" {
  source      = "../../stack"
  project     = var.project
  environment = var.environment
  domain_name = var.domain_name

  # Security Group
  vpc_id                = data.terraform_remote_state.shared.outputs.vpc_id
  rds_security_group_id = data.terraform_remote_state.shared.outputs.rds_security_group_id

  # Certificate
  route53_zone_id = data.terraform_remote_state.shared.outputs.route53_zone_id

  # ALB
  public_subnet_ids = data.terraform_remote_state.shared.outputs.public_subnet_ids

  # ECS
  private_subnet_ids    = data.terraform_remote_state.shared.outputs.private_subnet_ids
  rds_host              = data.terraform_remote_state.shared.outputs.rds_host
  rds_master_secret_arn = data.terraform_remote_state.shared.outputs.rds_master_secret_arn
  db_name               = "${var.project}_${var.environment}"
  db_username           = "${var.project}_${var.environment}"
  image_tag             = var.image_tag
  s3_endpoint_url       = var.s3_endpoint_url
  s3_bucket_name        = var.s3_bucket_name
}
