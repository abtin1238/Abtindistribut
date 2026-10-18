"""مرحله ۱۵: اعلان‌ها (ترجیح/صف ارسال/Push)، فیلتر ذخیره‌شده، نسخه‌بندی و ACL فایل، ایندکس pg_trgm

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None

COLS = {
    'users': [('email', sa.String(200), "''"), ('phone', sa.String(30), "''")],
    'notifications': [('event', sa.String(40), "''"), ('entity', sa.String(30), "''"), ('entity_id', sa.Integer(), None), ('dedupe_key', sa.String(100), None)],
    'documents': [('owner_id', sa.Integer(), None), ('size', sa.Integer(), '0'), ('mime', sa.String(100), "''"), ('sha256', sa.String(64), "''"), ('restricted', sa.Boolean(), sa.false()), ('current_version', sa.Integer(), '1'), ('deleted_at', sa.DateTime(), None)],
}
TABLES = ['notification_preferences', 'notification_deliveries', 'push_subscriptions', 'saved_filters', 'file_versions']


def upgrade():
    from app.core import pgtrgm
    from app.main import Base
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table, cols in COLS.items():
        have = {c['name'] for c in insp.get_columns(table)}
        for name, typ, default in cols:
            if name not in have:
                op.add_column(table, sa.Column(name, typ, nullable=default is None, server_default=default if default is None or not isinstance(default, str) else sa.text(default)))
    for t in TABLES:
        Base.metadata.tables[t].create(bind=bind, checkfirst=True)
    names = {i['name'] for i in sa.inspect(bind).get_indexes('notifications')}
    if 'ux_notif_dedupe' not in names:
        op.create_index('ux_notif_dedupe', 'notifications', ['company_id', 'user_id', 'dedupe_key'], unique=True)
    pgtrgm.apply(bind)


def downgrade():
    raise RuntimeError('برای بازگشت، پشتیبان پیش از ارتقا را برگردانید')
