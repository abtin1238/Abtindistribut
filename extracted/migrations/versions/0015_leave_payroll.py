"""مرخصی و حقوق و دستمزد

Revision ID: 0015
Revises: 0014
"""
from alembic import op

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None
TABLES = ['leave_requests', 'payroll_runs', 'payroll_lines']


def upgrade():
    from app.main import Base
    bind = op.get_bind()
    for t in TABLES:
        Base.metadata.tables[t].create(bind=bind, checkfirst=True)


def downgrade():
    for t in reversed(TABLES):
        op.drop_table(t)
