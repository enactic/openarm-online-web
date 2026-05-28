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

import asyncio
import logging

from sqlmodel import Session

from app import crud, job_queue
from app.db import engine
from app.settings import settings

logger = logging.getLogger(__name__)


def _timeout_claimed_jobs_main(session: Session):
    expired_claims = job_queue.find_all_expired_claimed_executions(session=session)
    reason = f"[server] Job timed out after {settings.CLAIM_TIMEOUT} minutes"
    for claimed in expired_claims:
        try:
            job = job_queue.fail_job(
                session=session,
                job_id=claimed.job_id,
                reason=reason,
                api_key_id=claimed.api_key_id,
            )
            crud.create_job_failure(
                session=session,
                submission_id=job.submission_id,
                reason=reason,
            )
        except (ValueError, job_queue.JobNotFoundError):
            # Ignore if the job was already processed by the API.
            pass


def timeout_claimed_jobs():
    with Session(engine) as session:
        with session.begin():
            _timeout_claimed_jobs_main(session)


async def timeout_worker():
    while True:
        await asyncio.sleep(settings.CLAIM_TIMEOUT_CHECK_INTERVAL * 60)
        try:
            timeout_claimed_jobs()
        except Exception:
            logger.exception("Error in timeout_claimed_jobs()")
