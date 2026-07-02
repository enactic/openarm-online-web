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

resource "aws_secretsmanager_secret" "this" {
  for_each                = var.secret_keys
  name                    = "${var.prefix}/${each.key}"
  recovery_window_in_days = var.recovery_window_in_days
}

# Do not set the actual value in OpenTofu so that no value is stored in `state`.
# You need to configure this using the AWS CLI or the AWS Management Console.
