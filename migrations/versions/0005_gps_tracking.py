"""مرحله ۱۳ (نقشه و GPS): جدول gps_points + مجوزهای gps برای نقش‌های الگو

Revision ID: 0005
Revises: 0004
"""
import json
import sqlalchemy as sa
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

# نقش‌های الگو فقط یک‌بار مجوز می‌گیرند؛ نقش‌های سفارشی دست‌نخورده می‌مانند.
GRANTS = {'مدیر شرکت': ['gps.read', 'gps.write', 'gps.record'], 'مدیر فروش': ['gps.read'], 'بازاریاب': ['gps.record'], 'مأمور پخش': ['gps.record']}


def upgrade():
    from app.main import Base
    bind = op.get_bind()
    Base.metadata.tables['gps_points'].create(bind=bind, checkfirst=True)
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
