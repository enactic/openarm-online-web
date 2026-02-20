#!/usr/bin/bash

# Temporary migration execution until initial development is complete.

set -eux

cd "$(dirname "$0")"

alembic downgrade base

rm -f alembic/versions/*.py

alembic revision --autogenerate -m "wip"
alembic upgrade head
