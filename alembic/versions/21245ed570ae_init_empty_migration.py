"""init empty migration

Revision ID: 21245ed570ae
Revises:
Create Date: 2026-11-09 17:32:18.519075

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '21245ed570ae'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
