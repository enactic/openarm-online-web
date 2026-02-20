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

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.deps import CurrentUser, CurrentUserOptional, NotLoggedIn
from app.routers import login, task
from app.settings import settings
from app.templates import templates

app = FastAPI()
app.include_router(login.router)
app.include_router(task.router)


@app.exception_handler(NotLoggedIn)
async def requires_login_handler(request: Request, exc: NotLoggedIn):
    return RedirectResponse(url="/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def top_page(request: Request, user: CurrentUserOptional):
    return templates.TemplateResponse(
        request,
        "top.html",
        {"site_name": settings.SITE_NAME, "user": user},
    )


@app.get("/logout")
def logout(user: CurrentUser):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token", path="/")
    return response


@app.get("/me", response_class=HTMLResponse)
def me_page(request: Request, user: CurrentUser):
    return templates.TemplateResponse(
        request,
        "me.html",
        {
            "site_name": settings.SITE_NAME,
            "user": user,
        },
    )
