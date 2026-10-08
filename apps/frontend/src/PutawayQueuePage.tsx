import { useCallback, useEffect, useState } from 'react'
import { ApiError, loadEligiblePutawayLines, PutawayQueue } from './api'

type Props = { onUnauthorized: () => void }

export default function PutawayQueuePage({ onUnauthorized }: Props) {
  const [queue, setQueue] = useState<PutawayQueue | null>(null)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')

  const loadQueue = useCallback(async () => {
    setLoading(true)
    setForbidden(false)
    setError('')
    try {
      setQueue(await loadEligiblePutawayLines())
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
      else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
      else setError(failure instanceof Error ? failure.message : 'Unable to load eligible Putaway lines.')
    } finally {
      setLoading(false)
    }
  }, [onUnauthorized])

  useEffect(() => {
    let active = true
    loadEligiblePutawayLines()
      .then((loaded) => { if (active) setQueue(loaded) })
      .catch((failure: unknown) => {
        if (!active) return
        if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
        else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
        else setError(failure instanceof Error ? failure.message : 'Unable to load eligible Putaway lines.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [onUnauthorized])

  return (
    <section className="putaway-card" aria-labelledby="putaway-queue-title">
      <div className="title-row"><div><p className="eyebrow">Warehouse Staff work queue</p><h1 id="putaway-queue-title">Putaway</h1><p className="supporting-copy">Select a recorded Receive line with quantity still eligible for placement.</p></div><span className="step-badge">PUTAWAY</span></div>
      {loading && <p className="status-panel" role="status">Loading eligible Putaway lines…</p>}
      {!loading && forbidden && <div className="error-panel" role="alert"><h2>Warehouse Staff role required</h2></div>}
      {!loading && error && <div className="error-panel" role="alert"><p>{error}</p><button type="button" onClick={() => void loadQueue()}>Retry</button></div>}
      {!loading && !forbidden && !error && queue?.items.length === 0 && <p className="status-panel">No Receive lines currently have eligible Putaway quantity.</p>}
      {!loading && !forbidden && !error && queue && queue.items.length > 0 && (
        <div className="history-table-scroll"><table><thead><tr><th>Reference</th><th>SKU</th><th>Actual</th><th>Placed</th><th>Eligible</th><th>Action</th></tr></thead><tbody>{queue.items.map((item) => (
          <tr key={item.receive_line_id}><td>{item.expected_reference || '—'}</td><td>{item.sku}</td><td>{item.actual_quantity}</td><td>{item.confirmed_quantity}</td><td>{item.eligible_quantity}</td><td><a className="primary-link" href={`/putaway/${encodeURIComponent(item.receive_line_id)}`}>Open Putaway</a></td></tr>
        ))}</tbody></table></div>
      )}
    </section>
  )
}
