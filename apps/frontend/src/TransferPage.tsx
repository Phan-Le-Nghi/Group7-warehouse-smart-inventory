import { FormEvent, useEffect, useRef, useState } from 'react'
import {
  ApiError,
  loadTransferContext,
  submitTransfer,
  TransferCommand,
  TransferContext,
  TransferResult,
} from './api'

type TransferPageProps = {
  skuId: string
  onUnauthorized: () => void
}

type SubmissionAttempt = {
  fingerprint: string
  key: string
}

const locationLabels: Record<string, string> = {
  BACKROOM: 'Backroom',
  SALES_SHELF: 'Sales Shelf',
}

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `transfer-${Date.now()}`
}

function fingerprint(command: TransferCommand) {
  return JSON.stringify(command)
}

export default function TransferPage({ skuId, onUnauthorized }: TransferPageProps) {
  const [context, setContext] = useState<TransferContext | null>(null)
  const [sourceId, setSourceId] = useState('')
  const [destinationId, setDestinationId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<TransferResult | null>(null)
  const attempt = useRef<SubmissionAttempt | null>(null)

  async function loadContext() {
    setLoading(true)
    setError('')
    try {
      const loaded = await loadTransferContext(skuId)
      setContext(loaded)
      setSourceId((current) => current || loaded.locations[0]?.id || '')
      setDestinationId((current) => current || loaded.locations[1]?.id || '')
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Unable to load Transfer context.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    loadTransferContext(skuId)
      .then((loaded) => {
        if (!active) return
        setContext(loaded)
        setSourceId(loaded.locations[0]?.id || '')
        setDestinationId(loaded.locations[1]?.id || '')
      })
      .catch((loadError: unknown) => {
        if (!active) return
        if (loadError instanceof ApiError && loadError.status === 401) {
          onUnauthorized()
          return
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Unable to load Transfer context.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [onUnauthorized, skuId])

  function edit(setter: (value: string) => void, value: string) {
    setter(value)
    attempt.current = null
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!context || submitting) return
    if (!sourceId || !destinationId) {
      setError('Select both a source and a destination location.')
      return
    }
    if (sourceId === destinationId) {
      setError('Source and destination locations must be different.')
      return
    }
    if (!/^[1-9]\d*$/.test(quantity)) {
      setError('Quantity must be a positive integer.')
      return
    }
    const command: TransferCommand = {
      sku_id: context.sku_id,
      source_location_id: sourceId,
      destination_location_id: destinationId,
      quantity: Number(quantity),
    }
    const commandFingerprint = fingerprint(command)
    if (!attempt.current || attempt.current.fingerprint !== commandFingerprint) {
      attempt.current = {
        fingerprint: commandFingerprint,
        key: createIdempotencyKey(),
      }
    }

    setSubmitting(true)
    setError('')
    try {
      setResult(await submitTransfer(command, attempt.current.key))
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Unable to confirm Transfer.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  const source = context?.locations.find((location) => location.id === sourceId)

  return (
    <section className="putaway-card transfer-card" aria-labelledby="transfer-title">
      <div className="title-row">
        <div>
          <p className="eyebrow">Internal relocation</p>
          <h1 id="transfer-title">Confirm Transfer</h1>
          <p className="supporting-copy">
            Move one SKU between tracked locations in this warehouse.
          </p>
        </div>
        <span className="step-badge">TRANSFER</span>
      </div>

      {loading && <p role="status" className="status-panel">Loading Transfer context…</p>}
      {!loading && !context && <p role="alert" className="error-panel">{error}</p>}

      {context && !result && (
        <form onSubmit={handleSubmit}>
          <dl className="item-summary">
            <div><dt>SKU</dt><dd>{context.sku}</dd></div>
            <div><dt>Warehouse total</dt><dd>{context.warehouse_total}</dd></div>
          </dl>

          <label>
            Source location
            <select
              aria-label="Source location"
              value={sourceId}
              disabled={submitting}
              onChange={(event) => edit(setSourceId, event.target.value)}
            >
              {context.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {locationLabels[location.code] ?? location.code} — {location.available_quantity} available
                </option>
              ))}
            </select>
          </label>
          {source && <p className="field-help">Available: {source.available_quantity}</p>}

          <label>
            Destination location
            <select
              aria-label="Destination location"
              value={destinationId}
              disabled={submitting}
              onChange={(event) => edit(setDestinationId, event.target.value)}
            >
              {context.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {locationLabels[location.code] ?? location.code}
                </option>
              ))}
            </select>
          </label>

          <label>
            Quantity
            <input
              aria-label="Quantity"
              inputMode="numeric"
              value={quantity}
              disabled={submitting}
              onChange={(event) => edit(setQuantity, event.target.value)}
            />
          </label>

          {error && (
            <div className="error-panel" role="alert">
              <p>{error}</p>
              <button type="button" onClick={() => void loadContext()}>
                Reload availability
              </button>
            </div>
          )}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Confirming…' : 'Confirm Transfer'}
          </button>
        </form>
      )}

      {result && (
        <section className="success-panel" aria-live="polite">
          <p className="eyebrow">Transfer confirmed</p>
          <h2>{result.quantity} units transferred</h2>
          <p>{result.source_location} → {result.destination_location}</p>
          <dl>
            <div><dt>Source stock</dt><dd>{result.stock.source_quantity}</dd></div>
            <div><dt>Destination stock</dt><dd>{result.stock.destination_quantity}</dd></div>
            <div><dt>Warehouse total</dt><dd>{result.stock.warehouse_total}</dd></div>
          </dl>
        </section>
      )}
    </section>
  )
}
