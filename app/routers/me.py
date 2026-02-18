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


from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import crud
from app.deps import CurrentUser, SessionDep
from app.settings import settings
from app.templates import templates

router = APIRouter(prefix="/me")


@router.get("/", response_class=HTMLResponse)
def me_page(request: Request, user: CurrentUser):
    return templates.TemplateResponse(
        request,
        "me.html",
        {
            "site_name": settings.SITE_NAME,
            "user": user,
        },
    )


@router.get("/logout")
def logout(user: CurrentUser):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token", path="/")
    return response


@router.get("/me/api-keys", response_class=HTMLResponse)
def list_api_keys_page(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
):
    keys = crud.get_api_keys_by_user(session=session, user=user)
    return templates.TemplateResponse(
        request,
        "api_keys.html",
        {
            "site_name": settings.SITE_NAME,
            "user": user,
            "api_keys": keys,
        },
    )


@router.post("/me/api-keys", response_class=HTMLResponse)
def create_api_key_page(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    name: str = Form(),
):
    new_key = crud.create_api_key(
        session=session,
        user_id=user.id,
        name=name,
    )
    keys = crud.get_api_keys_by_user(session=session, user=user)
    return templates.TemplateResponse(
        request,
        "api_keys.html",
        {
            "site_name": settings.SITE_NAME,
            "user": user,
            "api_keys": keys,
            "new_key": new_key,
        },
    )


@router.post("/me/api-keys/{api_key_id}/delete", response_class=HTMLResponse)
def delete_api_key_page(
    api_key_id: int,
    request: Request,
    session: SessionDep,
    user: CurrentUser,
):
    crud.delete_api_key(session=session, api_key_id=api_key_id, user=user)
    keys = crud.get_api_keys_by_user(session=session, user=user)
    return templates.TemplateResponse(
        request,
        "api_keys.html",
        {
            "site_name": settings.SITE_NAME,
            "user": user,
            "api_keys": keys,
        },
    )
