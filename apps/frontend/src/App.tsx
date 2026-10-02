import type { Actor } from './auth'
import AdjustmentPage from './AdjustmentPage'
import AdjustmentDecisionPage from './AdjustmentDecisionPage'
import AuditDiscrepancyPage from './AuditDiscrepancyPage'
import AuditPage from './AuditPage'
import DashboardPage from './DashboardPage'
import PickPage from './PickPage'
import PutawayPage from './PutawayPage'
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

const roleLabels: Record<Actor['role'], string> = {
  WAREHOUSE_STAFF: 'Warehouse Staff',
  MANAGER: 'Manager',
  PURCHASING: 'Purchasing',
  ADMIN: 'Admin',
}

function NotFoundPage() {
  return (
    <section className="putaway-card not-found" aria-labelledby="not-found-title">
      <p className="eyebrow">Page not found</p>
      <h1 id="not-found-title">This page is not available</h1>
      <p className="supporting-copy">
        Check the address or return to the Dashboard.
      </p>
      <a className="primary-link" href="/">
        Back to Dashboard
      </a>
    </section>
  )
}

function App({
  actor,
  onLogout,
  onUnauthorized,
  receiveId = import.meta.env.VITE_RECEIVE_ID,
  receiveLineId = import.meta.env.VITE_RECEIVE_LINE_ID,
}: AppProps) {
  const currentPath = window.location.pathname.replace(/\/+$/, '') || '/'
  const pickPathMatch = currentPath.match(/^\/pick\/([^/]+)$/)
  const pickId = pickPathMatch ? decodeURIComponent(pickPathMatch[1]) : null
  const transferPathMatch = currentPath.match(/^\/transfer\/([^/]+)$/)
  const transferSkuId = transferPathMatch
    ? decodeURIComponent(transferPathMatch[1])
    : null
  const adjustmentPathMatch = currentPath.match(/^\/adjustments\/([^/]+)$/)
  const adjustmentRecheckId = adjustmentPathMatch
    ? decodeURIComponent(adjustmentPathMatch[1])
    : null

  let page
  if (currentPath === '/') {
    page = (
      <DashboardPage
        role={actor.role}
        receiveContextAvailable={Boolean(receiveId)}
        putawayContextAvailable={Boolean(receiveLineId)}
      />
    )
  } else if (currentPath === '/putaway') {
    page = (
      <PutawayPage
        receiveLineId={receiveLineId}
        onUnauthorized={onUnauthorized}
      />
    )
  } else if (currentPath === '/receive') {
    page = (
      <ReceivePage receiveId={receiveId} onUnauthorized={onUnauthorized} />
    )
  } else if (currentPath === '/transfers/history') {
    page = <TransferHistoryPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/audits/new') {
    page = <AuditPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/audit-discrepancies') {
    page = <AuditDiscrepancyPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/adjustment-decisions') {
    page = <AdjustmentDecisionPage onUnauthorized={onUnauthorized} />
  } else if (pickId) {
    page = <PickPage pickId={pickId} onUnauthorized={onUnauthorized} />
  } else if (transferSkuId) {
    page = (
      <TransferPage skuId={transferSkuId} onUnauthorized={onUnauthorized} />
    )
  } else if (adjustmentRecheckId) {
    page = (
      <AdjustmentPage
        auditRecheckId={adjustmentRecheckId}
        onUnauthorized={onUnauthorized}
      />
    )
  } else {
    page = <NotFoundPage />
  }

  return (
    <main className="page-shell">
      <header className="app-header">
        <a className="brand-link" href="/" aria-label="Smart Inventory Dashboard">
          <span className="brand-mark" aria-hidden="true">
            W
          </span>
          <span>
            <span className="eyebrow">MAIN warehouse</span>
            <span className="brand-name">Smart Inventory</span>
          </span>
        </a>
        <nav className="app-navigation" aria-label="Primary navigation">
          <a href="/">Dashboard</a>
        </nav>
        <span className="role-chip">{roleLabels[actor.role]}</span>
        <button className="logout-button" type="button" onClick={onLogout}>
          Sign out
        </button>
      </header>

      {page}
    </main>
  )
}

export default App
