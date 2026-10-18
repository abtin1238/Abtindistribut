"""خرج چک و برگشت از خرید

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def _add(table, name, col):
    cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
    if name not in cols:
        op.add_column(table, col)


def upgrade():
    _add('checks', 'endorsed_supplier_id', sa.Column('endorsed_supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id'), nullable=True))
    _add('checks', 'endorsed_at', sa.Column('endorsed_at', sa.DateTime(), nullable=True))
    _add('purchase_items', 'returned_qty', sa.Column('returned_qty', sa.Numeric(18, 3), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('purchase_items', 'returned_qty')
    op.drop_column('checks', 'endorsed_at')
    op.drop_column('checks', 'endorsed_supplier_id')
