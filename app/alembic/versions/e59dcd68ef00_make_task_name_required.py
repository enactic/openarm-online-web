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

"""Make task.name required

Revision ID: e59dcd68ef00
Revises: 9a0055488879
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision: str = "e59dcd68ef00"
down_revision: Union[str, Sequence[str], None] = "9a0055488879"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Name existing nameless tasks so that the NOT NULL constraint can
    # be added.
    op.execute("UPDATE task SET name = 'task-' || id WHERE name IS NULL")
    op.alter_column(
        "task",
        "name",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=255),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "task",
        "name",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=255),
        nullable=True,
    )
