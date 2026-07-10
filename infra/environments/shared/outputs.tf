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

output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "public_subnet_cidrs" {
  value = aws_subnet.public[*].cidr_block
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "rds_security_group_id" {
  value = aws_security_group.db.id
}

output "route53_zone_id" {
  value = aws_route53_zone.public.zone_id
}

output "rds_host" {
  value = aws_db_instance.db.address
}

output "rds_master_secret_arn" {
  value = aws_db_instance.db.master_user_secret[0].secret_arn
}
