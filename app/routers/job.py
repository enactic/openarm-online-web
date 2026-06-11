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

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import crud, job_queue
from app.deps import CurrentUser, SessionDep
from app.responses import not_found

router = APIRouter(prefix="/jobs", include_in_schema=False)


@router.post("/{id}/retry", response_class=HTMLResponse)
def retry_job_page(
    id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
):
    job = job_queue.find_job(session=session, id=id)
    if job is None:
        return not_found(request, current_user)
    submission = crud.find_submission(session=session, id=job.submission_id)
    if submission is None or submission.user_id != current_user.id:
        return not_found(request, current_user)
    try:
        job_queue.retry_job(session=session, job_id=job.id)
    except ValueError:
        # Job is no longer in a failed state (e.g. already retried)
        pass
    return RedirectResponse(
        url=request.url_for("list_rollouts_page").include_query_params(
            submission_id=job.submission_id
        ),
        status_code=303,
    )
