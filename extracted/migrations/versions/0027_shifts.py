"""شیفت کاری و تخصیص به کارمند

Revision ID: 0027
Revises: 0026
"""
from alembic import op
import sqlalchemy as sa

revision = '0027'
down_revision = '0026'
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'shifts' not in tables:
        op.create_table(
            'shifts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('start_time', sa.Time(), nullable=False),
            sa.Column('end_time', sa.Time(), nullable=False),
            sa.Column('grace_minutes', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.UniqueConstraint('company_id', 'name'),
        )
        op.create_index('ix_shifts_company_id', 'shifts', ['company_id'])
    if 'employee_shifts' not in tables:
        op.create_table(
            'employee_shifts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, unique=True),
            sa.Column('shift_id', sa.Integer(), sa.ForeignKey('shifts.id'), nullable=False),
        )
        op.create_index('ix_employee_shifts_company_id', 'employee_shifts', ['company_id'])


def downgrade():
    op.drop_table('employee_shifts')
    op.drop_table('shifts')
