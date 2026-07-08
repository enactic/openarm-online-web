#!/usr/bin/env python3
#
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

import json
import os
import sys

from pathlib import Path

from sqlmodel import Session

from app.db import engine
from app.crud import create_tasks

if len(sys.argv) == 2:
    task_data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
elif len(sys.argv) == 1 and (raw_task_data := os.getenv("TASK_DATA")):
    task_data = json.loads(raw_task_data)
else:
    print("Usage: create_tasks.py <task.json> (or set TASK_DATA to the JSON string)")
    sys.exit(1)

with Session(engine) as session:
    with session.begin():
        create_tasks(session=session, data=task_data)
