# Architecture

Group (Holding) -> Companies -> Branches -> Warehouses/Units.

Every operational record carries `company_id`. Authentication selects an active company through a membership, and operational list/write APIs scope records to that company. One user can belong to multiple companies in the same holding.

The web admin, visitor app and delivery app share the same API/database. They do not maintain separate business databases.

PostgreSQL is the production database; SQLite is only a development/test fallback.

## Accounting (double-entry)

- `accounts` (per company chart, default codes lazily created), `journal_entries` + `journal_lines` (multi-line, `sum(debit)==sum(credit)` enforced in `post_entry`).
- Customer/supplier balances are **derived** from ledger lines (accounts 1210 / 2110 with `customer_id` / `supplier_id`); `Customer.balance` / `Supplier.balance` columns are legacy and unused.
- Auto postings: invoice approve (Dr 1210; Cr 4110/2210/4120), payments (cash 1110 / bank 1120 / checks 1130), purchase receive (Dr 1310, Cr 2110), checks (create + each status change).
- Cancel = reversal entry (`reverses_id`); auto entries can only be reversed through their source operation; manual entries via `POST /api/journal/{id}/reverse` (`finance.approve`).
- Endpoints: `/api/accounts`, `/api/journal`, `/api/reports/trial-balance`, `/api/customers/{id}/ledger`.
- `backfill_ledger()` runs once at startup (flag in `sequences`) to post pre-ledger invoices/payments/purchases/checks.

## Returns & partial delivery

- `sales_returns` + `sales_return_lines`; `Invoice.returned` accumulates credit; effective payable = `total - returned - paid`.
- `POST /api/orders/{id}/return` (delivered orders only, `sales.approve`): restocks, posts Dr 4110/2210, Cr 1210.
- `PATCH /api/deliveries/{id}` with `items:[{product_id,quantity}]` and `status=delivered`: ships delivered qty, releases the full reservation, auto-creates a non-restocked return for the shortfall.

## Financial reports

`/api/reports/{trial-balance,profit-loss,balance-sheet,general-ledger,aging}` (all derived from posted journal lines / invoices) with `.xlsx` exports for trial-balance, profit-loss, general-ledger and aging (`openpyxl`; text cells starting with `= + - @` are escaped).

## Offline sync

`POST /api/sync` applies events through the same service functions as the REST endpoints (permission check per event type). Supported: `delivery.start|delivered|failed`, `visit.start|finish`, `order.create`, `payment.create`. Per-event result: `applied | duplicate | rejected | retry` (`retry` = reference not synced yet or transient error; the event is not stored, so the client keeps it). Offline-created records are referenced by `ref` = client id of the creating event. Max 200 events/request.

## Permission model

`current()` enforces `required_perm(method,path)` on every authenticated route. Unknown `/api/*` paths default to `admin.write` (deny-by-default). Public: `/api/auth/login`, `/api/brand/logo/*`. Open to any authenticated user (self-scoped or filtered inside): `/api/me`, `/api/notifications`, `/api/permissions`, `/api/sync` (per-event permission), `/api/dashboard` (fields nulled without the matching read permission), `/api/search` (per-entity permission + own-orders scope). Financial reports and customer ledger need `finance.read`; dashboard series need `sales.read`.

## Data import (Holoo / Excel / CSV)

`POST /api/import/preview` and `/api/import/commit` (multipart: `file`, optional `entity`, `mapping` JSON `{colIndex: field}`, `sheet`, `header_row`, `warehouse_id`, `strict`) — permission `import.write` plus the target module's write permission (`finance.write` when balances are imported). Stateless: the client re-sends the file on commit. Format is detected from content (xlsx, legacy xls via optional `xlrd`, HTML-as-xls, Excel-2003 XML, CSV/TSV in utf-8/utf-16/cp1256, JSON). `app/services/importer.py` (no DB deps) finds the header row (skips report titles, repeated page headers, totals), auto-maps Persian/English headers, normalizes Persian digits/Arabic ي ك, `1,234` / `(123)` / `123-` numbers and phones. `app/modules/importer/router.py` upserts: products by `sku`, customers by `code` (else name), suppliers by name; stock is *set* to the file quantity (diff posted as `in`/`out` stock move, never below reserved). Customer/supplier balances are *set* to the file value by posting an adjustment entry (`source=import_balance`) against equity `3100`, so re-importing the same file is a no-op. Empty cells never overwrite existing values. Preview writes nothing; commit skips error rows (or aborts all with `strict`).

## Code layout

`app/core` (config, db, security/permissions, common helpers, bootstrap/seed) → `app/models.py`, `app/schemas.py` → `app/services/accounting.py` (ledger, pricing, invoice state) → `app/modules/*` (one APIRouter per domain: system, auth_org, crm, catalog, inventory, sales, purchasing, delivery, field, finance, hr, platform, sync). `app/main.py` wires routers and runs startup (seed, role templates, ledger backfill). Dependency direction is one-way; `sync` imports sales/delivery/field/finance, `sales` imports `platform` (brand).

## ساختار ماژولار بک‌اند

هر ماژول در `app/modules/<name>/` این فایل‌ها را دارد (فقط آن‌هایی که محتوا دارند):

- `models.py` — مدل‌های SQLAlchemy همان ماژول (جدول‌های مشترک `Sequence` و `IdempotencyRecord` در `app/core/models.py`)
- `schemas.py` — schemaهای Pydantic ورودی (شامل schemaهایی که قبلاً داخل router تعریف می‌شدند)
- `service.py` — کل منطق کسب‌وکار و کوئری‌ها: بدنهٔ هر handler با همان نام و پارامترها (بدون `Depends`) به‌علاوهٔ ثابت‌ها و توابع کمکی؛ هرگز از `router.py` import نمی‌کند
- `router.py` — فقط تعریف endpointها (decorator و signature)؛ هر handler یک stub است که `service.<همان‌نام>` را صدا می‌زند
- `__init__.py` — بارگذاری تنبل (PEP 562)؛ import پکیج، router را بالا نمی‌آورد و نام‌های router/service مثل قبل از پکیج در دسترس‌اند (`from app.modules.finance import payment`)

`app/models.py` و `app/schemas.py` فقط facade هستند (importهای قدیمی، Alembic و تست‌ها بدون تغییر کار می‌کنند). schema برند در پلتفرم از `BrandIn` به `BrandingIn` تغییر نام داد چون با `BrandIn` کاتالوگ هم‌نام بود.
