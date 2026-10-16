"""تست مرورگری وب‌اپ با API ماک‌شده (بدون نیاز به بک‌اند): جدول داده، فرم‌ها، XSS، موبایل بدون اسکرول افقی، نرمال‌سازی تصویر.
اجرا: pip install pytest playwright && playwright install chromium && pytest -q tests/ui"""
import functools, http.server, json, os, socketserver, threading
from urllib.parse import parse_qs, urlparse
import pytest
pw = pytest.importorskip('playwright.sync_api')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALL = [{'id': i, 'code': f'C{i}', 'name': ('<img src=x onerror=window.__xss=1>' if i == 1 else f'مشتری {i}'), 'phone': '0912', 'region': 'تهران', 'customer_group': 'A', 'credit_limit': 1000 * i, 'balance': i} for i in range(1, 8)]

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

@pytest.fixture(scope='module')
def site():
    srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{srv.server_address[1]}'
    srv.shutdown()

def make_api(posted, urls):
    def api(route):
        r = route.request; path = r.url.split('/api', 1)[1]; urls.append(r.method + ' ' + path)
        def ok(body, h=None): route.fulfill(status=200, content_type='application/json', body=json.dumps(body), headers=h or {})
        if path.startswith('/me'): return ok({'user': {'id': 1, 'name': 'مدیر', 'username': 'a', 'role': 'admin', 'permissions': ['*']}, 'company': {'id': 1, 'name': 'ش', 'code': 'c', 'group_name': 'g'}, 'companies': []})
        if path.startswith('/customers'):
            if r.method == 'POST':
                b = json.loads(r.post_data); posted.append(b)
                if b['code'] == 'DUP': return route.fulfill(status=409, content_type='application/json', body=json.dumps({'detail': 'کد تکراری است'}))
                return ok({'id': 99, **b})
            q = parse_qs(urlparse(r.url).query); lim = int(q.get('limit', ['500'])[0]); off = int(q.get('offset', ['0'])[0])
            return ok(ALL[off:off + lim], {'X-Total-Count': str(len(ALL))})
        if path.startswith('/notifications/feed'): return ok({'items': [], 'unread': 0})
        if path.startswith('/notifications/events'): return ok({'events': [{'code': f'e{i}', 'title': f'رویداد {i}', 'default_channels': []} for i in range(5)], 'channels': [{'code': 'inapp', 'label': 'درون‌برنامه', 'available': True}, {'code': 'email', 'label': 'ایمیل', 'available': False}, {'code': 'sms', 'label': 'پیامک', 'available': False}, {'code': 'webpush', 'label': 'اعلان مرورگر', 'available': False}]})
        if path.startswith('/notifications/preferences'): return ok({'prefs': {}, 'contact': {'email': '', 'phone': ''}, 'push_subscriptions': 0})
        return ok([])
    return api

def open_page(p, site, mobile=False):
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390 if mobile else 1200, 'height': 800}, is_mobile=mobile, has_touch=mobile)
    pg = ctx.new_page(); posted, urls = [], []
    pg.route('**/api/**', make_api(posted, urls)); pg.route(lambda u: '127.0.0.1' not in u, lambda r: r.abort())
    pg.add_init_script("localStorage.setItem('ads_token','t')")
    pg.goto(site + '/web/index.html'); pg.wait_for_timeout(1200)
    return b, pg, posted, urls

def test_datatable_flow(site):
    with pw.sync_playwright() as p:
        b, pg, posted, urls = open_page(p, site)
        pg.evaluate("go('customers')"); pg.wait_for_selector('.dt tbody tr[data-i]')
        assert pg.locator('.dt tbody tr[data-i]').count() == 7
        assert pg.evaluate('window.__xss') is None
        pg.select_option('.dt-size', '10'); pg.wait_for_timeout(200)
        assert any('limit=10&offset=0' in u for u in urls)
        pg.click('[data-sort=credit_limit]'); pg.click('[data-sort=credit_limit]')
        assert 'C7' in pg.locator('.dt tbody tr').first.inner_text()
        pg.fill('.dt-q', 'C3'); assert pg.locator('.dt tbody tr[data-i]').count() == 1; pg.fill('.dt-q', '')
        pg.click('[data-act=create]'); pg.fill('[name=code]', 'DUP'); pg.fill('[name=name]', 'x'); pg.click('.fd .primary'); pg.wait_for_timeout(200)
        assert 'تکراری' in pg.locator('.fd-err').inner_text()
        pg.fill('[name=code]', 'N1'); pg.fill('[name=credit_limit]', '500'); pg.click('.fd .primary'); pg.wait_for_selector('.fd', state='detached')
        assert posted[-1]['code'] == 'N1' and posted[-1]['credit_limit'] == 500
        b.close()

@pytest.mark.parametrize('page', ['customers', 'notifications', 'organizations'])
def test_mobile_no_horizontal_overflow(site, page):
    with pw.sync_playwright() as p:
        b, pg, _, _ = open_page(p, site, mobile=True)
        pg.evaluate(f"go('{page}')"); pg.wait_for_timeout(700)
        assert pg.evaluate('document.documentElement.scrollWidth') <= 390
        b.close()

def test_normalize_image_makes_square(site):
    with pw.sync_playwright() as p:
        b, pg, _, _ = open_page(p, site)
        r = pg.evaluate("""async()=>{const c=document.createElement('canvas');c.width=800;c.height=200;const x=c.getContext('2d');x.fillStyle='#f00';x.fillRect(0,0,800,200);const blob=await new Promise(r=>c.toBlob(r,'image/png'));const f=await Shared.normalizeImage(new File([blob],'a.png',{type:'image/png'}),{size:512});const bm=await createImageBitmap(f);return [bm.width,bm.height]}""")
        assert r == [512, 512]
        b.close()

EVIL = '<img src=x onerror=window.__xss=1>'
KEYS = ['name', 'title', 'number', 'code', 'sku', 'username', 'description', 'filename', 'body', 'message', 'note', 'notes', 'address', 'region', 'phone', 'party', 'bank', 'position', 'action', 'entity', 'status', 'unit', 'warehouse', 'product', 'customer', 'customer_name', 'user_name', 'supplier_name', 'label', 'reason']
PAGES = ['customers', 'products', 'stock', 'purchases', 'treasury', 'hr', 'audit', 'organizations', 'users', 'orders', 'invoices', 'deliveries', 'visits', 'automation', 'documents', 'contracts', 'integrations', 'notifications', 'search', 'reports', 'accounting', 'ceo', 'import', 'settings']

def test_no_xss_execution_on_any_page(site):
    """هر فیلد رشته‌ای سرور = payload؛ هیچ صفحه‌ای نباید آن را اجرا کند (خطاهای صفحه به‌خاطر شکل ناقص داده نادیده گرفته می‌شوند)."""
    evil_row = {k: EVIL for k in KEYS} | {'id': 1, 'total': 1, 'amount': 1, 'balance': 1}
    with pw.sync_playwright() as p:
        b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1200, 'height': 800}); pg = ctx.new_page()
        base = make_api([], [])
        def api(route):
            path = route.request.url.split('/api', 1)[1]
            if route.request.method == 'GET' and not path.startswith(('/me', '/notifications', '/organizations')):
                return route.fulfill(status=200, content_type='application/json', body=json.dumps([evil_row, evil_row]), headers={'X-Total-Count': '2'})
            if path.startswith('/organizations'):
                return route.fulfill(status=200, content_type='application/json', body=json.dumps({'group': {'name': EVIL}, 'companies': [{'id': 1, 'name': EVIL, 'code': EVIL, 'parent_company_id': None}], 'branches': [{'id': 1, 'company_id': 1, 'name': EVIL, 'address': EVIL}]}))
            return base(route)
        pg.route('**/api/**', api); pg.route(lambda u: '127.0.0.1' not in u, lambda r: r.abort())
        pg.on('dialog', lambda d: d.dismiss()); pg.on('pageerror', lambda e: None)
        pg.add_init_script("localStorage.setItem('ads_token','t')")
        pg.goto(site + '/web/index.html'); pg.wait_for_timeout(1200)
        for name in PAGES:
            try: pg.evaluate(f"go('{name}')")
            except Exception: pass
            pg.wait_for_timeout(300)
            assert pg.evaluate('window.__xss') is None, f'XSS executed on page {name}'
        b.close()

A11Y_JS = """()=>{const out=[];const vis=e=>e.offsetParent!==null||e.getClientRects().length;
const name=e=>(e.getAttribute('aria-label')||e.getAttribute('aria-labelledby')||e.getAttribute('title')||e.innerText||e.textContent||'').trim();
document.querySelectorAll('button,[role=button],a[href]').forEach(e=>{if(vis(e)&&!name(e))out.push('NO-NAME '+e.tagName+'.'+e.className)});
document.querySelectorAll('input:not([type=hidden]),select,textarea').forEach(e=>{if(!vis(e))return;const id=e.id;const lab=e.closest('label')||(id&&document.querySelector('label[for="'+CSS.escape(id)+'"]'));if(!lab&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby')&&!e.getAttribute('title'))out.push('NO-LABEL '+e.tagName+'#'+id)});
document.querySelectorAll('[onclick]').forEach(e=>{if(vis(e)&&!/^(BUTTON|A|INPUT|SELECT)$/.test(e.tagName)&&!e.getAttribute('role')&&e.tabIndex<0)out.push('CLICK-NOT-KEYBOARD '+e.tagName+'.'+e.className)});
return out}"""

@pytest.mark.parametrize('page', ['customers', 'treasury', 'notifications', 'organizations', 'integrations', 'documents', 'import'])
def test_basic_accessibility(site, page):
    """هر کنترل نمایان نام دسترس‌پذیر دارد و هر عنصر کلیک‌پذیر با کیبورد قابل دسترسی است."""
    with pw.sync_playwright() as p:
        b, pg, _, _ = open_page(p, site)
        pg.evaluate(f"go('{page}')"); pg.wait_for_timeout(500)
        assert pg.evaluate(A11Y_JS) == []
        b.close()
