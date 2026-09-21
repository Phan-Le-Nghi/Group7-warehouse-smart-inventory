import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  loadPickContext,
  PickAllocationCommand,
  PickContext,
  PickResult,
  submitPick,
} from './api'

type PickPageProps = {
  pickId: string
  onUnauthorized: () => void
}

const locationLabels: Record<string, string> = {
  BACKROOM: 'Backroom',
  SALES_SHELF: 'Sales Shelf',
}

export default function PickPage({ pickId, onUnauthorized }: PickPageProps) {
  const [context, setContext] = useState<PickContext | null>(null)
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [partialConfirmation, setPartialConfirmation] = useState(false)
  const [result, setResult] = useState<PickResult | null>(null)

  async function loadContext() {
    setLoading(true)
    setError('')
    try {
      setContext(await loadPickContext(pickId))
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Unable to load Pick context.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    loadPickContext(pickId)
      .then((loaded) => {
        if (active) setContext(loaded)
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
            : 'Unable to load Pick context.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [onUnauthorized, pickId])

  const pickedQuantity = useMemo(
    () =>
      Object.entries(selected).reduce((total, [locationId, isSelected]) => {
        const raw = quantities[locationId] ?? ''
        return isSelected && /^\d+$/.test(raw) ? total + Number(raw) : total
      }, 0),
    [quantities, selected],
  )
  const remainingQuantity = context
    ? Math.max(context.requested_quantity - pickedQuantity, 0)
    : 0

  function updateSelection(locationId: string, isSelected: boolean) {
    setSelected((current) => ({ ...current, [locationId]: isSelected }))
    setPartialConfirmation(false)
    setError('')
  }

  function updateQuantity(locationId: string, value: string) {
    setQuantities((current) => ({ ...current, [locationId]: value }))
    setPartialConfirmation(false)
    setError('')
  }

  function validatedAllocations(): PickAllocationCommand[] | null {
    if (!context) return null
    const locations = context.locations.filter((location) => selected[location.id])
    if (locations.length === 0) {
      setError('Select at least one source location.')
      return null
    }
    const invalid = locations.some(
      (location) => !/^[1-9]\d*$/.test(quantities[location.id] ?? ''),
    )
    if (invalid) {
      setError('Each selected source quantity must be a positive integer.')
      return null
    }
    const allocations = locations.map((location) => ({
      source_location_id: location.id,
      quantity: Number(quantities[location.id]),
    }))
    const total = allocations.reduce((sum, allocation) => sum + allocation.quantity, 0)
    if (total > context.requested_quantity) {
      setError('Picked quantity cannot exceed the requested quantity.')
      return null
    }
    return allocations
  }

  async function confirm(allocations: PickAllocationCommand[]) {
    setSubmitting(true)
    setError('')
    try {
      setResult(await submitPick(pickId, allocations))
      setPartialConfirmation(false)
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Unable to confirm Pick.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!context || submitting) return
    const allocations = validatedAllocations()
    if (!allocations) return
    const total = allocations.reduce((sum, allocation) => sum + allocation.quantity, 0)
    if (total < context.requested_quantity) {
      setPartialConfirmation(true)
      return
    }
    await confirm(allocations)
  }

  async function handlePartialConfirmation() {
    const allocations = validatedAllocations()
    if (!allocations) return
    await confirm(allocations)
  }

  return (
    <section className="putaway-card pick-card" aria-labelledby="pick-title">
      <div className="title-row">
        <div>
          <p className="eyebrow">Source allocation</p>
          <h1 id="pick-title">Confirm Pick</h1>
          <p className="supporting-copy">
            Select each source and enter the quantity to pick.
          </p>
        </div>
        <span className="step-badge">PICK</span>
      </div>

      {loading && (
        <p className="status-panel" role="status">
          Loading Pick context…
        </p>
      )}

      {!loading && !context && error && (
        <p className="error-panel" role="alert">
          {error}
        </p>
      )}

      {context && context.outcome && !result && (
        <section className="recorded-panel" aria-live="polite">
          <p className="eyebrow">Pick already recorded</p>
          <h2>{context.outcome}</h2>
          <p>This prepared Pick cannot be confirmed again.</p>
        </section>
      )}

      {context && !context.outcome && !result && (
        <form onSubmit={handleSubmit}>
          <dl className="item-summary pick-summary">
            <div>
              <dt>SKU</dt>
              <dd>{context.sku}</dd>
            </div>
            <div>
              <dt>Requested</dt>
              <dd>{context.requested_quantity}</dd>
            </div>
            <div>
              <dt>Warehouse total</dt>
              <dd>{context.warehouse_total}</dd>
            </div>
          </dl>

          <fieldset>
            <legend>Source allocations</legend>
            <p className="field-help">No source is allocated automatically.</p>
            <div className="pick-locations">
              {context.locations.map((location) => (
                <div className="pick-location" key={location.id}>
                  <label className="pick-source-choice">
                    <input
                      type="checkbox"
                      checked={Boolean(selected[location.id])}
                      onChange={(event) =>
                        updateSelection(location.id, event.target.checked)
                      }
                    />
                    <span>
                      <strong>{locationLabels[location.code] ?? location.code}</strong>
                      <small>{location.available_quantity} available</small>
                    </span>
                  </label>
                  <label className="receive-field">
                    Quantity from {locationLabels[location.code] ?? location.code}
                    <input
                      inputMode="numeric"
                      value={quantities[location.id] ?? ''}
                      disabled={!selected[location.id]}
                      onChange={(event) =>
                        updateQuantity(location.id, event.target.value)
                      }
                    />
                  </label>
                </div>
              ))}
            </div>
          </fieldset>

          <dl className="pick-totals" aria-live="polite">
            <div><dt>Requested quantity</dt><dd>{context.requested_quantity}</dd></div>
            <div><dt>Picked quantity</dt><dd>{pickedQuantity}</dd></div>
            <div><dt>Remaining quantity</dt><dd>{remainingQuantity}</dd></div>
          </dl>

          {partialConfirmation && (
            <section className="partial-confirmation" aria-labelledby="partial-title">
              <h2 id="partial-title">Confirm partial Pick</h2>
              <p>
                Pick is not fully completed. {remainingQuantity} units remain
                unfulfilled.
              </p>
              <dl className="pick-totals">
                <div><dt>Requested quantity</dt><dd>{context.requested_quantity}</dd></div>
                <div><dt>Picked quantity</dt><dd>{pickedQuantity}</dd></div>
                <div><dt>Remaining quantity</dt><dd>{remainingQuantity}</dd></div>
              </dl>
              <button
                type="button"
                disabled={submitting}
                onClick={handlePartialConfirmation}
              >
                {submitting ? 'Confirming…' : 'Confirm partial Pick'}
              </button>
            </section>
          )}

          {error && (
            <div className="error-panel" role="alert">
              <p>{error}</p>
              {error.toLowerCase().includes('stock') && (
                <button type="button" onClick={loadContext}>
                  Reload availability
                </button>
              )}
            </div>
          )}

          {!partialConfirmation && (
            <button type="submit" disabled={submitting}>
              {submitting ? 'Confirming…' : 'Review and confirm Pick'}
            </button>
          )}
        </form>
      )}

      {result && (
        <section className="success-panel" aria-live="polite">
          <span className="success-icon" aria-hidden="true">✓</span>
          <p className="eyebrow">
            {result.outcome === 'FULLY_COMPLETED'
              ? 'Pick fully completed'
              : 'Partial Pick recorded'}
          </p>
          <h2>
            {result.picked_quantity} of {result.requested_quantity} units picked
          </h2>
          {result.outcome === 'PARTIAL_INSUFFICIENT' && (
            <p>
              Pick is not fully completed. {result.remaining_quantity} units remain
              unfulfilled.
            </p>
          )}
          <dl>
            <div><dt>Remaining quantity</dt><dd>{result.remaining_quantity}</dd></div>
            <div><dt>Warehouse total</dt><dd>{result.warehouse_total}</dd></div>
          </dl>
        </section>
      )}
    </section>
  )
}
