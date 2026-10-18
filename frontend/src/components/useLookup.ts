import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import type { Row } from '../lib/types'
export function useLookup(endpoint?: string) {
  const q = useQuery({ queryKey: ['lookup', endpoint], enabled: !!endpoint, staleTime: 60_000, queryFn: () => get<Row[]>(endpoint!) })
  const map = new Map<number, string>()
  for (const r of q.data ?? []) map.set(r.id, String(r.name ?? r.title ?? r.number ?? r.id))
  return map
}
