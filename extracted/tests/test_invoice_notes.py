import os
os.environ.setdefault('DATABASE_URL', 'sqlite:////tmp/abtin_dist_invnotes.sqlite3')
os.environ['ADMIN_PASSWORD'] = 'test-password'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)


def H():
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'test-password'})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['token']}


def _order(h, tag, note=''):
    c = client.post('/api/customers', headers=h, json={'code': 'N' + tag, 'name': 'مشتری ' + tag, 'credit_limit': 10 ** 7}).json()
    p = client.post('/api/products', headers=h, json={'sku': 'N' + tag, 'name': 'کالا ' + tag, 'base_price': 100}).json()
    w = client.get('/api/warehouses', headers=h).json()[0]
    client.post('/api/stock/adjust', headers=h, json={'warehouse_id': w['id'], 'product_id': p['id'], 'quantity': 10, 'kind': 'in'})
    o = client.post('/api/orders', headers=h, json={'customer_id': c['id'], 'warehouse_id': w['id'], 'items': [{'product_id': p['id'], 'quantity': 2}], 'note': note})
    assert o.status_code == 200, o.text
    return o.json(), c


def test_note_sanitized_and_copied_to_invoice_with_terms():
    h = H()
    assert client.put('/api/settings/invoice-terms', headers=h, json={'terms': '<p>پرداخت ۷ روزه</p><script>x</script>'}).json()['terms'] == '<p>پرداخت ۷ روزه</p>'
    o, c = _order(h, 'A1', '<p onclick="x()">تحویل <b>فردا</b></p><script>alert(1)</script>')
    assert o['note'] == '<p>تحویل <strong>فردا</strong></p>'
    assert client.post(f"/api/orders/{o['id']}/approve", headers=h).status_code == 200
    inv = next(i for i in client.get('/api/invoices', headers=h).json() if i['order_id'] == o['id'])
    assert inv['customer_name'] == c['name'] and inv['order_number'] == o['number'] and float(inv['remaining']) == float(inv['total'])
    d = client.get(f"/api/invoices/{inv['id']}", headers=h).json()
    assert d['invoice']['note'] == o['note'] and d['invoice']['terms'] == '<p>پرداخت ۷ روزه</p>' and d['returns'] == []


def test_edit_note_and_filters():
    h = H()
    o, c = _order(h, 'B2')
    client.post(f"/api/orders/{o['id']}/approve", headers=h)
    inv = next(i for i in client.get('/api/invoices', headers=h).json() if i['order_id'] == o['id'])
    r = client.patch(f"/api/invoices/{inv['id']}/note", headers=h, json={'note': '<h1>عنوان</h1><i>x</i>'})
    assert r.status_code == 200 and r.json()['note'] == '<h2>عنوان</h2><em>x</em>'
    assert [i['id'] for i in client.get('/api/invoices', headers=h, params={'q': c['name'], 'status': 'open'}).json()] == [inv['id']]
    assert client.get('/api/invoices', headers=h, params={'status': 'bogus'}).status_code == 400
    assert client.get('/api/invoices', headers=h, params={'q': '%'}).json() == []
    assert client.post(f"/api/orders/{o['id']}/cancel", headers=h).status_code == 200
    assert client.patch(f"/api/invoices/{inv['id']}/note", headers=h, json={'note': 'x'}).status_code == 409
    assert client.patch(f"/api/invoices/{inv['id']}/note", json={'note': 'x'}).status_code == 401
