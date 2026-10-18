"""مشتری به شعبه وصل می‌شود (customers.branch_id)

مدیر شعبه‌ای فقط مشتریان شعبهٔ خودش را می‌بیند. مشتریان موجود در شرکتی که دقیقاً یک شعبه دارد به همان شعبه وصل می‌شوند؛
در شرکت چندشعبه‌ای بدون شعبه می‌مانند (فقط مدیر کل می‌بیند تا شعبه‌شان تعیین شود).

Revision ID: 0031
Revises: 0030
"""
from alembic import op
import sqlalchemy as sa

revision = '0031'
down_revision = '0030'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'customers' not in insp.get_table_names():
        return
    if 'branch_id' not in {c['name'] for c in insp.get_columns('customers')}:
        op.add_column('customers', sa.Column('branch_id', sa.Integer(), nullable=True))
    if 'branches' not in insp.get_table_names():
        return
    cu = sa.table('customers', sa.column('id', sa.Integer), sa.column('company_id', sa.Integer), sa.column('branch_id', sa.Integer))
    br = sa.table('branches', sa.column('id', sa.Integer), sa.column('company_id', sa.Integer))
    for cid, in bind.execute(sa.select(sa.distinct(cu.c.company_id)).where(cu.c.branch_id.is_(None))).all():
        bs = [b for (b,) in bind.execute(sa.select(br.c.id).where(br.c.company_id == cid)).all()]
        if len(bs) == 1:
            bind.execute(cu.update().where(cu.c.company_id == cid, cu.c.branch_id.is_(None)).values(branch_id=bs[0]))


def downgrade():
    pass
