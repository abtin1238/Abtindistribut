"""baseline: full schema as of accounting/returns/sync release

Revision ID: 0001
Revises:
"""
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Baseline snapshot. checkfirst=True makes it a no-op on databases already created by the
    # legacy ensure_schema(); on those, `alembic stamp 0001` is equivalent.
    # All later schema changes MUST be new revisions (alembic revision --autogenerate).
    from app.main import Base
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError('baseline cannot be downgraded')
