import { useCallback, useEffect, useState } from 'react'
import { ApiError, loadActionablePicks, PickQueue } from './api'

type Props = { onUnauthorized: () => void }

export default function PickQueuePage({ onUnauthorized }: Props) {
  const [queue, setQueue] = useState<PickQueue | null>(null)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')

  const loadQueue = useCallback(async () => {
    setLoading(true); setForbidden(false); setError('')
    try { setQueue(await loadActionablePicks()) }
    catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
      else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
      else setError(failure instanceof Error ? failure.message : 'Unable to load actionable Picks.')
    } finally { setLoading(false) }
  }, [onUnauthorized])

  useEffect(() => {
    let active = true
    loadActionablePicks()
      .then((loaded) => { if (active) setQueue(loaded) })
      .catch((failure: unknown) => {
        if (!active) return
        if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
        else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
        else setError(failure instanceof Error ? failure.message : 'Unable to load actionable Picks.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [onUnauthorized])

  return (
    <section className="putaway-card" aria-labelledby="pick-queue-title">
      <div className="title-row"><div><p className="eyebrow">Warehouse Staff work queue</p><h1 id="pick-queue-title">Pick</h1><p className="supporting-copy">Select a Pick request that has no recorded outcome.</p></div><span className="step-badge">PICK</span></div>
      {loading && <p className="status-panel" role="status">Loading actionable Picks…</p>}
      {!loading && forbidden && <div className="error-panel" role="alert"><h2>Warehouse Staff role required</h2></div>}
      {!loading && error && <div className="error-panel" role="alert"><p>{error}</p><button type="button" onClick={() => void loadQueue()}>Retry</button></div>}
      {!loading && !forbidden && !error && queue?.items.length === 0 && <p className="status-panel">No actionable Pick requests are available.</p>}
      {!loading && !forbidden && !error && queue && queue.items.length > 0 && (
        <div className="history-table-scroll"><table><thead><tr><th>SKU</th><th>Requested</th><th>Available</th><th>Action</th></tr></thead><tbody>{queue.items.map((item) => (
          <tr key={item.pick_id}><td>{item.sku}</td><td>{item.requested_quantity}</td><td>{item.available_quantity}</td><td><a className="primary-link" href={`/pick/${encodeURIComponent(item.pick_id)}`}>Open Pick</a></td></tr>
        ))}</tbody></table></div>
      )}
      <p className="field-help">Picks with FULLY_COMPLETED or PARTIAL_INSUFFICIENT outcomes are not shown. This page does not reopen terminal Picks.</p>
    </section>
  )
}
