import { FormEvent, useEffect, useRef, useState } from 'react'
import {
  AdjustmentDecisionCommand,
  AdjustmentDetail,
  AdjustmentQueue,
  ApiError,
  loadAdjustmentDetail,
  loadPendingAdjustments,
  submitAdjustmentDecision,
} from './api'

type Props = { onUnauthorized: () => void }
type Decision = 'APPROVE' | 'REJECT'
type Attempt = { fingerprint: string; key: string }

function createKey() {
  return globalThis.crypto?.randomUUID?.() ?? `adjust-decision-${Date.now()}`
}

function signed(value: number) {
  return value > 0 ? `+${value}` : String(value)
}

export default function AdjustmentDecisionPage({ onUnauthorized }: Props) {
  const [queue, setQueue] = useState<AdjustmentQueue | null>(null)
  const [detail, setDetail] = useState<AdjustmentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState('')
  const [detailError, setDetailError] = useState('')
  const [decision, setDecision] = useState<Decision | null>(null)
  const [reason, setReason] = useState('')
  const attempt = useRef<Attempt | null>(null)

  function handleFailure(value: unknown, fallback: string) {
    if (value instanceof ApiError && value.status === 401) {
      onUnauthorized()
      return ''
    }
    if (value instanceof ApiError && value.status === 403) {
      setForbidden(true)
      return ''
    }
    return value instanceof Error ? value.message : fallback
  }

  async function loadQueue() {
    setLoading(true)
    setError('')
    setForbidden(false)
    try {
      setQueue(await loadPendingAdjustments())
    } catch (loadError) {
      setError(handleFailure(loadError, 'Unable to load pending Adjust requests.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    loadPendingAdjustments()
      .then(async (loaded) => {
        if (!active) return
        setQueue(loaded)
        const selected = new URLSearchParams(window.location.search).get(
          'adjustment_id',
        )
        if (selected) {
          setDetailLoading(true)
          try {
            const selectedDetail = await loadAdjustmentDetail(selected)
            if (active) setDetail(selectedDetail)
          } catch (loadError) {
            if (active) {
              setDetailError(
                loadError instanceof Error
                  ? loadError.message
                  : 'Unable to load Adjust detail.',
              )
            }
          } finally {
            if (active) setDetailLoading(false)
          }
        }
      })
      .catch((loadError: unknown) => {
        if (!active) return
        if (loadError instanceof ApiError && loadError.status === 401) {
          onUnauthorized()
        } else if (loadError instanceof ApiError && loadError.status === 403) {
          setForbidden(true)
        } else {
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Unable to load pending Adjust requests.',
          )
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [onUnauthorized])

  async function openDetail(adjustmentId: string) {
    attempt.current = null
    setDecision(null)
    setReason('')
    setDetailError('')
    setDetailLoading(true)
    const url = new URL(window.location.href)
    url.searchParams.set('adjustment_id', adjustmentId)
    window.history.replaceState({}, '', `${url.pathname}${url.search}`)
    try {
      setDetail(await loadAdjustmentDetail(adjustmentId))
    } catch (loadError) {
      setDetailError(handleFailure(loadError, 'Unable to load Adjust detail.'))
    } finally {
      setDetailLoading(false)
    }
  }

  function chooseDecision(value: Decision) {
    attempt.current = null
    setDecision(value)
    setReason('')
    setDetailError('')
  }

  function cancelDecision() {
    attempt.current = null
    setDecision(null)
    setReason('')
    setDetailError('')
  }

  function changeReason(value: string) {
    attempt.current = null
    setReason(value)
    setDetailError('')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!detail || !decision || submitting) return
    const normalizedReason = reason.trim()
    if (decision === 'REJECT' && (!normalizedReason || normalizedReason.length > 500)) {
      setDetailError('Rejection reason must contain from 1 to 500 characters.')
      return
    }
    const command: AdjustmentDecisionCommand =
      decision === 'APPROVE'
        ? { decision: 'APPROVE' }
        : { decision: 'REJECT', rejection_reason: normalizedReason }
    const fingerprint = JSON.stringify(command)
    if (!attempt.current || attempt.current.fingerprint !== fingerprint) {
      attempt.current = { fingerprint, key: createKey() }
    }
    setSubmitting(true)
    setDetailError('')
    try {
      const decided = await submitAdjustmentDecision(
        detail.adjustment_id,
        command,
        attempt.current.key,
      )
      attempt.current = null
      setDetail(decided)
      setDecision(null)
      setQueue((current) =>
        current
          ? {
              items: current.items.filter(
                (item) => item.adjustment_id !== decided.adjustment_id,
              ),
            }
          : current,
      )
    } catch (submitError) {
      if (
        submitError instanceof ApiError &&
        submitError.code === 'ADJUSTMENT_NOT_PENDING'
      ) {
        attempt.current = null
        setDetailError('This request was already decided. Reloaded current detail.')
        try {
          setDetail(await loadAdjustmentDetail(detail.adjustment_id))
          await loadQueue()
        } catch (reloadError) {
          setDetailError(handleFailure(reloadError, 'Unable to reload Adjust detail.'))
        }
      } else {
        setDetailError(handleFailure(submitError, 'Unable to submit the decision.'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="putaway-card adjustment-decision-card">
      <div className="title-row">
        <div>
          <p className="eyebrow">Manager review</p>
          <h1>Adjust decisions</h1>
          <p className="supporting-copy">Review pending requests and record one terminal decision.</p>
        </div>
        <span className="step-badge">ADJUST</span>
      </div>

      {loading && <p className="status-panel" role="status">Loading pending Adjust requests…</p>}
      {!loading && forbidden && <div className="error-panel" role="alert"><h2>Manager role required</h2></div>}
      {!loading && error && <div className="error-panel" role="alert"><p>{error}</p><button type="button" onClick={() => void loadQueue()}>Retry</button></div>}
      {!loading && !forbidden && !error && queue?.items.length === 0 && <p className="status-panel">No pending Adjust requests.</p>}

      {!loading && !forbidden && !error && queue && queue.items.length > 0 && (
        <div className="adjustment-decision-layout">
          <div className="history-table-scroll">
            <table>
              <thead><tr><th>Requested</th><th>SKU / location</th><th>Change</th><th>Review</th></tr></thead>
              <tbody>{queue.items.map((item) => (
                <tr key={item.adjustment_id}>
                  <td>{item.requested_by.login_identifier}<small>{new Date(item.requested_at).toLocaleString()}</small></td>
                  <td>{item.sku.code}<small>{item.location.code}</small></td>
                  <td>{signed(item.requested_change)}</td>
                  <td><button type="button" onClick={() => void openDetail(item.adjustment_id)} aria-label={`Review ${item.sku.code} at ${item.location.code}`}>Review</button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}

      {detailLoading && <p className="status-panel" role="status">Loading Adjust detail…</p>}
      {detail && !detailLoading && (
        <article className="adjustment-decision-detail">
          <h2>{detail.status}</h2>
          <dl className="item-summary audit-evidence-summary">
            <div><dt>SKU</dt><dd>{detail.sku.code}</dd></div>
            <div><dt>Location</dt><dd>{detail.location.code}</dd></div>
            <div><dt>Requested by</dt><dd>{detail.requested_by.login_identifier}</dd></div>
            <div><dt>Requested change</dt><dd data-testid="manager-requested-change">{signed(detail.requested_change)}</dd></div>
          </dl>
          <p><strong>Staff reason:</strong> {detail.reason}</p>
          <div className="audit-evidence-grid">
            <section><p className="eyebrow">ORIGINAL AUDIT</p><dl><div><dt>System</dt><dd>{detail.original_audit.system_quantity}</dd></div><div><dt>Physical</dt><dd>{detail.original_audit.physical_quantity}</dd></div></dl></section>
            <section><p className="eyebrow">MANAGER RECHECK</p><dl><div><dt>System snapshot</dt><dd>{detail.manager_recheck.recheck_system_quantity}</dd></div><div><dt>Physical</dt><dd>{detail.manager_recheck.recheck_physical_quantity}</dd></div></dl></section>
          </div>

          {detail.status === 'PENDING_MANAGER_DECISION' && !decision && (
            <div className="decision-actions"><button type="button" onClick={() => chooseDecision('APPROVE')}>Approve</button><button type="button" className="secondary-action" onClick={() => chooseDecision('REJECT')}>Reject</button></div>
          )}
          {detail.status === 'PENDING_MANAGER_DECISION' && decision && (
            <form onSubmit={submit} className="decision-confirmation">
              <h3>Confirm {decision === 'APPROVE' ? 'approval' : 'rejection'}</h3>
              {decision === 'REJECT' && <label>Rejection reason<textarea value={reason} maxLength={500} onChange={(event) => changeReason(event.target.value)} /></label>}
              <button type="submit" disabled={submitting}>{submitting ? 'Submitting…' : `Confirm ${decision === 'APPROVE' ? 'approval' : 'rejection'}`}</button>
              <button type="button" className="secondary-action" onClick={cancelDecision}>Cancel</button>
            </form>
          )}
          {detail.status === 'APPLIED' && <div className="success-panel"><p>Stock adjustment applied.</p><p>Before: {detail.applied_stock_before} · After: {detail.applied_stock_after}</p></div>}
          {detail.status === 'REJECTED' && <div className="status-panel"><p>Rejected: {detail.rejection_reason}</p><p>Stock was not changed.</p></div>}
          {detailError && <p className="error-panel" role="alert">{detailError}</p>}
        </article>
      )}
    </section>
  )
}
