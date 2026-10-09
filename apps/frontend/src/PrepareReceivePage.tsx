import { FormEvent, useEffect, useState } from 'react'
import {
  ApiError,
  createPreparedReceive,
  loadSkuCatalog,
  PreparedReceiveCreateResult,
  SkuCatalog,
} from './api'

type Props = { onUnauthorized: () => void }
type DraftLine = { key: number; skuId: string; quantity: string }

export default function PrepareReceivePage({ onUnauthorized }: Props) {
  const [catalog, setCatalog] = useState<SkuCatalog | null>(null)
  const [reference, setReference] = useState('')
  const [lines, setLines] = useState<DraftLine[]>([
    { key: 1, skuId: '', quantity: '' },
  ])
  const [nextKey, setNextKey] = useState(2)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PreparedReceiveCreateResult | null>(null)

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

  function updateLine(key: number, patch: Partial<DraftLine>) {
    setLines((current) => current.map((line) => line.key === key ? { ...line, ...patch } : line))
  }

  function addLine() {
    setLines((current) => [...current, { key: nextKey, skuId: '', quantity: '' }])
    setNextKey((current) => current + 1)
  }

  function reset() {
    setReference('')
    setLines([{ key: nextKey, skuId: '', quantity: '' }])
    setNextKey((current) => current + 1)
    setResult(null)
    setError('')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    const trimmedReference = reference.trim()
    const selected = lines.map((line) => line.skuId)
    const quantities = lines.map((line) => Number(line.quantity))
    if (!trimmedReference || trimmedReference.length > 255) {
      setError('Expected reference must contain from 1 to 255 characters.')
      return
    }
    if (selected.some((skuId) => !skuId)) {
      setError('Select a SKU for every Receive line.')
      return
    }
    if (new Set(selected).size !== selected.length) {
      setError('Each SKU may appear only once in a Receive.')
      return
    }
    if (lines.some((line, index) => !/^\d+$/.test(line.quantity) || quantities[index] <= 0)) {
      setError('Expected quantity must be a positive integer for every line.')
      return
    }
    setSubmitting(true)
    try {
      setResult(await createPreparedReceive({
        expected_reference: trimmedReference,
        lines: lines.map((line, index) => ({
          sku_id: line.skuId,
          expected_quantity: quantities[index],
        })),
      }))
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) onUnauthorized()
      else if (failure instanceof ApiError && failure.status === 403) setForbidden(true)
      else setError(failure instanceof Error ? failure.message : 'Unable to prepare Receive.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="putaway-card" aria-labelledby="prepare-receive-title">
      <p className="eyebrow">Purchasing supporting workflow</p>
      <h1 id="prepare-receive-title">Prepare Receive</h1>
      <p className="supporting-copy">Create expected context for Warehouse Staff without changing stock.</p>
      <p><a className="primary-link" href="/">Back to Dashboard</a></p>
      {loading && <p className="status-panel" role="status">Loading SKUs…</p>}
      {!loading && forbidden && <div className="error-panel" role="alert"><h2>Purchasing role required</h2></div>}
      {!loading && !forbidden && result && (
        <div className="success-panel" role="status">
          <h2>Prepared Receive created and ready for Warehouse Staff.</h2>
          <p>{result.expected_reference} · {result.lines.length} line{result.lines.length === 1 ? '' : 's'}</p>
          <button type="button" onClick={reset}>Prepare another Receive</button>
        </div>
      )}
      {!loading && !forbidden && !result && (
        <form onSubmit={submit} noValidate>
          <label className="receive-field">Expected reference
            <input value={reference} maxLength={255} onChange={(event) => setReference(event.target.value)} />
          </label>
          <div className="creation-lines">
            {lines.map((line, index) => {
              const selectedElsewhere = new Set(lines.filter((candidate) => candidate.key !== line.key).map((candidate) => candidate.skuId))
              return (
                <fieldset key={line.key} className="creation-line">
                  <legend>Receive line {index + 1}</legend>
                  <label className="receive-field">SKU
                    <select value={line.skuId} onChange={(event) => updateLine(line.key, { skuId: event.target.value })}>
                      <option value="">Select a SKU</option>
                      {catalog?.items.map((sku) => <option key={sku.sku_id} value={sku.sku_id} disabled={selectedElsewhere.has(sku.sku_id)}>{sku.sku}</option>)}
                    </select>
                  </label>
                  <label className="receive-field">Expected quantity
                    <input inputMode="numeric" value={line.quantity} onChange={(event) => updateLine(line.key, { quantity: event.target.value })} />
                  </label>
                  {lines.length > 1 && <button type="button" className="secondary-button" onClick={() => setLines((current) => current.filter((candidate) => candidate.key !== line.key))}>Remove line</button>}
                </fieldset>
              )
            })}
          </div>
          <button type="button" className="secondary-button" onClick={addLine}>Add line</button>
          {error && <p className="error-panel" role="alert">{error}</p>}
          <button type="submit" disabled={submitting || !catalog?.items.length}>{submitting ? 'Creating…' : 'Create'}</button>
        </form>
      )}
    </section>
  )
}
