"""انتقال چندقلمی بین انبارها: جدول اقلام + product_id روی بچ‌های در راه؛ انتقال‌های قدیمی به یک ردیف منتقل می‌شوند

Revision ID: 0022
Revises: 0021
"""
from alembic import op
import sqlalchemy as sa

revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    names = set(sa.inspect(bind).get_table_names())
    if 'stock_transfer_items' not in names:
        op.create_table(
            'stock_transfer_items',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('transfer_id', sa.Integer(), sa.ForeignKey('stock_transfers.id'), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('quantity', sa.Numeric(18, 3), nullable=False),
            sa.UniqueConstraint('transfer_id', 'product_id'),
        )
        op.create_index('ix_stock_transfer_items_transfer_id', 'stock_transfer_items', ['transfer_id'])
    cols = {c['name'] for c in sa.inspect(bind).get_columns('stock_transfer_batches')}
    if 'product_id' not in cols:
        op.add_column('stock_transfer_batches', sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True))
    # انتقال‌های قدیمی (تک‌قلمی) → یک ردیف قلم؛ بچ‌های قدیمی → product_id سرتیتر
    op.execute(sa.text('INSERT INTO stock_transfer_items (transfer_id, product_id, quantity) '
                       'SELECT t.id, t.product_id, t.quantity FROM stock_transfers t '
                       'WHERE NOT EXISTS (SELECT 1 FROM stock_transfer_items i WHERE i.transfer_id = t.id)'))
    op.execute(sa.text('UPDATE stock_transfer_batches SET product_id = '
                       '(SELECT t.product_id FROM stock_transfers t WHERE t.id = stock_transfer_batches.transfer_id) '
                       'WHERE product_id IS NULL'))


def downgrade():
    op.drop_column('stock_transfer_batches', 'product_id')
    op.drop_index('ix_stock_transfer_items_transfer_id', table_name='stock_transfer_items')
    op.drop_table('stock_transfer_items')
