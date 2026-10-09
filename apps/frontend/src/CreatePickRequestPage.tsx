import { FormEvent, useEffect, useState } from 'react'
import { ApiError, createPickRequest, loadSkuCatalog, PickRequestCreateResult, SkuCatalog } from './api'

type Props = { onUnauthorized: () => void }

export default function CreatePickRequestPage({ onUnauthorized }: Props) {
  const [catalog, setCatalog] = useState<SkuCatalog | null>(null)
  const [skuId, setSkuId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PickRequestCreateResult | null>(null)

  useEffect(() => {
    let active = true
    loadSkuCatalog()
      .then((loaded) => { if (active) setCatalog(loaded) })
      .catch((failure: unknown) => {
        if (!active) return
        if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
        else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
        else setError(failure instanceof Error ? failure.message : 'Unable to load SKUs.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [onUnauthorized])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (!skuId) {
      setError('Select a SKU.')
      return
    }
    if (!/^\d+$/.test(quantity) || Number(quantity) <= 0) {
      setError('Requested quantity must be a positive integer.')
      return
    }
    setSubmitting(true)
    try {
      setResult(await createPickRequest(skuId, Number(quantity)))
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
      else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
      else setError(failure instanceof Error ? failure.message : 'Unable to create Pick Request.')
    } finally {
      setSubmitting(false)
    }
  }

  function reset() {
    setSkuId('')
    setQuantity('')
    setResult(null)
    setError('')
  }

  return (
    <section className="putaway-card" aria-labelledby="create-pick-request-title">
      <p className="eyebrow">Manager supporting workflow</p>
      <h1 id="create-pick-request-title">Create Pick Request</h1>
      <p className="supporting-copy">Create actionable work for Warehouse Staff without reserving or changing stock.</p>
      <p><a className="primary-link" href="/">Back to Dashboard</a></p>
      {loading && <p className="status-panel" role="status">Loading SKUs…</p>}
      {!loading && forbidden && <div className="error-panel" role="alert"><h2>Manager role required</h2></div>}
      {!loading && !forbidden && result && (
        <div className="success-panel" role="status">
          <h2>Pick Request created and ready for Warehouse Staff.</h2>
          <p>{result.sku} × {result.requested_quantity}</p>
          <button type="button" onClick={reset}>Create another Pick Request</button>
        </div>
      )}
      {!loading && !forbidden && !result && (
        <form onSubmit={submit} noValidate>
          <label className="receive-field">SKU
            <select value={skuId} onChange={(event) => setSkuId(event.target.value)}>
              <option value="">Select a SKU</option>
              {catalog?.items.map((sku) => <option key={sku.sku_id} value={sku.sku_id}>{sku.sku}</option>)}
            </select>
          </label>
          <label className="receive-field">Requested quantity
            <input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
          </label>
          {error && <p className="error-panel" role="alert">{error}</p>}
          <button type="submit" disabled={submitting || !catalog?.items.length}>{submitting ? 'Creating…' : 'Create'}</button>
        </form>
      )}
    </section>
  )
}
