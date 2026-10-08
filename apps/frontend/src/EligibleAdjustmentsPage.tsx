import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  EligibleAdjustmentRecheckList,
  loadEligibleAdjustmentRechecks,
} from './api'

type Props = { onUnauthorized: () => void }

function signed(value: number) {
  return value > 0 ? `+${value}` : String(value)
}

export default function EligibleAdjustmentsPage({ onUnauthorized }: Props) {
  const [queue, setQueue] = useState<EligibleAdjustmentRecheckList | null>(null)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')

  const loadQueue = useCallback(async () => {
    setLoading(true)
    setForbidden(false)
    setError('')
    try {
      setQueue(await loadEligibleAdjustmentRechecks())
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 401) {
        onUnauthorized()
        return
      }
      if (loadError instanceof ApiError && loadError.status === 403) {
        setForbidden(true)
        return
      }
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Unable to load eligible Adjust requests.',
      )
    } finally {
      setLoading(false)
    }
  }, [onUnauthorized])

  useEffect(() => {
    let active = true
    loadEligibleAdjustmentRechecks()
      .then((loaded) => {
        if (active) setQueue(loaded)
      })
      .catch((loadError: unknown) => {
        if (!active) return
        if (loadError instanceof ApiError && loadError.status === 401) {
          onUnauthorized()
          return
        }
        if (loadError instanceof ApiError && loadError.status === 403) {
          setForbidden(true)
          return
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Unable to load eligible Adjust requests.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [onUnauthorized])

  return (
    <section className="putaway-card adjustment-queue-card" aria-labelledby="eligible-adjustments-title">
      <div className="title-row">
        <div>
          <p className="eyebrow">Inventory corrections</p>
          <h1 id="eligible-adjustments-title">Adjust Requests</h1>
          <p className="supporting-copy">
            Create requests from manager-confirmed inventory discrepancies.
          </p>
        </div>
        <span className="step-badge">ADJUST</span>
      </div>

      {loading && <p className="status-panel" role="status">Loading eligible adjustments…</p>}
      {!loading && forbidden && (
        <div className="error-panel" role="alert">
          <h2>Warehouse Staff role required</h2>
          <p>This Adjust operation is not available for your current role.</p>
        </div>
      )}
      {!loading && error && (
        <div className="error-panel" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void loadQueue()}>Retry</button>
        </div>
      )}
      {!loading && !forbidden && !error && queue?.items.length === 0 && (
        <p className="status-panel">No eligible adjustment requests are available.</p>
      )}
      {!loading && !forbidden && !error && queue && queue.items.length > 0 && (
        <div className="history-table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">SKU / location</th>
                <th scope="col">System</th>
                <th scope="col">Physical</th>
                <th scope="col">Requested change</th>
                <th scope="col">Rechecked</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {queue.items.map((item) => (
                <tr key={item.audit_recheck_id}>
                  <td>{item.sku.code}<small>{item.location.code}</small></td>
                  <td>{item.recheck_system_quantity}</td>
                  <td>{item.recheck_physical_quantity}</td>
                  <td>{signed(item.requested_change)}</td>
                  <td>{new Date(item.rechecked_at).toLocaleString()}</td>
                  <td>
                    <a
                      className="primary-link"
                      href={`/adjustments/${encodeURIComponent(item.audit_recheck_id)}`}
                    >
                      Create Adjust Request
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
