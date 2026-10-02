import { FormEvent, useEffect, useState } from 'react'
import {
  ApiError,
  loadPutawayContext,
  PutawayContext,
  PutawayResult,
  submitPutaway,
} from './api'

type PutawayPageProps = {
  onUnauthorized: () => void
  receiveLineId?: string
}

const locationLabels: Record<string, string> = {
  BACKROOM: 'Backroom',
  SALES_SHELF: 'Sales Shelf',
}

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `putaway-${Date.now()}`
}

export default function PutawayPage({
  onUnauthorized,
  receiveLineId,
}: PutawayPageProps) {
  const [context, setContext] = useState<PutawayContext | null>(null)
  const [destinationId, setDestinationId] = useState('')
  const [result, setResult] = useState<PutawayResult | null>(null)
  const [error, setError] = useState(() =>
    receiveLineId ? '' : 'Putaway context is not configured.',
  )
  const [submitting, setSubmitting] = useState(false)
  const [idempotencyKey] = useState(createIdempotencyKey)

  useEffect(() => {
    if (!receiveLineId) return

    let active = true
    loadPutawayContext(receiveLineId)
      .then((loaded) => {
        if (active) {
          setContext(loaded)
          setDestinationId(
            loaded.eligible_quantity > 0 ? (loaded.locations[0]?.id ?? '') : '',
          )
        }
      })
      .catch((loadError: unknown) => {
        if (active) {
          if (loadError instanceof ApiError && loadError.status === 401) {
            onUnauthorized()
            return
          }
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Unable to load Putaway context.',
          )
        }
      })

    return () => {
      active = false
    }
  }, [onUnauthorized, receiveLineId])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (
      !context ||
      context.eligible_quantity <= 0 ||
      !destinationId ||
      submitting
    )
      return

    setSubmitting(true)
    setError('')
    try {
      setResult(await submitPutaway(context, destinationId, idempotencyKey))
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Unable to confirm Putaway.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="putaway-card" aria-labelledby="putaway-title">
      <div className="title-row">
        <div>
          <p className="eyebrow">Initial placement</p>
          <h1 id="putaway-title">Confirm Putaway</h1>
          <p className="supporting-copy">
            Select the tracked location that will receive this stock.
          </p>
        </div>
        <span className="step-badge">PUTAWAY</span>
      </div>

      {!context && !error && (
        <p className="status-panel" role="status">
          Loading Putaway context…
        </p>
      )}

      {context && !result && (
        <form onSubmit={handleSubmit}>
          <dl className="item-summary">
            <div>
              <dt>SKU</dt>
              <dd>{context.sku}</dd>
            </div>
            <div>
              <dt>Eligible quantity</dt>
              <dd>
                <strong>{context.eligible_quantity}</strong> units
              </dd>
            </div>
          </dl>

          {context.eligible_quantity <= 0 ? (
            <p className="status-panel" role="status">
              This receive line has been fully put away.
            </p>
          ) : (
            <>
              <fieldset>
                <legend>Destination location</legend>
                <p className="field-help">Choose one internal location.</p>
                <div className="location-grid">
                  {context.locations.map((location) => (
                    <label className="location-option" key={location.id}>
                      <input
                        type="radio"
                        name="destination"
                        value={location.id}
                        checked={destinationId === location.id}
                        onChange={() => setDestinationId(location.id)}
                      />
                      <span>
                        <strong>
                          {locationLabels[location.code] ?? location.code}
                        </strong>
                        <small>{location.code}</small>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>

              {error && (
                <p className="error-panel" role="alert">
                  {error}
                </p>
              )}

              <button type="submit" disabled={!destinationId || submitting}>
                {submitting ? 'Confirming…' : 'Confirm Putaway'}
              </button>
            </>
          )}
        </form>
      )}

      {!context && error && (
        <p className="error-panel" role="alert">
          {error}
        </p>
      )}

      {result && (
        <section className="success-panel" aria-live="polite">
          <span className="success-icon" aria-hidden="true">
            ✓
          </span>
          <p className="eyebrow">Putaway confirmed</p>
          <h2>
            {result.quantity} units placed in{' '}
            {locationLabels[result.destination_location] ??
              result.destination_location}
          </h2>
          <dl>
            <div>
              <dt>Destination stock</dt>
              <dd>{result.stock.destination_quantity}</dd>
            </div>
            <div>
              <dt>Warehouse total</dt>
              <dd>{result.stock.warehouse_total}</dd>
            </div>
          </dl>
        </section>
      )}
    </section>
  )
}
