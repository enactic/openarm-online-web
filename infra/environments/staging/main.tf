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
}
