"""بارکد کالا + واحدهای فرعی (UnitConversion)

Revision ID: 0023
Revises: 0022
"""
from alembic import op
import sqlalchemy as sa

revision = '0023'
down_revision = '0022'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if 'barcode' not in {c['name'] for c in sa.inspect(bind).get_columns('products')}:
        op.add_column('products', sa.Column('barcode', sa.String(64), nullable=True))
        op.create_index('ix_products_barcode', 'products', ['barcode'])
    if 'unit_conversions' not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            'unit_conversions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('unit', sa.String(30), nullable=False),
            sa.Column('factor', sa.Numeric(18, 4), nullable=False),
            sa.Column('barcode', sa.String(64), nullable=True),
            sa.UniqueConstraint('product_id', 'unit'),
        )
        op.create_index('ix_unit_conversions_company_id', 'unit_conversions', ['company_id'])
        op.create_index('ix_unit_conversions_product_id', 'unit_conversions', ['product_id'])
        op.create_index('ix_unit_conversions_barcode', 'unit_conversions', ['barcode'])


def downgrade():
    op.drop_table('unit_conversions')
    op.drop_index('ix_products_barcode', table_name='products')
    op.drop_column('products', 'barcode')
