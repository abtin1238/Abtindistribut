import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import { ErrorBox, Spinner } from '../components/ui'
import { Kpis } from './Dashboard'
export default function Ceo() {
  const q = useQuery({ queryKey: ['ceo'], queryFn: () => get<{ kpis: Record<string, unknown> }>('/ceo/summary') })
  return (
    <section className="flex flex-col gap-4 p-4">
      <h2 className="text-lg font-bold">پنل مدیرعامل</h2>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorBox error={q.error} /> : <Kpis data={q.data?.kpis ?? {}} />}
    </section>
  )
}
