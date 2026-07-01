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

variable "region" {
  type    = string
  default = "ap-northeast-1"
}

variable "environment" {
  type    = string
  default = "shared"
}

variable "project" {
  type    = string
  default = "openeval"
}

# --- Route53 ---
variable "route53_zone_name" {
  type    = string
  default = "run.example.com"
}

# --- Networking (staging and production) ---
variable "vpc_cidr" {
  type    = string
  default = "10.29.0.0/16"
}

variable "azs" {
  type    = list(string)
  default = ["ap-northeast-1a", "ap-northeast-1c"]
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.29.0.0/24", "10.29.1.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.29.10.0/24", "10.29.11.0/24"]
}
