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

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi_pagination import add_pagination

from app.deps import (
    CurrentUser,
    CurrentUserOptional,
    NotLoggedIn,
    NotSubmissionAllowed,
)
from app.routers import api, job, leaderboard, login, rollout, submission, task, user
from app.scheduler import timeout_worker
from app.settings import settings
from app.templates import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(timeout_worker())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)
app.include_router(api.router)
app.include_router(job.router)
app.include_router(leaderboard.router)
app.include_router(login.router)
app.include_router(rollout.router)
app.include_router(submission.router)
app.include_router(task.router)
app.include_router(user.router)


@app.exception_handler(NotLoggedIn)
async def requires_login_handler(request: Request, exc: NotLoggedIn):
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(NotSubmissionAllowed)
async def requires_submission_allowed_handler(
    request: Request, exc: NotSubmissionAllowed
):
    return templates.TemplateResponse(
        request,
        "403.html",
        {
            "site_name": settings.SITE_NAME,
            "message": "You are not allowed to register submissions.",
        },
        status_code=403,
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def top_page(request: Request, current_user: CurrentUserOptional):
    return templates.TemplateResponse(
        request,
        "top.html",
        {"site_name": settings.SITE_NAME, "current_user": current_user},
    )


@app.get("/logout", include_in_schema=False)
def logout(current_user: CurrentUser):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token", path="/")
    return response


add_pagination(app)
