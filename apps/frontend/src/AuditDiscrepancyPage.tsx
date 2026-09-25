import { FormEvent, useEffect, useRef, useState } from 'react'
import {
  ApiError,
  AuditDiscrepancy,
  AuditDiscrepancyList,
  AuditRecheckResult,
  loadAuditDiscrepancies,
  loadAuditDiscrepancy,
  submitAuditRecheck,
} from './api'

type AuditDiscrepancyPageProps = {
  onUnauthorized: () => void
}

type SubmissionAttempt = {
  fingerprint: string
  key: string
}

const maxQuantity = 2_147_483_647

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `audit-recheck-${Date.now()}`
}

function recheckEvidence(result: AuditRecheckResult) {
  return {
    recheck_id: result.recheck_id,
    recheck_system_quantity: result.recheck_system_quantity,
    recheck_physical_quantity: result.recheck_physical_quantity,
    recheck_quantity_discrepancy: result.recheck_quantity_discrepancy,
    result: result.result,
    performed_by: result.performed_by,
    performed_at: result.performed_at,
  }
}

export default function AuditDiscrepancyPage({
  onUnauthorized,
}: AuditDiscrepancyPageProps) {
  const [discrepancies, setDiscrepancies] =
    useState<AuditDiscrepancyList | null>(null)
  const [detail, setDetail] = useState<AuditDiscrepancy | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [quantityInput, setQuantityInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')
  const [detailError, setDetailError] = useState('')
  const [alreadyRecorded, setAlreadyRecorded] = useState(false)
  const attempt = useRef<SubmissionAttempt | null>(null)

  function handleApiFailure(loadError: unknown, fallback: string) {
    if (loadError instanceof ApiError && loadError.status === 401) {
      onUnauthorized()
      return 'unauthorized'
    }
    if (loadError instanceof ApiError && loadError.status === 403) {
      setForbidden(true)
      return 'forbidden'
    }
    return loadError instanceof Error ? loadError.message : fallback
  }

  async function loadList() {
    setLoading(true)
    setForbidden(false)
    setError('')
    try {
      setDiscrepancies(await loadAuditDiscrepancies())
    } catch (loadError) {
      const message = handleApiFailure(
        loadError,
        'Unable to load Audit discrepancies.',
      )
      if (message !== 'unauthorized' && message !== 'forbidden') {
        setError(message)
      }
      setDiscrepancies(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    loadAuditDiscrepancies()
      .then((loaded) => {
        if (active) setDiscrepancies(loaded)
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
            : 'Unable to load Audit discrepancies.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [onUnauthorized])

  async function openDetail(auditLineId: string) {
    attempt.current = null
    setSelectedId(auditLineId)
    setDetail(null)
    setQuantityInput('')
    setAlreadyRecorded(false)
    setDetailError('')
    setDetailLoading(true)
    try {
      setDetail(await loadAuditDiscrepancy(auditLineId))
    } catch (loadError) {
      const message = handleApiFailure(
        loadError,
        'Unable to load the Audit discrepancy.',
      )
      if (message !== 'unauthorized' && message !== 'forbidden') {
        setDetailError(message)
      }
    } finally {
      setDetailLoading(false)
    }
  }

  function changeQuantity(value: string) {
    setQuantityInput(value)
    attempt.current = null
    setDetailError('')
    setAlreadyRecorded(false)
  }

  function parsedQuantity(): number | null {
    if (!/^(0|[1-9]\d*)$/.test(quantityInput)) {
      setDetailError('Physical quantity must be a non-negative integer.')
      return null
    }
    const quantity = Number(quantityInput)
    if (!Number.isSafeInteger(quantity) || quantity > maxQuantity) {
      setDetailError(`Physical quantity must not exceed ${maxQuantity}.`)
      return null
    }
    return quantity
  }

  function applyResult(result: AuditRecheckResult) {
    const evidence = recheckEvidence(result)
    setDetail((current) =>
      current
        ? {
            ...current,
            recheck: evidence,
            adjust_eligible: result.adjust_eligible,
          }
        : current,
    )
    setDiscrepancies((current) =>
      current
        ? {
            items: current.items.map((item) =>
              item.audit_line_id === result.audit_line_id
                ? {
                    ...item,
                    recheck: evidence,
                    adjust_eligible: result.adjust_eligible,
                  }
                : item,
            ),
          }
        : current,
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!detail || detail.recheck || submitting) return
    const quantity = parsedQuantity()
    if (quantity === null) return
    const fingerprint = `${detail.audit_line_id}:${quantity}`
    if (!attempt.current || attempt.current.fingerprint !== fingerprint) {
      attempt.current = { fingerprint, key: createIdempotencyKey() }
    }
    setSubmitting(true)
    setDetailError('')
    setAlreadyRecorded(false)
    try {
      const result = await submitAuditRecheck(
        detail.audit_line_id,
        quantity,
        attempt.current.key,
      )
      attempt.current = null
      applyResult(result)
    } catch (submitError) {
      if (
        submitError instanceof ApiError &&
        submitError.code === 'RECHECK_ALREADY_RECORDED'
      ) {
        attempt.current = null
        setAlreadyRecorded(true)
        try {
          const persisted = await loadAuditDiscrepancy(detail.audit_line_id)
          setDetail(persisted)
          setDiscrepancies((current) =>
            current
              ? {
                  items: current.items.map((item) =>
                    item.audit_line_id === persisted.audit_line_id
                      ? persisted
                      : item,
                  ),
                }
              : current,
          )
        } catch (reloadError) {
          const message = handleApiFailure(
            reloadError,
            'The recheck exists, but its detail could not be reloaded.',
          )
          if (message !== 'unauthorized' && message !== 'forbidden') {
            setDetailError(message)
          }
        }
        return
      }
      const message = handleApiFailure(
        submitError,
        'Unable to record the Manager recheck.',
      )
      if (message !== 'unauthorized' && message !== 'forbidden') {
        setDetailError(message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section
      className="putaway-card audit-discrepancy-card"
      aria-labelledby="audit-discrepancy-title"
    >
      <div className="title-row">
        <div>
          <p className="eyebrow">Manager review</p>
          <h1 id="audit-discrepancy-title">Audit discrepancies</h1>
          <p className="supporting-copy">
            Review original mismatch evidence and record one physical recheck.
          </p>
        </div>
        <span className="step-badge">RECHECK</span>
      </div>

      {loading && (
        <p className="status-panel" role="status">
          Loading Audit discrepancies…
        </p>
      )}
      {!loading && forbidden && (
        <div className="forbidden-panel" role="alert">
          <p className="eyebrow">Forbidden</p>
          <h2>Manager role required</h2>
          <p>This operation is not available for your current role.</p>
        </div>
      )}
      {!loading && error && (
        <div className="error-panel" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void loadList()}>
            Retry
          </button>
        </div>
      )}
      {!loading && !forbidden && !error && discrepancies?.items.length === 0 && (
        <p className="status-panel">No Audit discrepancies require review.</p>
      )}

      {!loading &&
        !forbidden &&
        !error &&
        discrepancies &&
        discrepancies.items.length > 0 && (
          <div className="audit-discrepancy-layout">
            <div className="history-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th scope="col">SKU</th>
                    <th scope="col">Location</th>
                    <th scope="col">Original discrepancy</th>
                    <th scope="col">Recheck</th>
                    <th scope="col">Review</th>
                  </tr>
                </thead>
                <tbody>
                  {discrepancies.items.map((item) => (
                    <tr key={item.audit_line_id}>
                      <td>{item.sku.code}</td>
                      <td>{item.location.code}</td>
                      <td>{item.original.quantity_discrepancy}</td>
                      <td>{item.recheck?.result ?? 'Pending'}</td>
                      <td>
                        <button
                          type="button"
                          aria-pressed={selectedId === item.audit_line_id}
                          onClick={() => void openDetail(item.audit_line_id)}
                        >
                          Review {item.sku.code} at {item.location.code}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {detailLoading && (
              <p className="status-panel" role="status">
                Loading discrepancy detail…
              </p>
            )}
            {!detailLoading && selectedId && !detail && detailError && (
              <div className="error-panel" role="alert">
                <p>{detailError}</p>
                <button type="button" onClick={() => void openDetail(selectedId)}>
                  Retry detail
                </button>
              </div>
            )}
            {!detailLoading && detail && (
              <div className="audit-evidence-grid">
                <section aria-labelledby="original-audit-title">
                  <p className="eyebrow">ORIGINAL AUDIT</p>
                  <h2 id="original-audit-title">
                    {detail.sku.code} at {detail.location.code}
                  </h2>
                  <dl className="item-summary audit-evidence-summary">
                    <div>
                      <dt>System quantity</dt>
                      <dd>{detail.original.system_quantity}</dd>
                    </div>
                    <div>
                      <dt>Physical quantity</dt>
                      <dd>{detail.original.physical_quantity}</dd>
                    </div>
                    <div>
                      <dt>Discrepancy</dt>
                      <dd>{detail.original.quantity_discrepancy}</dd>
                    </div>
                    <div>
                      <dt>Auditor</dt>
                      <dd>{detail.original.audited_by.login_identifier}</dd>
                    </div>
                  </dl>
                  <p className="field-help">
                    Original Audit evidence is immutable. Stock has not been changed.
                  </p>
                </section>

                <section aria-labelledby="manager-recheck-title">
                  <p className="eyebrow">MANAGER RECHECK</p>
                  <h2 id="manager-recheck-title">Physical recheck</h2>
                  {detail.recheck ? (
                    <div
                      className={
                        detail.recheck.result === 'MATCH'
                          ? 'success-panel'
                          : 'review-required'
                      }
                    >
                      <h3>{detail.recheck.result}</h3>
                      <p>
                        Recheck system {detail.recheck.recheck_system_quantity};
                        physical {detail.recheck.recheck_physical_quantity};
                        discrepancy{' '}
                        {detail.recheck.recheck_quantity_discrepancy}.
                      </p>
                      <p>Stock was not changed by this recheck.</p>
                      {detail.adjust_eligible && (
                        <p>This mismatch is eligible context for future Adjust work.</p>
                      )}
                      {alreadyRecorded && (
                        <p role="status">
                          Another request recorded this recheck first. Persisted evidence
                          is shown read-only.
                        </p>
                      )}
                    </div>
                  ) : (
                    <form onSubmit={handleSubmit}>
                      <label htmlFor="recheck-physical-quantity">
                        Recheck physical quantity
                      </label>
                      <input
                        id="recheck-physical-quantity"
                        inputMode="numeric"
                        value={quantityInput}
                        disabled={submitting}
                        onChange={(event) => changeQuantity(event.target.value)}
                      />
                      <p className="field-help">
                        Enter a whole number from 0 to {maxQuantity}. The server reads
                        current stock only when you submit.
                      </p>
                      {detailError && (
                        <div className="error-panel" role="alert">
                          <p>{detailError}</p>
                        </div>
                      )}
                      <button type="submit" disabled={submitting}>
                        {submitting ? 'Recording recheck…' : 'Record Manager recheck'}
                      </button>
                    </form>
                  )}
                </section>
              </div>
            )}
          </div>
        )}
    </section>
  )
}
