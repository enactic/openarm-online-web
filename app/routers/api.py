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

from app import crud
from app.deps import CurrentApiKey, SessionDep
from app.schemas import ApiRequestJobResult, ApiResponseJob, ApiResponseTask

router = APIRouter(prefix="/api/v1")

# todo: filter


@router.get("/tasks", response_model=list[ApiResponseTask])
def api_get_tasks(session: SessionDep, api_key: CurrentApiKey):
    return crud.get_tasks(session=session)


@router.get("/jobs", response_model=list[ApiResponseJob])
def api_get_jobs(session: SessionDep, api_key: CurrentApiKey):
    return crud.get_jobs(session=session)


@router.post("/job_results")
def api_post_job_results(
    request: ApiRequestJobResult, session: SessionDep, api_key: CurrentApiKey
):
    try:
        crud.create_job_result(session=session, request=request)
        return {"status": True}
    except Exception as err:
        # todo error log
        print(err)
        return {"stauts": False}
