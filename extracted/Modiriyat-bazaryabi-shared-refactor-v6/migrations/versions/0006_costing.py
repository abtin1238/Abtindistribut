"""مرحله ۱۴: ثبت بهای تمام‌شده (میانگین موزون)، تخفیف/هزینه‌ی جانبی خرید، بهای سطر فاکتور

Revision ID: 0006
Revises: 0005

- products.avg_cost: از خریدهای دریافت‌شده‌ی قبلی (میانگین وزنی کل رسیدها) برآورد می‌شود؛ فاکتورهای قبلی بهای تمام‌شده ندارند.
"""
import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

COLS = {
    'products': [('avg_cost', sa.Numeric(18, 4), '0')],
    'stock_moves': [('unit_cost', sa.Numeric(18, 4), None)],
    'purchases': [('discount', sa.Numeric(18, 2), '0'), ('freight', sa.Numeric(18, 2), '0')],
    'purchase_items': [('discount', sa.Numeric(18, 2), '0'), ('landed', sa.Numeric(18, 2), '0')],
    'invoice_lines': [('unit_cost', sa.Numeric(18, 4), '0'), ('cogs', sa.Numeric(18, 2), '0')],
}


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table, cols in COLS.items():
        have = {c['name'] for c in insp.get_columns(table)}
        for name, typ, default in cols:
            if name not in have:
                op.add_column(table, sa.Column(name, typ, nullable=default is None, server_default=default))
    rows = bind.execute(sa.text(
        "SELECT pi.product_id, SUM(pi.quantity * pi.unit_cost), SUM(pi.quantity) FROM purchase_items pi "
        "JOIN purchases p ON p.id = pi.purchase_id WHERE p.status = 'received' GROUP BY pi.product_id")).fetchall()
    for pid, value, qty in rows:
        if qty and float(qty) > 0:
            bind.execute(sa.text('UPDATE products SET avg_cost = :c WHERE id = :i AND avg_cost = 0'),
                         {'c': round(float(value) / float(qty), 4), 'i': pid})


def downgrade():
    raise RuntimeError('برای بازگشت، پشتیبان پیش از ارتقا را برگردانید')
