import { FormEvent, useEffect, useRef, useState } from 'react'
import {
  ApiError,
  AuditCommand,
  AuditContext,
  AuditResult,
  AuditScopeType,
  loadAuditContext,
  submitAudit,
} from './api'

type AuditPageProps = {
  onUnauthorized: () => void
}

type SubmissionAttempt = {
  fingerprint: string
  key: string
}

const maxQuantity = 2_147_483_647
const locationLabels: Record<string, string> = {
  BACKROOM: 'Backroom',
  SALES_SHELF: 'Sales Shelf',
}

function pairKey(skuId: string, locationId: string) {
  return `${skuId}:${locationId}`
}

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `audit-${Date.now()}`
}

function commandFingerprint(command: AuditCommand) {
  return JSON.stringify(command)
}

export default function AuditPage({ onUnauthorized }: AuditPageProps) {
  const [context, setContext] = useState<AuditContext | null>(null)
  const [mode, setMode] = useState<AuditScopeType>('SELECTED_PAIRS')
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [physicalInputs, setPhysicalInputs] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [forbidden, setForbidden] = useState(false)
  const [scopeChanged, setScopeChanged] = useState(false)
  const [result, setResult] = useState<AuditResult | null>(null)
  const attempt = useRef<SubmissionAttempt | null>(null)

  function applyContext(loaded: AuditContext, reconcile: boolean) {
    const available = new Set(
      loaded.pairs.map((pair) => pairKey(pair.sku_id, pair.location_id)),
    )
    setContext(loaded)
    if (reconcile) {
      setSelected((current) =>
        new Set([...current].filter((key) => available.has(key))),
      )
      setPhysicalInputs((current) =>
        Object.fromEntries(
          Object.entries(current).filter(([key]) => available.has(key)),
        ),
      )
    }
  }

  async function reloadContext() {
    attempt.current = null
    setLoading(true)
    setError('')
    setForbidden(false)
    setScopeChanged(false)
    try {
      applyContext(await loadAuditContext(), true)
    } catch (loadError) {
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
          : 'Unable to load Audit context.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    loadAuditContext()
      .then((loaded) => {
        if (active) applyContext(loaded, false)
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
            : 'Unable to load Audit context.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [onUnauthorized])

  function editCommand(action: () => void) {
    action()
    attempt.current = null
    setError('')
    setScopeChanged(false)
  }

  function changeMode(nextMode: AuditScopeType) {
    editCommand(() => setMode(nextMode))
  }

  function togglePair(key: string) {
    editCommand(() =>
      setSelected((current) => {
        const next = new Set(current)
        if (next.has(key)) next.delete(key)
        else next.add(key)
        return next
      }),
    )
  }

  function changePhysical(key: string, value: string) {
    editCommand(() =>
      setPhysicalInputs((current) => ({ ...current, [key]: value })),
    )
  }

  function buildCommand(): AuditCommand | null {
    if (!context) return null
    const pairs = context.pairs.filter((pair) => {
      const key = pairKey(pair.sku_id, pair.location_id)
      return mode === 'WHOLE_WAREHOUSE' || selected.has(key)
    })
    if (pairs.length === 0) {
      setError('Select at least one SKU/location pair.')
      return null
    }
    const lines: AuditCommand['lines'] = []
    for (const pair of pairs) {
      const value = physicalInputs[pairKey(pair.sku_id, pair.location_id)] ?? ''
      if (!/^(0|[1-9]\d*)$/.test(value)) {
        setError('Every physical quantity must be a non-negative integer.')
        return null
      }
      const quantity = Number(value)
      if (!Number.isSafeInteger(quantity) || quantity > maxQuantity) {
        setError(`Physical quantity must not exceed ${maxQuantity}.`)
        return null
      }
      lines.push({
        sku_id: pair.sku_id,
        location_id: pair.location_id,
        physical_quantity: quantity,
      })
    }
    lines.sort((left, right) =>
      `${left.sku_id}:${left.location_id}`.localeCompare(
        `${right.sku_id}:${right.location_id}`,
      ),
    )
    return { scope_type: mode, lines }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    const command = buildCommand()
    if (!command) return
    const fingerprint = commandFingerprint(command)
    if (!attempt.current || attempt.current.fingerprint !== fingerprint) {
      attempt.current = { fingerprint, key: createIdempotencyKey() }
    }
    setSubmitting(true)
    setError('')
    setScopeChanged(false)
    try {
      const submitted = await submitAudit(command, attempt.current.key)
      attempt.current = null
      setResult(submitted)
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 401) {
        onUnauthorized()
        return
      }
      if (submitError instanceof ApiError && submitError.status === 403) {
        setForbidden(true)
        return
      }
      if (
        submitError instanceof ApiError &&
        submitError.code === 'AUDIT_SCOPE_CHANGED'
      ) {
        setScopeChanged(true)
      }
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Unable to record Audit.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (forbidden) {
    return (
      <section className="putaway-card forbidden-panel">
        <p className="eyebrow">Forbidden</p>
        <h1>Warehouse Staff role required</h1>
        <p>This Audit operation is not available for your current role.</p>
      </section>
    )
  }

  return (
    <section className="putaway-card audit-card" aria-labelledby="audit-title">
      <div className="title-row">
        <div>
          <p className="eyebrow">Inventory count</p>
          <h1 id="audit-title">New Audit</h1>
          <p className="supporting-copy">
            Count explicit SKU/location pairs and record the comparison.
          </p>
        </div>
        <span className="step-badge">AUDIT</span>
      </div>

      {loading && <p className="status-panel">Loading Audit context…</p>}
      {!loading && !context && (
        <div className="error-panel" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void reloadContext()}>
            Retry context
          </button>
        </div>
      )}

      {context && !result && (
        <form onSubmit={handleSubmit}>
          <fieldset className="audit-mode">
            <legend>Audit scope</legend>
            <label>
              <input
                type="radio"
                name="audit-mode"
                checked={mode === 'SELECTED_PAIRS'}
                onChange={() => changeMode('SELECTED_PAIRS')}
              />
              Selected pairs
            </label>
            <label>
              <input
                type="radio"
                name="audit-mode"
                checked={mode === 'WHOLE_WAREHOUSE'}
                onChange={() => changeMode('WHOLE_WAREHOUSE')}
              />
              Whole Warehouse
            </label>
          </fieldset>

          <div className="history-table-scroll audit-table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Count</th>
                  <th scope="col">SKU</th>
                  <th scope="col">Location</th>
                  <th scope="col">System preview</th>
                  <th scope="col">Physical quantity</th>
                  <th scope="col">Preview discrepancy</th>
                </tr>
              </thead>
              <tbody>
                {context.pairs.map((pair) => {
                  const key = pairKey(pair.sku_id, pair.location_id)
                  const included =
                    mode === 'WHOLE_WAREHOUSE' || selected.has(key)
                  const rawPhysical = physicalInputs[key] ?? ''
                  const valid = /^(0|[1-9]\d*)$/.test(rawPhysical)
                  const preview = valid
                    ? Number(rawPhysical) - pair.preview_system_quantity
                    : null
                  return (
                    <tr key={key}>
                      <td>
                        <input
                          aria-label={`Count ${pair.sku} at ${pair.location}`}
                          type="checkbox"
                          checked={included}
                          disabled={mode === 'WHOLE_WAREHOUSE' || submitting}
                          onChange={() => togglePair(key)}
                        />
                      </td>
                      <td>{pair.sku}</td>
                      <td>{locationLabels[pair.location] ?? pair.location}</td>
                      <td>{pair.preview_system_quantity}</td>
                      <td>
                        <input
                          aria-label={`Physical quantity for ${pair.sku} at ${pair.location}`}
                          inputMode="numeric"
                          value={rawPhysical}
                          disabled={!included || submitting}
                          onChange={(event) =>
                            changePhysical(key, event.target.value)
                          }
                        />
                      </td>
                      <td>{preview ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="field-help">
            System quantities and discrepancies above are previews. The submit
            response is authoritative.
          </p>

          {error && (
            <div className="error-panel" role="alert">
              <p>{error}</p>
              {scopeChanged && (
                <button type="button" onClick={() => void reloadContext()}>
                  Reload and reconcile scope
                </button>
              )}
            </div>
          )}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Recording…' : 'Record Audit'}
          </button>
        </form>
      )}

      {result && (
        <section className="success-panel" aria-live="polite">
          <p className="eyebrow">Audit recorded</p>
          <h2>
            {result.status === 'MATCH_COMPLETED'
              ? 'All counted quantities match'
              : 'Discrepancy recorded'}
          </h2>
          {result.status === 'MISMATCH_RECORDED' && (
            <p>The discrepancy was recorded. Stock was not changed.</p>
          )}
          <dl>
            <div>
              <dt>Result</dt>
              <dd>{result.result}</dd>
            </div>
            <div>
              <dt>Lines</dt>
              <dd>{result.lines.length}</dd>
            </div>
          </dl>
        </section>
      )}
    </section>
  )
}
