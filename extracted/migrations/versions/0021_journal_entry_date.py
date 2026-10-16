"""تاریخ سند (entry_date) جدا از زمان ثبت؛ سندهای قدیمی از created_at پر می‌شوند

Revision ID: 0021
Revises: 0020
"""
from alembic import op
import sqlalchemy as sa

revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade():
    cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('journal_entries')}
    if 'entry_date' not in cols:
        op.add_column('journal_entries', sa.Column('entry_date', sa.Date(), nullable=True))
        op.create_index('ix_journal_entries_entry_date', 'journal_entries', ['entry_date'])
    expr = 'date(created_at)' if op.get_bind().dialect.name == 'sqlite' else 'created_at::date'
    op.execute(sa.text(f'UPDATE journal_entries SET entry_date = {expr} WHERE entry_date IS NULL'))


def downgrade():
    op.drop_index('ix_journal_entries_entry_date', table_name='journal_entries')
    op.drop_column('journal_entries', 'entry_date')
