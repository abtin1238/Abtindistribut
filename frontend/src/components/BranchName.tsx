import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
type Org = { branches?: { id: number; name: string }[] }
/** نام شعبه از روی شناسه؛ همان کلید کش صفحهٔ «هلدینگ و شرکت‌ها» */
export function BranchName({ id }: { id: unknown }) {
  const q = useQuery({ queryKey: ['organizations'], staleTime: 60_000, queryFn: () => get<Org>('/organizations') })
  if (id == null || id === '') return <>—</>
  return <>{q.data?.branches?.find(b => b.id === Number(id))?.name ?? String(id)}</>
}
