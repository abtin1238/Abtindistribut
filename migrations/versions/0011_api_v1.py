"""مرحله ۱۶: کلید API، وبهوک خروجی، Idempotency

Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None
TABLES = ['api_keys', 'webhook_endpoints', 'webhook_deliveries', 'idempotency_records']


def upgrade():
    from app.main import Base
    bind = op.get_bind()
    for t in TABLES:
        Base.metadata.tables[t].create(bind=bind, checkfirst=True)


def downgrade():
    for t in reversed(TABLES):
        op.drop_table(t)
