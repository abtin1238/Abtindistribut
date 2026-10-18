import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

from app.main import Base, DB_URL  # noqa: E402  (models live in app.main)

target_metadata = Base.metadata


def _url():
    return config.get_main_option('sqlalchemy.url') or os.getenv('DATABASE_URL') or DB_URL


def run_migrations_offline():
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    url = _url()
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True, render_as_batch=url.startswith('sqlite'))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
