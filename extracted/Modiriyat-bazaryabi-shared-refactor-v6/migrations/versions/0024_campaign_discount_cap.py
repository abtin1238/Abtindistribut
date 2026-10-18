"""کمپین فروش + سقف تخفیف دستی نقش

Revision ID: 0024
Revises: 0023
"""
from alembic import op
import sqlalchemy as sa

revision = '0024'
down_revision = '0023'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if 'max_discount_percent' not in {c['name'] for c in sa.inspect(bind).get_columns('roles')}:
        op.add_column('roles', sa.Column('max_discount_percent', sa.Numeric(5, 2), nullable=True))
    if 'campaigns' not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            'campaigns',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('code', sa.String(40), nullable=True),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
            sa.Column('customer_group', sa.String(100), nullable=False, server_default=''),
            sa.Column('discount_percent', sa.Numeric(8, 2), nullable=False),
            sa.Column('min_qty', sa.Numeric(18, 3), nullable=False, server_default='1'),
            sa.Column('starts_at', sa.DateTime(), nullable=True),
            sa.Column('ends_at', sa.DateTime(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index('ix_campaign_active', 'campaigns', ['company_id', 'active'])


def downgrade():
    op.drop_table('campaigns')
    op.drop_column('roles', 'max_discount_percent')
