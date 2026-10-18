"""مرحله ۱۵ (تکمیل): جدول قراردادها برای پیوست قرارداد

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    from app.main import Base
    bind = op.get_bind()
    Base.metadata.tables['contracts'].create(bind=bind, checkfirst=True)


def downgrade():
    op.drop_table('contracts')
