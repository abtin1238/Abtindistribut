"""حساب بانکی، دسته‌چک و تاریخچهٔ چک

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def _add(table, name, col):
    cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
    if name not in cols:
        op.add_column(table, col)


def upgrade():
    names = set(sa.inspect(op.get_bind()).get_table_names())
    if 'bank_accounts' not in names:
        op.create_table(
            'bank_accounts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('bank_name', sa.String(120), nullable=False, server_default=''),
            sa.Column('branch', sa.String(120), nullable=False, server_default=''),
            sa.Column('account_number', sa.String(60), nullable=False, server_default=''),
            sa.Column('iban', sa.String(40), nullable=False, server_default=''),
            sa.Column('holder', sa.String(200), nullable=False, server_default=''),
            sa.Column('opening_balance', sa.Numeric(18, 2), nullable=False, server_default='0'),
            sa.Column('ledger_code', sa.String(20), nullable=False, server_default=''),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('company_id', 'name'),
        )
    if 'chequebooks' not in names:
        op.create_table(
            'chequebooks',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('bank_account_id', sa.Integer(), sa.ForeignKey('bank_accounts.id'), nullable=False, index=True),
            sa.Column('series', sa.String(40), nullable=False, server_default=''),
            sa.Column('start_no', sa.Integer(), nullable=False),
            sa.Column('end_no', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
    if 'check_history' not in names:
        op.create_table(
            'check_history',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('check_id', sa.Integer(), sa.ForeignKey('checks.id'), nullable=False, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('action', sa.String(30), nullable=False),
            sa.Column('from_status', sa.String(30), nullable=False, server_default=''),
            sa.Column('to_status', sa.String(30), nullable=False, server_default=''),
            sa.Column('note', sa.String(300), nullable=False, server_default=''),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
    _add('checks', 'bank_account_id', sa.Column('bank_account_id', sa.Integer(), sa.ForeignKey('bank_accounts.id'), nullable=True))
    _add('checks', 'chequebook_id', sa.Column('chequebook_id', sa.Integer(), sa.ForeignKey('chequebooks.id'), nullable=True))
    _add('payments', 'bank_account_id', sa.Column('bank_account_id', sa.Integer(), sa.ForeignKey('bank_accounts.id'), nullable=True))


def downgrade():
    op.drop_column('payments', 'bank_account_id')
    op.drop_column('checks', 'chequebook_id')
    op.drop_column('checks', 'bank_account_id')
    op.drop_table('check_history')
    op.drop_table('chequebooks')
    op.drop_table('bank_accounts')
