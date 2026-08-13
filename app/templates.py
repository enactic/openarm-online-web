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

import math
from pathlib import Path
from urllib.parse import quote

from fastapi.templating import Jinja2Templates

from jinja2 import pass_context

from app.deps import is_admin
from app.s3 import generate_presigned_download_url
from app.settings import settings


def format_rate(value):
    if value is None:
        return "-"
    return value


def is_active_user(user):
    return user and user.github


def rerun_viewer_url(s3_key):
    download_url = generate_presigned_download_url(s3_key, expires_in=600)
    return f"{settings.RERUN_VIEWER_URL}?url={quote(download_url, safe='')}"


def total_pages(pagenator):
    return math.ceil(pagenator.total / pagenator.size)


@pass_context
def update_query_params(context, **kwargs):
    request = context.get("request")
    params = dict(request.query_params) | kwargs
    return request.url.include_query_params(**params)


templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

templates.env.globals["format_rate"] = format_rate
templates.env.globals["is_active_user"] = is_active_user
templates.env.globals["is_admin"] = is_admin
templates.env.globals["revision"] = settings.REVISION
templates.env.globals["rerun_viewer_url"] = rerun_viewer_url
templates.env.globals["total_pages"] = total_pages
templates.env.globals["update_query_params"] = update_query_params
