"""امنیت حساب: متادادهٔ نشست (زمان/IP/دستگاه)

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('sessions')}
    for n, t in (('created_at', sa.DateTime()), ('ip', sa.String(64)), ('user_agent', sa.String(300))):
        if n not in cols:
            op.add_column('sessions', sa.Column(n, t, nullable=True))


def downgrade():
    for n in ('user_agent', 'ip', 'created_at'):
        op.drop_column('sessions', n)
