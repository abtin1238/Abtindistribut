"""دسترسی اختصاصی داشبورد مدیرعامل (ceo.read/ceo.write)

قبلاً /api/ceo با reports.read + data.all باز می‌شد و نقش «حسابدار» هم به آن دسترسی داشت.
نقش‌های «مدیر شرکت» که فهرست صریح دسترسی دارند، دسترسی جدید را می‌گیرند؛ نقش‌های «*» بدون تغییر ادامه می‌دهند.

Revision ID: 0029
Revises: 0028
"""
import json
from alembic import op
import sqlalchemy as sa

revision = '0029'
down_revision = '0028'
branch_labels = None
depends_on = None

NEW = ('ceo.read', 'ceo.write')
ROLE_NAMES = ('مدیر شرکت',)


def _roles():
    return sa.table('roles', sa.column('id', sa.Integer), sa.column('name', sa.String), sa.column('permissions', sa.JSON))


def upgrade():
    bind = op.get_bind()
    if 'roles' not in set(sa.inspect(bind).get_table_names()):
        return
    t = _roles()
    for rid, perms in bind.execute(sa.select(t.c.id, t.c.permissions).where(t.c.name.in_(ROLE_NAMES))).all():
        if isinstance(perms, str):
            perms = json.loads(perms)
        perms = list(perms or [])
        if '*' in perms or all(p in perms for p in NEW):
            continue
        bind.execute(t.update().where(t.c.id == rid).values(permissions=perms + [p for p in NEW if p not in perms]))


def downgrade():
    bind = op.get_bind()
    if 'roles' not in set(sa.inspect(bind).get_table_names()):
        return
    t = _roles()
    for rid, perms in bind.execute(sa.select(t.c.id, t.c.permissions).where(t.c.name.in_(ROLE_NAMES))).all():
        if isinstance(perms, str):
            perms = json.loads(perms)
        bind.execute(t.update().where(t.c.id == rid).values(permissions=[p for p in (perms or []) if p not in NEW]))
