import { FormEvent, useEffect, useState } from 'react'
import {
  ApiError,
  loadPutawayContext,
  PutawayContext,
  PutawayResult,
  submitPutaway,
} from './api'
import type { Actor } from './auth'
import AuditDiscrepancyPage from './AuditDiscrepancyPage'
import AuditPage from './AuditPage'
import PickPage from './PickPage'
import ReceivePage from './ReceivePage'
import TransferHistoryPage from './TransferHistoryPage'
import TransferPage from './TransferPage'

type AppProps = {
  actor: Actor
  onLogout: () => void | Promise<void>
  onUnauthorized: () => void
  receiveId?: string
  receiveLineId?: string
}

const locationLabels: Record<string, string> = {
  BACKROOM: 'Backroom',
  SALES_SHELF: 'Sales Shelf',
}

const roleLabels: Record<Actor['role'], string> = {
  WAREHOUSE_STAFF: 'Warehouse Staff',
  MANAGER: 'Manager',
  PURCHASING: 'Purchasing',
  ADMIN: 'Admin',
}

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `putaway-${Date.now()}`
}

function App({
  actor,
  onLogout,
  onUnauthorized,
  receiveId = import.meta.env.VITE_RECEIVE_ID,
  receiveLineId = import.meta.env.VITE_RECEIVE_LINE_ID,
}: AppProps) {
  const currentPath = window.location.pathname.replace(/\/+$/, '') || '/'
  const isReceivePage = currentPath === '/receive'
  const isTransferHistoryPage = currentPath === '/transfers/history'
  const isAuditPage = currentPath === '/audits/new'
  const isAuditDiscrepancyPage = currentPath === '/audit-discrepancies'
  const pickPathMatch = window.location.pathname.match(/^\/pick\/([^/]+)\/?$/)
  const pickId = pickPathMatch ? decodeURIComponent(pickPathMatch[1]) : null
  const transferPathMatch = window.location.pathname.match(/^\/transfer\/([^/]+)\/?$/)
  const transferSkuId = transferPathMatch
    ? decodeURIComponent(transferPathMatch[1])
    : null
  const [context, setContext] = useState<PutawayContext | null>(null)
  const [destinationId, setDestinationId] = useState('')
  const [result, setResult] = useState<PutawayResult | null>(null)
  const [error, setError] = useState(() =>
    receiveLineId ||
    isReceivePage ||
    isTransferHistoryPage ||
    isAuditPage ||
    isAuditDiscrepancyPage ||
    pickId ||
    transferSkuId
      ? ''
      : 'Putaway context is not configured.',
  )
  const [submitting, setSubmitting] = useState(false)
  const [idempotencyKey] = useState(createIdempotencyKey)

  useEffect(() => {
    if (
      isReceivePage ||
      isTransferHistoryPage ||
      isAuditPage ||
      isAuditDiscrepancyPage ||
      pickId ||
      transferSkuId ||
      !receiveLineId ||
      actor.role !== 'WAREHOUSE_STAFF'
    ) return

    let active = true
    loadPutawayContext(receiveLineId)
      .then((loaded) => {
        if (active) {
          setContext(loaded)
          setDestinationId(loaded.locations[0]?.id ?? '')
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
  }, [
    actor.role,
    isReceivePage,
    isTransferHistoryPage,
    isAuditPage,
    isAuditDiscrepancyPage,
    onUnauthorized,
    pickId,
    receiveLineId,
    transferSkuId,
  ])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!context || !destinationId || submitting) return

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
    <main className="page-shell">
      <header className="app-header">
        <div className="brand-mark" aria-hidden="true">
          W
        </div>
        <div>
          <p className="eyebrow">MAIN warehouse</p>
          <p className="brand-name">Smart Inventory</p>
        </div>
        <span className="role-chip">{roleLabels[actor.role]}</span>
        <button className="logout-button" type="button" onClick={onLogout}>
          Sign out
        </button>
      </header>

      {isAuditDiscrepancyPage ? (
        <AuditDiscrepancyPage onUnauthorized={onUnauthorized} />
      ) : isAuditPage && actor.role === 'WAREHOUSE_STAFF' ? (
        <AuditPage onUnauthorized={onUnauthorized} />
      ) : isAuditPage ? (
        <section className="putaway-card forbidden-panel">
          <p className="eyebrow">Forbidden</p>
          <h1>Warehouse Staff role required</h1>
          <p>This Audit operation is not available for your current role.</p>
        </section>
      ) : isTransferHistoryPage ? (
        <TransferHistoryPage onUnauthorized={onUnauthorized} />
      ) : transferSkuId && actor.role === 'WAREHOUSE_STAFF' ? (
        <TransferPage skuId={transferSkuId} onUnauthorized={onUnauthorized} />
      ) : pickId && actor.role === 'WAREHOUSE_STAFF' ? (
        <PickPage pickId={pickId} onUnauthorized={onUnauthorized} />
      ) : isReceivePage && actor.role === 'WAREHOUSE_STAFF' ? (
        <ReceivePage receiveId={receiveId} onUnauthorized={onUnauthorized} />
      ) : (
      <section className="putaway-card" aria-labelledby="putaway-title">
        {actor.role !== 'WAREHOUSE_STAFF' ? (
          <div className="forbidden-panel">
            <p className="eyebrow">Forbidden</p>
            <h1 id="putaway-title">Warehouse Staff role required</h1>
            <p className="supporting-copy">
              Your session is valid, but this operation is not available for
              your current role.
            </p>
          </div>
        ) : (
          <>
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
          </>
        )}
      </section>
      )}
    </main>
  )
}

export default App
