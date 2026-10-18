"""step 12: GPS تحویل و زمان بارگیری

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    have = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('deliveries')}
    if 'gps_status' not in have:
        op.add_column('deliveries', sa.Column('gps_status', sa.String(20), nullable=False, server_default=sa.text("''")))
    if 'distance_m' not in have:
        op.add_column('deliveries', sa.Column('distance_m', sa.Float(), nullable=True))
    if 'loaded_at' not in have:
        op.add_column('deliveries', sa.Column('loaded_at', sa.DateTime(), nullable=True))


def downgrade():
    raise RuntimeError('برای بازگشت، پشتیبان پیش از ارتقا را برگردانید')
