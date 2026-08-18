#!/usr/bin/env bash
#
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

set -euo pipefail

cd "$(dirname "$0")/.."

if [ $# -ne 3 ]; then
  echo "Usage: $0 ENVIRONMENT AWS_ACCOUNT_ID REGION"
  echo " e.g.: $0 production 123456789012 ap-northeast-1"
  exit 1
fi

environment=$1
aws_account_id=$2
region=$3

registry="${aws_account_id}.dkr.ecr.${region}.amazonaws.com"
auth_json=${XDG_RUNTIME_DIR}/containers/auth.json
if [ ! -f "${auth_json}" ] || \
   [ "$(jq --arg registry "${registry}" '.auths[$registry].auth' "${auth_json}")" = "null" ]; then
  aws ecr get-login-password --region "${region}" | \
    podman login --username AWS --password-stdin "${registry}"
fi

tag="${registry}/openarm-online-${environment}:latest"
podman image build \
  --build-arg "REVISION=$(git rev-parse --short HEAD)" \
  --file "app/${environment}.Containerfile" \
  --tag "${tag}" \
  .
podman image push "${tag}"

aws ecs update-service \
  --cluster "openarm-online-${environment}" \
  --service "openarm-online-${environment}" \
  --force-new-deployment
