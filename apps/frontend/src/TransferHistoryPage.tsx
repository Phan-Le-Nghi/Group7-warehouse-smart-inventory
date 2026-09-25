import { useEffect, useState } from 'react'
import { ApiError, loadTransferHistory, TransferHistory } from './api'

type TransferHistoryPageProps = {
  onUnauthorized: () => void
}

function formatTimestamp(timestamp: string) {
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return timestamp
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed)
}

export default function TransferHistoryPage({
  onUnauthorized,
}: TransferHistoryPageProps) {
  const [history, setHistory] = useState<TransferHistory | null>(null)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')

  async function retryHistory() {
    setLoading(true)
    setForbidden(false)
    setError('')
    try {
      setHistory(await loadTransferHistory())
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 401) {
        onUnauthorized()
        return
      }
      if (loadError instanceof ApiError && loadError.status === 403) {
        setForbidden(true)
        setHistory(null)
        return
      }
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Unable to load Transfer history.',
      )
      setHistory(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    loadTransferHistory()
      .then((loaded) => {
        if (active) setHistory(loaded)
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
            : 'Unable to load Transfer history.',
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
    <section
      className="putaway-card transfer-history-card"
      aria-labelledby="transfer-history-title"
    >
      <div className="title-row">
        <div>
          <p className="eyebrow">Confirmed records</p>
          <h1 id="transfer-history-title">Transfer history</h1>
          <p className="supporting-copy">
            Review confirmed internal relocations for this warehouse.
          </p>
        </div>
        <span className="step-badge">HISTORY</span>
      </div>

      {loading && (
        <p className="status-panel" role="status">
          Loading Transfer history…
        </p>
      )}

      {!loading && forbidden && (
        <div className="forbidden-panel" role="alert">
          <p className="eyebrow">Forbidden</p>
          <h2>Manager role required</h2>
          <p className="supporting-copy">
            Your session is valid, but Transfer history is not available for
            your current role.
          </p>
        </div>
      )}

      {!loading && error && (
        <div className="error-panel" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void retryHistory()}>
            Retry
          </button>
        </div>
      )}

      {!loading && !forbidden && !error && history?.items.length === 0 && (
        <p className="status-panel">No confirmed Transfers yet.</p>
      )}

      {!loading && !forbidden && !error && history && history.items.length > 0 && (
        <div className="history-table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">SKU</th>
                <th scope="col">Source</th>
                <th scope="col">Destination</th>
                <th scope="col">Quantity</th>
                <th scope="col">Actor</th>
                <th scope="col">Transferred at</th>
              </tr>
            </thead>
            <tbody>
              {history.items.map((item) => (
                <tr key={item.transfer_id}>
                  <td>
                    <strong>{item.sku.code}</strong>
                    <small>{item.sku.id}</small>
                  </td>
                  <td>{item.source.code}</td>
                  <td>{item.destination.code}</td>
                  <td>{item.quantity}</td>
                  <td>
                    <strong>{item.transferred_by.login_identifier}</strong>
                    <small>{item.transferred_by.user_id}</small>
                  </td>
                  <td>
                    <time dateTime={item.transferred_at}>
                      {formatTimestamp(item.transferred_at)}
                    </time>
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
