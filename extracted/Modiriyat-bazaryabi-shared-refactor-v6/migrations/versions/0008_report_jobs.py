"""مرحله ۱۴ (بخش دوم): جدول report_jobs (خروجی گزارش در صف پس‌زمینه) + مجوز reports.read برای نقش‌های مدیریتی

Revision ID: 0008
Revises: 0007
"""
import json
import sqlalchemy as sa
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

GRANTS = {'مدیر شرکت': ['reports.read', 'reports.write'], 'مدیر فروش': ['reports.read'], 'حسابدار': ['reports.read']}


def upgrade():
    from app.main import Base
    bind = op.get_bind()
    Base.metadata.tables['report_jobs'].create(bind=bind, checkfirst=True)
    roles = sa.table('roles', sa.column('id', sa.Integer), sa.column('name', sa.String), sa.column('permissions', sa.JSON))
    for rid, name, perms in bind.execute(sa.select(roles.c.id, roles.c.name, roles.c.permissions)).fetchall():
        add = GRANTS.get(name)
        p = json.loads(perms) if isinstance(perms, str) else list(perms or [])
        if add and '*' not in p:
            new = [x for x in add if x not in p]
            if new:
                bind.execute(roles.update().where(roles.c.id == rid).values(permissions=p + new))


def downgrade():
    raise RuntimeError('برای بازگشت، پشتیبان پیش از ارتقا را برگردانید')
