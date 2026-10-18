"""قیمت پله‌ای: حداقل تعداد در قانون قیمت

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade():
    cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('price_rules')}
    if 'min_qty' not in cols:
        op.add_column('price_rules', sa.Column('min_qty', sa.Numeric(18, 3), nullable=False, server_default='1'))


def downgrade():
    op.drop_column('price_rules', 'min_qty')
