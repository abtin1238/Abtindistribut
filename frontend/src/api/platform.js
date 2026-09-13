import { authApi } from './auth.js';
import { apiUrl } from './base.js';
async function get(path) {
  const session = authApi.getSession();
  const res = await fetch(apiUrl(`/api${path}`), { headers: { Authorization: `Bearer ${session?.tokens?.access || ''}` } });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.detail || 'خطا در دریافت اطلاعات');
  return data?.results ?? data ?? [];
}
export const platformApi = {
  company: async () => { const data = await get('/org/companies/?is_active=true'); return Array.isArray(data) ? data[0] || null : data?.results?.[0] || data || null; },
  notifications: () => get('/notifications/notifications/'),
  markAllRead: () => fetch(apiUrl('/api/notifications/notifications/mark_all_read/'), { method: 'POST', headers: { Authorization: `Bearer ${authApi.getSession()?.tokens?.access || ''}` } }),
  auditLogs: () => get('/audit/logs/'),
};
