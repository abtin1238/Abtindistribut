import { useQuery } from '@tanstack/react-query'
import { get } from './api'
export type Me = {
  user: { id: number; name: string; username: string; role: string; permissions: string[] }
  company: { id: number; name: string; code: string; group_name: string }
  companies: { id: number; name: string; code: string }[]
}
export const useMe = () => useQuery({ queryKey: ['me'], queryFn: () => get<Me>('/me'), staleTime: 300_000 })
export const can = (me: Me | undefined, perm?: string) =>
  !perm || !!me?.user.permissions.some(p => p === '*' || p === perm || (p.endsWith('.*') && perm.startsWith(p.slice(0, -1))))
