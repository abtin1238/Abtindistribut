"""انبار: بچ/انقضا، انبارگردانی، دلیل حرکت، قفسه، سقف موجودی؛ حسابداری: سلسله‌مراتب حساب، مغایرت‌گیری بانکی

Revision ID: 0020
Revises: 0019
"""
from alembic import op
import sqlalchemy as sa

revision = '0020'
down_revision = '0019'
branch_labels = None
depends_on = None


def _add(table, name, col):
    if name not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}:
        op.add_column(table, col)


def upgrade():
    names = set(sa.inspect(op.get_bind()).get_table_names())
    _add('stock', 'location', sa.Column('location', sa.String(60), nullable=False, server_default=''))
    _add('stock_moves', 'reason', sa.Column('reason', sa.String(200), nullable=False, server_default=''))
    _add('products', 'max_stock', sa.Column('max_stock', sa.Numeric(18, 2), nullable=False, server_default='0'))
    _add('products', 'track_batch', sa.Column('track_batch', sa.Boolean(), nullable=False, server_default=sa.false()))
    _add('purchase_items', 'batch_no', sa.Column('batch_no', sa.String(60), nullable=False, server_default=''))
    _add('purchase_items', 'expiry_date', sa.Column('expiry_date', sa.Date(), nullable=True))
    _add('accounts', 'parent_id', sa.Column('parent_id', sa.Integer(), nullable=True))
    _add('accounts', 'level', sa.Column('level', sa.Integer(), nullable=False, server_default='3'))
    if 'stock_batches' not in names:
        op.create_table(
            'stock_batches',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('batch_no', sa.String(60), nullable=False),
            sa.Column('expiry_date', sa.Date(), nullable=True),
            sa.Column('quantity', sa.Numeric(18, 3), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('warehouse_id', 'product_id', 'batch_no'),
        )
        op.create_index('ix_batch_expiry', 'stock_batches', ['company_id', 'expiry_date'])
    if 'stock_counts' not in names:
        op.create_table(
            'stock_counts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('number', sa.String(80), nullable=False, unique=True),
            sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
            sa.Column('note', sa.Text(), nullable=False, server_default=''),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
        )
    if 'stock_count_lines' not in names:
        op.create_table(
            'stock_count_lines',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('count_id', sa.Integer(), sa.ForeignKey('stock_counts.id'), nullable=False, index=True),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('system_qty', sa.Numeric(18, 3), nullable=False),
            sa.Column('counted_qty', sa.Numeric(18, 3), nullable=True),
            sa.UniqueConstraint('count_id', 'product_id'),
        )
    if 'stock_transfer_batches' not in names:
        op.create_table(
            'stock_transfer_batches',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('transfer_id', sa.Integer(), sa.ForeignKey('stock_transfers.id'), nullable=False, index=True),
            sa.Column('batch_no', sa.String(60), nullable=False),
            sa.Column('expiry_date', sa.Date(), nullable=True),
            sa.Column('quantity', sa.Numeric(18, 3), nullable=False),
        )
    if 'journal_templates' not in names:
        op.create_table(
            'journal_templates',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('name', sa.String(120), nullable=False),
            sa.Column('description', sa.String(300), nullable=False, server_default=''),
            sa.Column('lines', sa.JSON(), nullable=False),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('company_id', 'name'),
        )
    if 'bank_reconciliations' not in names:
        op.create_table(
            'bank_reconciliations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('bank_account_id', sa.Integer(), sa.ForeignKey('bank_accounts.id'), nullable=False, index=True),
            sa.Column('statement_balance', sa.Numeric(18, 2), nullable=False),
            sa.Column('cleared_balance', sa.Numeric(18, 2), nullable=False),
            sa.Column('book_balance', sa.Numeric(18, 2), nullable=False),
            sa.Column('difference', sa.Numeric(18, 2), nullable=False),
            sa.Column('note', sa.String(300), nullable=False, server_default=''),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
    if 'bank_reconciliation_lines' not in names:
        op.create_table(
            'bank_reconciliation_lines',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('reconciliation_id', sa.Integer(), sa.ForeignKey('bank_reconciliations.id'), nullable=False, index=True),
            sa.Column('journal_line_id', sa.Integer(), sa.ForeignKey('journal_lines.id'), nullable=False, unique=True),
        )


def downgrade():
    for t in ('journal_templates', 'stock_transfer_batches', 'bank_reconciliation_lines', 'bank_reconciliations', 'stock_count_lines', 'stock_counts', 'stock_batches'):
        op.drop_table(t)
