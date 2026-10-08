import { useCallback, useEffect, useState } from 'react'
import { ApiError, loadPreparedReceives, PreparedReceiveQueue } from './api'

type Props = { onUnauthorized: () => void }

export default function ReceiveQueuePage({ onUnauthorized }: Props) {
  const [queue, setQueue] = useState<PreparedReceiveQueue | null>(null)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')

  const loadQueue = useCallback(async () => {
    setLoading(true)
    setForbidden(false)
    setError('')
    try {
      setQueue(await loadPreparedReceives())
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        onUnauthorized()
      } else if (failure instanceof ApiError && failure.status === 403) {
        setForbidden(true)
      } else {
        setError(failure instanceof Error ? failure.message : 'Unable to load prepared Receives.')
      }
    } finally {
      setLoading(false)
    }
  }, [onUnauthorized])

  useEffect(() => {
    let active = true
    loadPreparedReceives()
      .then((loaded) => { if (active) setQueue(loaded) })
      .catch((failure: unknown) => {
        if (!active) return
        if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
        else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
        else setError(failure instanceof Error ? failure.message : 'Unable to load prepared Receives.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [onUnauthorized])

  return (
    <section className="putaway-card" aria-labelledby="receive-queue-title">
      <div className="title-row">
        <div>
          <p className="eyebrow">Warehouse Staff work queue</p>
          <h1 id="receive-queue-title">Receive</h1>
          <p className="supporting-copy">Select a prepared Receive that has not been recorded.</p>
        </div>
        <span className="step-badge">RECEIVE</span>
      </div>
      {loading && <p className="status-panel" role="status">Loading prepared Receives…</p>}
      {!loading && forbidden && <div className="error-panel" role="alert"><h2>Warehouse Staff role required</h2></div>}
      {!loading && error && <div className="error-panel" role="alert"><p>{error}</p><button type="button" onClick={() => void loadQueue()}>Retry</button></div>}
      {!loading && !forbidden && !error && queue?.items.length === 0 && <p className="status-panel">No prepared Receives are waiting to be recorded.</p>}
      {!loading && !forbidden && !error && queue && queue.items.length > 0 && (
        <div className="history-table-scroll">
          <table>
            <thead><tr><th>Reference</th><th>Expected items</th><th>Action</th></tr></thead>
            <tbody>{queue.items.map((item) => (
              <tr key={item.receive_id}>
                <td>{item.expected_reference}</td>
                <td>{item.lines.map((line) => `${line.sku} × ${line.expected_quantity}`).join(', ')}</td>
                <td><a className="primary-link" href={`/receive/${encodeURIComponent(item.receive_id)}`}>Record Receive</a></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}
