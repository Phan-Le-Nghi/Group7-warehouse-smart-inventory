import { useCallback, useEffect, useState } from 'react'
import { ApiError, loadTransferableSkus, TransferSelector } from './api'

type Props = { onUnauthorized: () => void }

export default function TransferSelectorPage({ onUnauthorized }: Props) {
  const [selector, setSelector] = useState<TransferSelector | null>(null)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')

  const loadSelector = useCallback(async () => {
    setLoading(true); setForbidden(false); setError('')
    try { setSelector(await loadTransferableSkus()) }
    catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
      else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
      else setError(failure instanceof Error ? failure.message : 'Unable to load transferable stock.')
    } finally { setLoading(false) }
  }, [onUnauthorized])

  useEffect(() => {
    let active = true
    loadTransferableSkus()
      .then((loaded) => { if (active) setSelector(loaded) })
      .catch((failure: unknown) => {
        if (!active) return
        if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
        else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
        else setError(failure instanceof Error ? failure.message : 'Unable to load transferable stock.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [onUnauthorized])

  return (
    <section className="putaway-card" aria-labelledby="transfer-selector-title">
      <div className="title-row"><div><p className="eyebrow">Warehouse Staff stock selector</p><h1 id="transfer-selector-title">Transfer</h1><p className="supporting-copy">Select a SKU with positive stock at a tracked source location.</p></div><span className="step-badge">TRANSFER</span></div>
      {loading && <p className="status-panel" role="status">Loading transferable stock…</p>}
      {!loading && forbidden && <div className="error-panel" role="alert"><h2>Warehouse Staff role required</h2></div>}
      {!loading && error && <div className="error-panel" role="alert"><p>{error}</p><button type="button" onClick={() => void loadSelector()}>Retry</button></div>}
      {!loading && !forbidden && !error && selector?.items.length === 0 && <p className="status-panel">No SKU currently has a valid Transfer source and destination.</p>}
      {!loading && !forbidden && !error && selector && selector.items.length > 0 && (
        <div className="history-table-scroll"><table><thead><tr><th>SKU</th><th>Backroom</th><th>Sales Shelf</th><th>Total</th><th>Action</th></tr></thead><tbody>{selector.items.map((item) => {
          const quantity = (code: string) => item.locations.find((location) => location.code === code)?.available_quantity ?? 0
          return <tr key={item.sku_id}><td>{item.sku}</td><td>{quantity('BACKROOM')}</td><td>{quantity('SALES_SHELF')}</td><td>{item.warehouse_total}</td><td><a className="primary-link" href={`/transfer/${encodeURIComponent(item.sku_id)}`}>Open Transfer</a></td></tr>
        })}</tbody></table></div>
      )}
    </section>
  )
}
