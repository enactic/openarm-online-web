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

"""Add kind to webrtc_offer

Revision ID: c3d1f0a4b2e7
Revises: f195b6c850a8
Create Date: 2026-08-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3d1f0a4b2e7"
down_revision: Union[str, Sequence[str], None] = "f195b6c850a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "webrtc_offer",
        sa.Column("kind", sa.Text(), nullable=False, server_default="keyboard"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("webrtc_offer", "kind")
