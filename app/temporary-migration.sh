#!/usr/bin/bash

# Temporary migration execution until initial development is complete.

set -eux

cd "$(dirname "$0")"

alembic downgrade base

rm -f alembic/versions/*.py

alembic revision --autogenerate -m "wip"
alembic upgrade head

# Insert test dummy data.
# todo: How to add tasks in production.
python3 << CODE
from sqlmodel import Session

from app.db import engine
from app.models import Task

with Session(engine) as session:
  session.add(Task(name="task1", prompt="dummy1", reset_docker_tag="reset tag1"))
  session.add(Task(name="task2", prompt="dummy2", reset_docker_tag="reset tag2"))
  session.add(Task(name="task3", prompt="dummy3", reset_docker_tag="reset tag3"))
  session.commit()
CODE
