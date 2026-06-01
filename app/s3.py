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

import boto3
from botocore.config import Config

from app.settings import settings


def _client():
    config = Config(
        signature_version="s3v4",
    )
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        config=config,
        region_name=settings.S3_REGION,
    )


def _generate_presigned_url(action: str, key: str, expires_in: int = 300) -> str:
    return _client().generate_presigned_url(
        action,
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )


def generate_presigned_download_url(key: str, expires_in: int = 300) -> str:
    return _generate_presigned_url("get_object", key, expires_in)


def generate_presigned_upload_url(key: str, expires_in: int = 300) -> str:
    return _generate_presigned_url("put_object", key, expires_in)
