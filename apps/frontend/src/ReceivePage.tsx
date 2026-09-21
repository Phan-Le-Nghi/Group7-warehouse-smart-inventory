import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  acknowledgeReferenceMismatch,
  ApiError,
  loadReceiveContext,
  ReceiveContext,
  recordReceive,
} from './api'

type ReceivePageProps = {
  onUnauthorized: () => void
  receiveId?: string
}

function signedQuantity(value: number) {
  return value > 0 ? `+${value}` : String(value)
}

export default function ReceivePage({
  onUnauthorized,
  receiveId = import.meta.env.VITE_RECEIVE_ID,
}: ReceivePageProps) {
  const [context, setContext] = useState<ReceiveContext | null>(null)
  const [documentReference, setDocumentReference] = useState('')
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState(() =>
    receiveId ? '' : 'Receive context is not configured.',
  )
  const [submitting, setSubmitting] = useState(false)
  const [reviewing, setReviewing] = useState(false)

  useEffect(() => {
    if (!receiveId) return
    let active = true
    loadReceiveContext(receiveId)
      .then((loaded) => {
        if (!active) return
        setContext(loaded)
        setDocumentReference(loaded.reference.document ?? '')
        setQuantities(
          Object.fromEntries(
            loaded.lines.map((line) => [
              line.receive_line_id,
              line.actual_quantity === null ? '' : String(line.actual_quantity),
            ]),
          ),
        )
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
            : 'Unable to load Receive context.',
        )
      })
    return () => {
      active = false
    }
  }, [onUnauthorized, receiveId])

  const previews = useMemo(() => {
    if (!context) return {}
    return Object.fromEntries(
      context.lines.map((line) => {
        const raw = quantities[line.receive_line_id] ?? ''
        const valid = /^\d+$/.test(raw)
        return [
          line.receive_line_id,
          valid ? Number(raw) - line.expected_quantity : null,
        ]
      }),
    ) as Record<string, number | null>
  }, [context, quantities])

  function validate(): boolean {
    if (!context) return false
    const nextErrors: Record<string, string> = {}
    if (!documentReference.trim()) {
      nextErrors.document_reference = 'Document reference is required.'
    }
    for (const line of context.lines) {
      const value = quantities[line.receive_line_id] ?? ''
      if (!/^\d+$/.test(value)) {
        nextErrors[line.receive_line_id] =
          'Actual quantity must be a non-negative integer.'
      }
    }
    setFieldErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      setError('Check the highlighted Receive fields.')
      return false
    }
    return true
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!context || submitting || !validate()) return
    setSubmitting(true)
    setError('')
    try {
      const recorded = await recordReceive({
        receive_id: context.receive_id,
        document_reference: documentReference.trim(),
        lines: context.lines.map((line) => ({
          receive_line_id: line.receive_line_id,
          sku_id: line.sku_id,
          actual_quantity: Number(quantities[line.receive_line_id]),
        })),
      })
      setContext(recorded)
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Unable to record Receive.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  async function handleReview() {
    if (!context || reviewing) return
    setReviewing(true)
    setError('')
    try {
      const reviewed = await acknowledgeReferenceMismatch(context.receive_id)
      setContext({
        ...context,
        putaway_eligible: reviewed.putaway_eligible,
        reference: {
          ...context.reference,
          reviewed_by_user_id: reviewed.reviewed_by_user_id,
          reviewed_at: reviewed.reviewed_at,
        },
      })
    } catch (reviewError) {
      if (reviewError instanceof ApiError && reviewError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        reviewError instanceof Error
          ? reviewError.message
          : 'Unable to acknowledge the reference mismatch.',
      )
    } finally {
      setReviewing(false)
    }
  }

  return (
    <section className="putaway-card receive-card" aria-labelledby="receive-title">
      <div className="title-row">
        <div>
          <p className="eyebrow">Inbound facts</p>
          <h1 id="receive-title">Record Receive</h1>
          <p className="supporting-copy">
            Compare the prepared context with the received document and items.
          </p>
        </div>
        <span className="step-badge">RECEIVE</span>
      </div>

      {!context && !error && (
        <p className="status-panel" role="status">
          Loading Receive context…
        </p>
      )}
      {!context && error && (
        <p className="error-panel" role="alert">
          {error}
        </p>
      )}

      {context && !context.recorded_at && (
        <form onSubmit={handleSubmit}>
          <dl className="item-summary receive-reference-summary">
            <div>
              <dt>Expected reference</dt>
              <dd>{context.reference.expected}</dd>
            </div>
            <div>
              <dt>Prepared lines</dt>
              <dd>{context.lines.length}</dd>
            </div>
          </dl>

          <label className="receive-field">
            Document reference
            <input
              value={documentReference}
              onChange={(event) => setDocumentReference(event.target.value)}
              aria-invalid={Boolean(fieldErrors.document_reference)}
              aria-describedby="document-reference-error"
            />
            {fieldErrors.document_reference && (
              <small id="document-reference-error" className="field-error">
                {fieldErrors.document_reference}
              </small>
            )}
          </label>

          <div className="receive-lines">
            {context.lines.map((line) => {
              const preview = previews[line.receive_line_id]
              const errorId = `${line.receive_line_id}-error`
              return (
                <section className="receive-line" key={line.receive_line_id}>
                  <div>
                    <p className="eyebrow">{line.sku}</p>
                    <p>Expected: {line.expected_quantity} units</p>
                  </div>
                  <label className="receive-field">
                    Actual quantity
                    <input
                      inputMode="numeric"
                      value={quantities[line.receive_line_id] ?? ''}
                      onChange={(event) =>
                        setQuantities((current) => ({
                          ...current,
                          [line.receive_line_id]: event.target.value,
                        }))
                      }
                      aria-invalid={Boolean(fieldErrors[line.receive_line_id])}
                      aria-describedby={errorId}
                    />
                    {fieldErrors[line.receive_line_id] && (
                      <small id={errorId} className="field-error">
                        {fieldErrors[line.receive_line_id]}
                      </small>
                    )}
                  </label>
                  <p className="discrepancy-preview">
                    Difference:{' '}
                    <strong>
                      {preview === null ? '—' : signedQuantity(preview)}
                    </strong>
                  </p>
                </section>
              )
            })}
          </div>

          {error && (
            <p className="error-panel" role="alert">
              {error}
            </p>
          )}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Recording…' : 'Record Receive'}
          </button>
        </form>
      )}

      {context?.recorded_at && (
        <section className="recorded-panel" aria-live="polite">
          <p className="eyebrow">Receive recorded</p>
          <h2>Observed facts saved</h2>
          <dl className="reference-comparison">
            <div>
              <dt>Expected reference</dt>
              <dd>{context.reference.expected}</dd>
            </div>
            <div>
              <dt>Document reference</dt>
              <dd>{context.reference.document}</dd>
            </div>
          </dl>
          <div className="receive-lines">
            {context.lines.map((line) => (
              <section className="receive-line" key={line.receive_line_id}>
                <strong>{line.sku}</strong>
                <span>Expected: {line.expected_quantity}</span>
                <span>Actual: {line.actual_quantity}</span>
                <span>
                  Difference: {signedQuantity(line.quantity_discrepancy ?? 0)}
                </span>
              </section>
            ))}
          </div>

          {context.reference.match_status === 'REFERENCE_MISMATCH' &&
            !context.reference.reviewed_at && (
              <div className="review-required" role="alert">
                <strong>Review required</strong>
                <p>
                  The references differ. Acknowledge this mismatch before the
                  Receive can be eligible for Putaway.
                </p>
                <button type="button" onClick={handleReview} disabled={reviewing}>
                  {reviewing ? 'Acknowledging…' : 'Acknowledge mismatch'}
                </button>
              </div>
            )}

          {context.reference.reviewed_at && (
            <p className="reviewed-panel" role="status">
              Mismatch acknowledged by {context.reference.reviewed_by_user_id} at{' '}
              {new Date(context.reference.reviewed_at).toLocaleString()}.
            </p>
          )}

          {context.reference.match_status === 'REFERENCE_MATCH' && (
            <p className="reviewed-panel" role="status">
              References match. This Receive is eligible for Putaway.
            </p>
          )}
          {error && (
            <p className="error-panel" role="alert">
              {error}
            </p>
          )}
        </section>
      )}
    </section>
  )
}
