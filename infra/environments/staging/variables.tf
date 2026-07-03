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
  default = "staging"
}

variable "project" {
  type    = string
  default = "openeval"
}

variable "domain_name" {
  type    = string
  default = "dev.run.example.com"
}

variable "shared_state_config" {
  type = object({
    bucket = string
    key    = string
    region = string
  })
  default = {
    bucket = "tfstate"
    key    = "shared/terraform.tfstate"
    region = "ap-northeast-1"
  }
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "s3_endpoint_url" {
  type    = string
  default = "https://s3"
}

variable "s3_bucket_name" {
  type    = string
  default = "openeval"
}
