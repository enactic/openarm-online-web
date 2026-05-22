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

import pytest

from sqlmodel import Session

from app import crud
from app.models import Task


def test_find_task(session: Session, tasks: list[Task]):
    actual = crud.find_task(session=session, id=tasks[0].id)
    assert actual == tasks[0]


def test_find_task_not_found(session: Session):
    assert crud.find_task(session=session, id=9999) is None
