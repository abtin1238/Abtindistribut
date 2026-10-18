"""Audit: ip و request_id + تغییرناپذیری در سطح دیتابیس (PostgreSQL)

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa

revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    cols = {c['name'] for c in sa.inspect(bind).get_columns('audit_logs')}
    if 'ip' not in cols:
        op.add_column('audit_logs', sa.Column('ip', sa.String(64), nullable=True))
    if 'request_id' not in cols:
        op.add_column('audit_logs', sa.Column('request_id', sa.String(64), nullable=True))
    if bind.dialect.name == 'postgresql':
        op.execute("""CREATE OR REPLACE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END; $$ LANGUAGE plpgsql""")
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_change ON audit_logs")
        op.execute("CREATE TRIGGER audit_logs_no_change BEFORE UPDATE OR DELETE ON audit_logs FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_change ON audit_logs")
        op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable()")
    op.drop_column('audit_logs', 'request_id')
    op.drop_column('audit_logs', 'ip')
