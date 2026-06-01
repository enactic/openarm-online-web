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

import pytest
import requests

from app.s3 import (
    _client,
    generate_presigned_download_url,
    generate_presigned_upload_url,
)
from app.settings import settings


@pytest.fixture(autouse=True)
def create_bucket():
    client = _client()
    client.create_bucket(Bucket=settings.S3_BUCKET_NAME)

    yield

    objects = client.list_objects_v2(Bucket=settings.S3_BUCKET_NAME).get("Contents", [])
    for obj in objects:
        client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=obj["Key"])
    client.delete_bucket(Bucket=settings.S3_BUCKET_NAME)


def test_generate_presigned_upload_url():
    url = generate_presigned_upload_url("path/to/example")
    response = requests.put(url, data=b"test content", timeout=5)
    assert response.status_code == 200

    assert (
        _client()
        .get_object(Bucket=settings.S3_BUCKET_NAME, Key="path/to/example")["Body"]
        .read()
        == b"test content"
    )


def test_generate_presigned_upload_url_invalid_method():
    _client().put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key="path/to/example",
        Body=b"test content",
    )
    url = generate_presigned_upload_url("path/to/example")
    response = requests.get(url, data=b"test content", timeout=5)
    assert response.status_code == 403


def test_generate_presigned_download_url():
    _client().put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key="path/to/example",
        Body=b"test content",
    )
    url = generate_presigned_download_url("path/to/example")
    response = requests.get(url, timeout=5)
    assert response.status_code == 200
    assert response.content == b"test content"


def test_generate_presigned_download_url_invalid_method():
    url = generate_presigned_download_url("path/to/example")
    response = requests.put(url, data=b"test content", timeout=5)
    assert response.status_code == 403
