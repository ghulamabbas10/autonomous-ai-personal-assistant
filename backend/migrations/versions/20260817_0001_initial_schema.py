"""Create the initial assistant schema.

Revision ID: 20260817_0001
Revises: None
Create Date: 2026-08-17
"""

from collections.abc import Sequence

from alembic import op

from app.database import models  # noqa: F401
from app.database.base import Base

revision: str = "20260817_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=False)
    op.execute("DROP EXTENSION IF EXISTS vector")
