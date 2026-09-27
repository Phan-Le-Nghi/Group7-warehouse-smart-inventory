import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import {
  AdjustmentContext,
  AdjustmentResult,
  ApiError,
  loadAdjustmentContext,
  submitAdjustmentRequest,
} from './api'

type AdjustmentPageProps = {
  auditRecheckId: string
  onUnauthorized: () => void
}

type SubmissionAttempt = {
  normalizedReason: string
  key: string
}

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `adjustment-${Date.now()}`
}

function formatSigned(value: number) {
  return value > 0 ? `+${value}` : String(value)
}

export default function AdjustmentPage({
  auditRecheckId,
  onUnauthorized,
}: AdjustmentPageProps) {
  const [context, setContext] = useState<AdjustmentContext | null>(null)
  const [result, setResult] = useState<AdjustmentResult | null>(null)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [notEligible, setNotEligible] = useState(false)
  const [error, setError] = useState('')
  const attempt = useRef<SubmissionAttempt | null>(null)

  const handleFailure = useCallback((failure: unknown, fallback: string) => {
    if (failure instanceof ApiError && failure.status === 401) {
      onUnauthorized()
      return 'handled'
    }
    if (failure instanceof ApiError && failure.status === 403) {
      setForbidden(true)
      return 'handled'
    }
    if (
      failure instanceof ApiError &&
      (failure.code === 'AUDIT_RECHECK_NOT_FOUND' ||
        failure.code === 'ADJUSTMENT_NOT_ELIGIBLE')
    ) {
      setNotEligible(true)
      return 'handled'
    }
    return failure instanceof Error ? failure.message : fallback
  }, [onUnauthorized])

  const loadContext = useCallback(async () => {
    setLoading(true)
    setForbidden(false)
    setNotEligible(false)
    setError('')
    try {
      setContext(await loadAdjustmentContext(auditRecheckId))
    } catch (loadError) {
      const message = handleFailure(
        loadError,
        'Unable to load the Adjust request context.',
      )
      if (message !== 'handled') setError(message)
      setContext(null)
    } finally {
      setLoading(false)
    }
  }, [auditRecheckId, handleFailure])

  useEffect(() => {
    let active = true
    loadAdjustmentContext(auditRecheckId)
      .then((loaded) => {
        if (active) setContext(loaded)
      })
      .catch((loadError: unknown) => {
        if (!active) return
        const message = handleFailure(
          loadError,
          'Unable to load the Adjust request context.',
        )
        if (message !== 'handled') setError(message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [auditRecheckId, handleFailure])

  function changeReason(value: string) {
    setReason(value)
    attempt.current = null
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!context || context.existing_adjustment || submitting) return
    const normalizedReason = reason.trim()
    if (!normalizedReason) {
      setError('Reason is required.')
      return
    }
    if (normalizedReason.length > 500) {
      setError('Reason must not exceed 500 characters after trimming.')
      return
    }
    if (!attempt.current) {
      attempt.current = {
        normalizedReason,
        key: createIdempotencyKey(),
      }
    }
    setSubmitting(true)
    setError('')
    try {
      const created = await submitAdjustmentRequest(
        auditRecheckId,
        normalizedReason,
        attempt.current.key,
      )
      attempt.current = null
      setResult(created)
    } catch (submitError) {
      if (
        submitError instanceof ApiError &&
        submitError.code === 'ADJUSTMENT_ALREADY_EXISTS'
      ) {
        attempt.current = null
        await loadContext()
        return
      }
      const message = handleFailure(
        submitError,
        'Unable to create the Adjust request.',
      )
      if (message !== 'handled') setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  const persisted = result ?? context?.existing_adjustment ?? null

  return (
    <section
      className="putaway-card adjustment-card"
      aria-labelledby="adjustment-title"
    >
      <div className="title-row">
        <div>
          <p className="eyebrow">Warehouse Staff request</p>
          <h1 id="adjustment-title">Create Adjust request</h1>
          <p className="supporting-copy">
            Review immutable Audit evidence and explain the requested correction.
          </p>
        </div>
        <span className="step-badge">ADJUST</span>
      </div>

      {loading && (
        <p className="status-panel" role="status">
          Loading Adjust context…
        </p>
      )}
      {!loading && forbidden && (
        <div className="forbidden-panel" role="alert">
          <p className="eyebrow">Forbidden</p>
          <h2>Warehouse Staff role required</h2>
          <p>This operation is not available for your current role.</p>
        </div>
      )}
      {!loading && notEligible && (
        <div className="error-panel" role="alert">
          <p>This Audit recheck is unavailable or is not eligible for Adjust.</p>
        </div>
      )}
      {!loading && error && !context && (
        <div className="error-panel" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void loadContext()}>
            Retry
          </button>
        </div>
      )}

      {!loading && context && (
        <>
          <div className="audit-evidence-grid">
            <section aria-labelledby="adjust-original-title">
              <p className="eyebrow">ORIGINAL AUDIT</p>
              <h2 id="adjust-original-title">
                {context.sku.code} at {context.location.code}
              </h2>
              <dl className="item-summary audit-evidence-summary">
                <div>
                  <dt>System quantity</dt>
                  <dd>{context.original_audit.system_quantity}</dd>
                </div>
                <div>
                  <dt>Physical quantity</dt>
                  <dd>{context.original_audit.physical_quantity}</dd>
                </div>
                <div>
                  <dt>Discrepancy</dt>
                  <dd>{context.original_audit.quantity_discrepancy}</dd>
                </div>
              </dl>
            </section>

            <section aria-labelledby="adjust-recheck-title">
              <p className="eyebrow">MANAGER RECHECK</p>
              <h2 id="adjust-recheck-title">Confirmed mismatch evidence</h2>
              <dl className="item-summary audit-evidence-summary">
                <div>
                  <dt>System quantity</dt>
                  <dd>{context.recheck.recheck_system_quantity}</dd>
                </div>
                <div>
                  <dt>Physical quantity</dt>
                  <dd>{context.recheck.recheck_physical_quantity}</dd>
                </div>
                <div>
                  <dt>Requested change</dt>
                  <dd data-testid="requested-change">
                    {formatSigned(context.requested_change)}
                  </dd>
                </div>
              </dl>
              <p className="field-help">
                Requested change is derived by the server and cannot be edited.
              </p>
            </section>
          </div>

          <p className="review-required">
            Stock remains unchanged. A Manager decision and apply step are required
            before any stock quantity can change.
          </p>

          {persisted ? (
            <section className="success-panel" aria-live="polite">
              <p className="eyebrow">Adjust request recorded</p>
              <h2>{persisted.status}</h2>
              <p>{persisted.reason}</p>
              <p>Requested change: {formatSigned(persisted.requested_change)}</p>
              <p>Stock was not changed by this request.</p>
            </section>
          ) : (
            <form onSubmit={handleSubmit}>
              <label htmlFor="adjustment-reason">Reason</label>
              <textarea
                id="adjustment-reason"
                value={reason}
                disabled={submitting}
                onChange={(event) => changeReason(event.target.value)}
              />
              <p className="field-help">
                Required free text, up to 500 characters after trimming.
              </p>
              {error && (
                <div className="error-panel" role="alert">
                  <p>{error}</p>
                </div>
              )}
              <button type="submit" disabled={submitting}>
                {submitting ? 'Submitting request…' : 'Create Adjust request'}
              </button>
            </form>
          )}
        </>
      )}
    </section>
  )
}
