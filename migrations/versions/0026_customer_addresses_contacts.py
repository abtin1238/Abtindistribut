"""چندآدرس و مخاطبین مشتری

Revision ID: 0026
Revises: 0025
"""
from alembic import op
import sqlalchemy as sa

revision = '0026'
down_revision = '0025'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if 'customer_addresses' not in tables:
        op.create_table(
            'customer_addresses',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
            sa.Column('title', sa.String(100), nullable=False),
            sa.Column('kind', sa.String(20), nullable=False, server_default='delivery'),
            sa.Column('address', sa.Text(), nullable=False, server_default=''),
            sa.Column('region', sa.String(120), nullable=False, server_default=''),
            sa.Column('lat', sa.Float(), nullable=True),
            sa.Column('lng', sa.Float(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_customer_addresses_company_id', 'customer_addresses', ['company_id'])
        op.create_index('ix_customer_addresses_customer_id', 'customer_addresses', ['customer_id'])
        # آدرس فعلی هر مشتری ← آدرس پیش‌فرض (فقط اگر آدرس یا موقعیت داشته باشد)
        op.execute(sa.text(
            "INSERT INTO customer_addresses (company_id, customer_id, title, kind, address, region, lat, lng, is_default, active, created_at) "
            "SELECT company_id, id, 'آدرس اصلی', 'delivery', COALESCE(address, ''), COALESCE(region, ''), lat, lng, :t, :t, CURRENT_TIMESTAMP "
            "FROM customers WHERE (address IS NOT NULL AND address <> '') OR lat IS NOT NULL"
        ).bindparams(sa.bindparam('t', True, type_=sa.Boolean())))
    if 'customer_contacts' not in tables:
        op.create_table(
            'customer_contacts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('role', sa.String(100), nullable=False, server_default=''),
            sa.Column('phone', sa.String(50), nullable=False, server_default=''),
            sa.Column('email', sa.String(200), nullable=False, server_default=''),
            sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_customer_contacts_company_id', 'customer_contacts', ['company_id'])
        op.create_index('ix_customer_contacts_customer_id', 'customer_contacts', ['customer_id'])


def downgrade():
    op.drop_table('customer_contacts')
    op.drop_table('customer_addresses')
