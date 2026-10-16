"""خرید: ستون‌های رسید جزئی (received_qty/received_value) و جدول تسهیم هزینهٔ جانبی

Revision ID: 0025
Revises: 0024
"""
from alembic import op
import sqlalchemy as sa

revision = '0025'
down_revision = '0024'
branch_labels = None
depends_on = None


def _add(table, name, col):
    if name not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}:
        op.add_column(table, col)


def upgrade():
    _add('purchase_items', 'received_qty', sa.Column('received_qty', sa.Numeric(18, 3), nullable=False, server_default='0'))
    _add('purchases', 'received_value', sa.Column('received_value', sa.Numeric(18, 2), nullable=False, server_default='0'))
    # خریدهای قبلاً دریافت‌شده: کل مقدار و مبلغ دریافت‌شده فرض می‌شود
    op.execute(sa.text("UPDATE purchase_items SET received_qty = quantity WHERE received_qty = 0 AND purchase_id IN (SELECT id FROM purchases WHERE status = 'received')"))
    op.execute(sa.text("UPDATE purchases SET received_value = total WHERE received_value = 0 AND status = 'received'"))
    if 'cost_allocations' not in set(sa.inspect(op.get_bind()).get_table_names()):
        op.create_table(
            'cost_allocations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('purchase_id', sa.Integer(), sa.ForeignKey('purchases.id'), nullable=False),
            sa.Column('label', sa.String(100), nullable=False),
            sa.Column('basis', sa.String(10), nullable=False, server_default='value'),
            sa.Column('amount', sa.Numeric(18, 2), nullable=False),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_cost_allocations_company_id', 'cost_allocations', ['company_id'])
        op.create_index('ix_cost_allocations_purchase_id', 'cost_allocations', ['purchase_id'])


def downgrade():
    op.drop_table('cost_allocations')
    op.drop_column('purchases', 'received_value')
    op.drop_column('purchase_items', 'received_qty')
