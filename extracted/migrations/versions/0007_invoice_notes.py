"""مرحله ۱۵: یادداشت سفارش/فاکتور (ادیتور متن غنی) و شرایط فاکتور

Revision ID: 0007
Revises: 0006

- orders.note، invoices.note (HTML پاک‌سازی‌شده)، invoices.terms (نسخه‌ی شرایط در لحظه‌ی صدور؛ فاکتورهای قدیمی خالی می‌مانند).
"""
import sqlalchemy as sa
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

COLS = {'orders': ['note'], 'invoices': ['note', 'terms']}


def upgrade():
    insp = sa.inspect(op.get_bind())
    for table, names in COLS.items():
        have = {c['name'] for c in insp.get_columns(table)}
        for name in names:
            if name not in have:
                op.add_column(table, sa.Column(name, sa.Text(), nullable=False, server_default=''))


def downgrade():
    raise RuntimeError('برای بازگشت، پشتیبان پیش از ارتقا را برگردانید')
