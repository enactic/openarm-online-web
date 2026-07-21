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

import httpx
import secrets

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import crud
from app.deps import SessionDep
from app.settings import settings
from app.templates import templates
from app.security import create_access_token

router = APIRouter(prefix="/login", include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "site_name": settings.SITE_NAME,
        },
    )


@router.get("/github")
def login_github(request: Request):
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "scope": "read:user read:org",
        "state": state,
    }
    response = RedirectResponse(
        url=f"{settings.GITHUB_AUTHORIZE_URL}?{urlencode(params)}",
        status_code=302,
    )
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=300,  # sec
    )
    return response


@router.get("/github/callback")
def login_github_callback(
    request: Request,
    session: SessionDep,
    code: str,
    state: str,
):
    saved_state = request.cookies.get("oauth_state")
    if not saved_state or saved_state != state:
        # todo: error message
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "site_name": settings.SITE_NAME,
            },
        )
    # Exchange code for access token
    token_response = httpx.post(
        settings.GITHUB_TOKEN_URL,
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )
    token_data = token_response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        # todo: error message
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "site_name": settings.SITE_NAME,
            },
        )
    # Fetch GitHub user info
    github_user_response = httpx.get(
        settings.GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    github_user = github_user_response.json()
    github_id = github_user["id"]
    login_name = github_user.get("login")
    name = github_user.get("name")
    # Fetch GitHub user organizations info
    organizations = None
    try:
        github_orgs_response = httpx.get(
            settings.GITHUB_USER_URL + "/orgs",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            params={"per_page": 100},
            timeout=10.0,
        )
        github_orgs_response.raise_for_status()
        orgs_payload = github_orgs_response.json()
        if isinstance(orgs_payload, list):
            organizations = [
                {"github_id": org["id"], "login": org["login"]}
                for org in orgs_payload
                if "id" in org and "login" in org
            ]
    except (httpx.HTTPError, ValueError):
        organizations = None
    # Create user
    user = crud.find_user_by_github_id(session=session, github_id=github_id)
    if user:
        crud.update_user_github(
            session=session,
            user=user,
            login_name=login_name,
            name=name,
            organizations=organizations,
        )
    else:
        user = crud.create_user(
            session=session,
            github_id=github_id,
            login_name=login_name,
            name=name,
            organizations=organizations,
        )
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="oauth_state", path="/")
    access_token = create_access_token(str(user.id))
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response
