import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { faDigits } from '../lib/fa'
import { Btn, Card, Empty, ErrorBox, Spinner } from '../components/ui'

type Item = { id: number; title: string; body?: string; read: boolean; created_at: string }
type Feed = { items: Item[]; unread: number }
const when = (s: string) => {
  const d = new Date(s)
  return isNaN(+d) ? s : new Intl.DateTimeFormat('fa-IR-u-ca-persian', { dateStyle: 'short', timeStyle: 'short' }).format(d)
}
function FeedCard() {
  const qc = useQueryClient()
  const feed = useQuery({ queryKey: ['nt-feed'], queryFn: () => get<Feed>('/notifications/feed') })
  const [older, setOlder] = useState<Item[]>([]), [more, setMore] = useState(true)
  const readAll = useMutation({
    mutationFn: () => send('/notifications/read-all'),
    onSuccess: () => { setOlder([]); qc.invalidateQueries({ queryKey: ['nt-feed'] }); qc.invalidateQueries({ queryKey: ['unread'] }) },
  })
  const items = [...(feed.data?.items ?? []), ...older]
  async function loadMore() {
    const last = items[items.length - 1]
    if (!last) return
    const r = await get<Feed>(`/notifications/feed?before_id=${last.id}`)
    setOlder(o => [...o, ...r.items]); if (!r.items.length) setMore(false)
  }
  return (
    <Card title="فید">
      {feed.isLoading ? <Spinner /> : feed.error ? <ErrorBox error={feed.error} /> : (
        <>
          <div className="mb-2 flex items-center gap-2">
            <span className="me-auto text-sm text-mut">{faDigits(feed.data?.unread ?? 0)} اعلان خوانده‌نشده</span>
            <Btn variant="ghost" disabled={readAll.isPending} onClick={() => readAll.mutate()}>علامت‌گذاری همه به‌عنوان خوانده</Btn>
          </div>
          {!items.length && <Empty>اعلانی وجود ندارد</Empty>}
          {items.map(n => (
            <div key={n.id} className={`border-t border-bd py-2  ${n.read ? '' : 'font-semibold'}`}>
              <div>{n.title}</div>{n.body && <p className="text-sm font-normal">{n.body}</p>}
              <small className="text-mut">{when(n.created_at)}</small>
            </div>
          ))}
          {(feed.data?.items.length ?? 0) >= 30 && more && <Btn variant="ghost" onClick={() => loadMore().catch(() => setMore(false))}>قدیمی‌تر</Btn>}
        </>
      )}
    </Card>
  )
}

export default function Notifications() {
  return (
    <section className="mx-auto flex max-w-3xl flex-col gap-4 p-4">
      <div className="flex items-center gap-2">
        <h2 className="me-auto text-lg font-bold">اعلان‌ها</h2>
        <Link to="/settings?tab=notifications" className="ds-link text-sm">تنظیمات اعلان ←</Link>
      </div>
      <FeedCard />
    </section>
  )
}
