"""ناحیه‌های جغرافیایی (Geofence) و رویدادهای ورود/خروج

Revision ID: 0028
Revises: 0027
"""
from alembic import op
import sqlalchemy as sa

revision = '0028'
down_revision = '0027'
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'geofences' not in tables:
        op.create_table(
            'geofences',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('kind', sa.String(20), nullable=False, server_default='area'),
            sa.Column('lat', sa.Float(), nullable=False),
            sa.Column('lng', sa.Float(), nullable=False),
            sa.Column('radius_m', sa.Float(), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('company_id', 'name'),
        )
        op.create_index('ix_geofences_company_id', 'geofences', ['company_id'])
    if 'geofence_events' not in tables:
        op.create_table(
            'geofence_events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('geofence_id', sa.Integer(), sa.ForeignKey('geofences.id'), nullable=False),
            sa.Column('kind', sa.String(10), nullable=False),
            sa.Column('at', sa.DateTime(), nullable=False),
            sa.Column('lat', sa.Float(), nullable=False),
            sa.Column('lng', sa.Float(), nullable=False),
            sa.UniqueConstraint('company_id', 'user_id', 'geofence_id', 'kind', 'at'),
        )
        op.create_index('ix_geofence_events_company_id', 'geofence_events', ['company_id'])
        op.create_index('ix_geofence_events_geofence_id', 'geofence_events', ['geofence_id'])
        op.create_index('ix_gfe_user_time', 'geofence_events', ['company_id', 'user_id', 'at'])


def downgrade():
    op.drop_table('geofence_events')
    op.drop_table('geofences')
