"""مدیر شرکت دیگر مدیر کل نیست: دسترسی‌های مدیریتی سیستم حذف و مدیر به شعبه وصل می‌شود

دسترسی‌های admin/settings/ceo/import از نقش‌های «مدیر شرکت» (فهرست صریح) برداشته می‌شود؛ نقش «*» بدون تغییر.
عضویت مدیرهای بدون شعبه در شرکتی که دقیقاً یک شعبه دارد به همان شعبه وصل می‌شود.

Revision ID: 0030
Revises: 0029
"""
import json
from alembic import op
import sqlalchemy as sa

revision = '0030'
down_revision = '0029'
branch_labels = None
depends_on = None

EXCL = {'admin.read', 'admin.write', 'settings.read', 'settings.write', 'ceo.read', 'ceo.write', 'import.read', 'import.write'}
ROLE_NAMES = ('مدیر شرکت',)


def upgrade():
    bind = op.get_bind()
    names = set(sa.inspect(bind).get_table_names())
    if 'roles' not in names:
        return
    roles = sa.table('roles', sa.column('id', sa.Integer), sa.column('name', sa.String), sa.column('permissions', sa.JSON))
    ids = []
    for rid, perms in bind.execute(sa.select(roles.c.id, roles.c.permissions).where(roles.c.name.in_(ROLE_NAMES))).all():
        if isinstance(perms, str):
            perms = json.loads(perms)
        perms = list(perms or [])
        if '*' in perms:
            continue
        ids.append(rid)
        keep = [p for p in perms if p not in EXCL]
        if keep != perms:
            bind.execute(roles.update().where(roles.c.id == rid).values(permissions=keep))
    if not ids or not {'users', 'memberships', 'branches'} <= names:
        return
    users = sa.table('users', sa.column('id', sa.Integer), sa.column('role_id', sa.Integer))
    ms = sa.table('memberships', sa.column('id', sa.Integer), sa.column('user_id', sa.Integer), sa.column('company_id', sa.Integer), sa.column('branch_id', sa.Integer))
    br = sa.table('branches', sa.column('id', sa.Integer), sa.column('company_id', sa.Integer))
    for mid, cid in bind.execute(sa.select(ms.c.id, ms.c.company_id).where(ms.c.branch_id.is_(None), ms.c.user_id.in_(sa.select(users.c.id).where(users.c.role_id.in_(ids))))).all():
        bs = [b for (b,) in bind.execute(sa.select(br.c.id).where(br.c.company_id == cid)).all()]
        if len(bs) == 1:
            bind.execute(ms.update().where(ms.c.id == mid).values(branch_id=bs[0]))


def downgrade():
    pass
