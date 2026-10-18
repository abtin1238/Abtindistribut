"""دورهٔ مالی و قفل دوره

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade():
    from app.main import Base
    Base.metadata.tables['fiscal_periods'].create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table('fiscal_periods')
