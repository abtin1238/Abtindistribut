"""step 13-fix: Lead.reminded_on برای یادآوری خودکار

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    if 'reminded_on' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('leads')}:
        op.add_column('leads', sa.Column('reminded_on', sa.Date(), nullable=True))


def downgrade():
    raise RuntimeError('برای بازگشت، پشتیبان پیش از ارتقا را برگردانید')
