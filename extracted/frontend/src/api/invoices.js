import { authApi } from './auth.js';
import { apiUrl } from './base.js';

const token = () => authApi.getSession()?.tokens?.access || '';
async function request(path, options = {}) {
  const res = await fetch(apiUrl(`/api/sales${path}`), {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}`, ...(options.headers || {}) },
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.detail || Object.values(data || {})?.[0]?.[0] || 'عملیات فاکتور ناموفق بود');
  return data;
}
export const invoiceApi = {
  list: async () => { const d = await request('/invoices/'); return d?.results ?? d ?? []; },
  get: (id) => request(`/invoices/${id}/`),
  sign: (id, payload) => request(`/invoices/${id}/sign/`, { method: 'POST', body: JSON.stringify(payload) }),
  receivePayment: (payload) => request('/payments/receive/', { method: 'POST', body: JSON.stringify(payload) }),
};
