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
import pytest
from moto import mock_aws

from app.s3 import (
    _client,
    generate_presigned_download_url,
    generate_presigned_upload_url,
)
from app.settings import settings


@pytest.fixture(autouse=True)
def create_bucket():
    with mock_aws():
        _client().create_bucket(Bucket=settings.S3_BUCKET_NAME)
        yield


def test_generate_presigned_upload_url():
    url = generate_presigned_upload_url("path/to/example.rrd")
    assert "path/to/example.rrd" in url


def test_generate_presigned_download_url():
    url = generate_presigned_download_url("path/to/example.rrd")
    assert "path/to/example.rrd" in url
