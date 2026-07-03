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

# Connects as the RDS managed master (admin) user to create the per-environment
# (staging, production) database and role on the shared instance.

import os

import psycopg
from psycopg import sql

from app.settings import settings

role = settings.POSTGRES_USER
role_password = settings.POSTGRES_PASSWORD
db_name = settings.POSTGRES_DB


with psycopg.connect(
    host=settings.POSTGRES_SERVER,
    port=settings.POSTGRES_PORT,
    user=os.environ["POSTGRES_MASTER_USER"],
    password=os.environ["POSTGRES_MASTER_PASSWORD"],
    dbname="postgres",
    autocommit=True,
) as conn, conn.cursor() as cursor:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
    if cursor.fetchone():
        cursor.execute(
            sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                sql.Identifier(role),
                sql.Literal(role_password),
            )
        )
    else:
        cursor.execute(
            sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                sql.Identifier(role),
                sql.Literal(role_password),
            )
        )

    cursor.execute(sql.SQL("GRANT {} TO CURRENT_USER").format(sql.Identifier(role)))
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if not cursor.fetchone():
        cursor.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(db_name),
                sql.Identifier(role),
            )
        )
        cursor.execute(
            sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(
                sql.Identifier(db_name)
            )
        )
        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(db_name),
                sql.Identifier(role),
            )
        )

with psycopg.connect(
    host=settings.POSTGRES_SERVER,
    port=settings.POSTGRES_PORT,
    user=os.environ["POSTGRES_MASTER_USER"],
    password=os.environ["POSTGRES_MASTER_PASSWORD"],
    dbname=db_name,
    autocommit=True,
) as conn, conn.cursor() as cursor:
    cursor.execute(
        sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(sql.Identifier(role))
    )
