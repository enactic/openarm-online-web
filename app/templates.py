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

from markupsafe import Markup
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context


def format_rate(value):
    if value is None:
        return "-"
    return value


def is_active_user(user):
    return user and user.github


@pass_context
def user_format(context, user):
    if not is_active_user(user):
        return "[anonymous]"

    link = context.get("request").url_for("user_page", id=user.id)
    return Markup(f'<a href="{link}">{user.github.name}</a>')


templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

templates.env.globals["format_rate"] = format_rate
templates.env.globals["is_active_user"] = is_active_user
templates.env.globals["user_format"] = user_format
