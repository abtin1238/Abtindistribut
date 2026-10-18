# Migrations (Alembic)

- Baseline `0001` snapshots the current schema (idempotent `create_all(checkfirst=True)`).
- New database: `alembic upgrade head`.
- Existing database created by the app: `alembic stamp 0001`, then `alembic upgrade head`.
- Schema change: edit models in `app/modules/<name>/models.py` -> `alembic revision --autogenerate -m "msg"` -> review -> commit.
- Do NOT add new `ALTER TABLE` entries to `ensure_schema()`; it remains only for legacy databases and will be removed after all deployments are stamped.
- Rollback: restore the pre-upgrade backup (baseline has no downgrade).
