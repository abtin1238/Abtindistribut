"""step 11: سرنخ/وظیفه/پیشنهاد/تارگت، نتیجه و GPS ویزیت

Revision ID: 0002
Revises: 0001
"""
import json
import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

LEAD_COLS = [('source', sa.String(50), "''"), ('value', sa.Numeric(18, 2), '0'), ('lost_reason', sa.String(200), "''"), ('created_at', sa.DateTime(), None), ('closed_at', sa.DateTime(), None)]
VISIT_COLS = [('result', sa.String(30), "''"), ('no_order_reason', sa.String(200), "''"), ('distance_m', sa.Float(), None), ('gps_status', sa.String(20), "''")]
NEW_TABLES = ['lead_activities', 'tasks', 'proposals', 'proposal_lines', 'targets']
TEMPLATE_ROLES = ('مدیر فروش', 'فروشنده', 'بازاریاب')


def _add(bind, table, cols):
    have = {c['name'] for c in sa.inspect(bind).get_columns(table)}
    for name, typ, default in cols:
        if name not in have:
            op.add_column(table, sa.Column(name, typ, nullable=default is None, server_default=sa.text(default) if default is not None else None))


def upgrade():
    from app.main import Base
    bind = op.get_bind()
    insp = sa.inspect(bind)
    _add(bind, 'leads', LEAD_COLS)
    _add(bind, 'visits', VISIT_COLS)
    if 'order_id' not in {c['name'] for c in insp.get_columns('visits')}:
        op.add_column('visits', sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id') if bind.dialect.name != 'sqlite' else None, nullable=True))
    op.execute(sa.text('UPDATE leads SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL'))
    for t in NEW_TABLES:
        Base.metadata.tables[t].create(bind=bind, checkfirst=True)
    # نقش‌های الگو فقط یک‌بار دسترسی automation.write را می‌گیرند (نقش‌های سفارشی دست‌نخورده می‌مانند)
    roles = sa.table('roles', sa.column('id', sa.Integer), sa.column('name', sa.String), sa.column('permissions', sa.JSON))
    for rid, name, perms in bind.execute(sa.select(roles.c.id, roles.c.name, roles.c.permissions)).fetchall():
        if name in TEMPLATE_ROLES:
            p = json.loads(perms) if isinstance(perms, str) else list(perms or [])
            if 'automation.write' not in p and '*' not in p:
                bind.execute(roles.update().where(roles.c.id == rid).values(permissions=p + ['automation.write']))


def downgrade():
    raise RuntimeError('برای بازگشت، پشتیبان پیش از ارتقا را برگردانید')
