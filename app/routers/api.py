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

from fastapi import APIRouter

from app.deps import ApiUser

router = APIRouter(prefix="/api/v1")


@router.get("/me")
def api_me(user: ApiUser):
    return {
        "id": user.id,
        "login_name": user.github.login_name if user.github else None,
        "name": user.github.name if user.github else None,
    }
