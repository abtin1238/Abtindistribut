export class ApiError extends Error {
  constructor(public status: number, message: string, public requestId?: string) { super(message) }
}
let token: string | null = sessionStorage.getItem('abtin_token')
export const setToken = (t: string | null) => {
  token = t
  t ? sessionStorage.setItem('abtin_token', t) : sessionStorage.removeItem('abtin_token')
}
export const hasToken = () => !!token
const authHeaders = (h?: HeadersInit) => { const x = new Headers(h); if (token) x.set('Authorization', `Bearer ${token}`); return x }
async function fail(r: Response): Promise<never> {
  const body = await r.json().catch(() => null)
  if (r.status === 401) setToken(null)
  const m = body?.message ?? (typeof body?.detail === 'string' ? body.detail : null) ?? 'خطای ناشناخته'
  throw new ApiError(r.status, m, body?.request_id)
}
export async function api<T>(path: string, init: RequestInit & { json?: unknown; form?: FormData } = {}): Promise<{ data: T; total: number | null }> {
  const headers = authHeaders(init.headers)
  let body = init.body
  if (init.json !== undefined) { headers.set('Content-Type', 'application/json'); body = JSON.stringify(init.json) }
  if (init.form) body = init.form
  const r = await fetch(`/api${path}`, { ...init, headers, body })
  if (!r.ok) return fail(r)
  const data = (await r.json().catch(() => null)) as T
  const t = r.headers.get('X-Total-Count')
  return { data, total: t ? Number(t) : null }
}
export async function download(path: string, filename: string) {
  const r = await fetch(`/api${path}`, { headers: authHeaders() })
  if (!r.ok) return fail(r)
  const url = URL.createObjectURL(await r.blob())
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url)
}
export const get = <T,>(p: string) => api<T>(p).then(r => r.data)
export const send = <T = unknown,>(p: string, json?: unknown, method = 'POST') => api<T>(p, { method, json }).then(r => r.data)
