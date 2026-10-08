import type { Actor } from './auth'
import EligibleAdjustmentsPage from './EligibleAdjustmentsPage'
import AdjustmentPage from './AdjustmentPage'
import AdjustmentDecisionPage from './AdjustmentDecisionPage'
import AuditDiscrepancyPage from './AuditDiscrepancyPage'
import AuditPage from './AuditPage'
import DashboardPage from './DashboardPage'
import PickPage from './PickPage'
import PickQueuePage from './PickQueuePage'
import PutawayPage from './PutawayPage'
import PutawayQueuePage from './PutawayQueuePage'
import ReceivePage from './ReceivePage'
import ReceiveQueuePage from './ReceiveQueuePage'
import TransferHistoryPage from './TransferHistoryPage'
import TransferPage from './TransferPage'
import TransferSelectorPage from './TransferSelectorPage'

type AppProps = {
  actor: Actor
  onLogout: () => void | Promise<void>
  onUnauthorized: () => void
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
}: AppProps) {
  const currentPath = window.location.pathname.replace(/\/+$/, '') || '/'
  const receivePathMatch = currentPath.match(/^\/receive\/([^/]+)$/)
  const selectedReceiveId = receivePathMatch
    ? decodeURIComponent(receivePathMatch[1])
    : null
  const putawayPathMatch = currentPath.match(/^\/putaway\/([^/]+)$/)
  const selectedReceiveLineId = putawayPathMatch
    ? decodeURIComponent(putawayPathMatch[1])
    : null
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
    page = <DashboardPage role={actor.role} />
  } else if (currentPath === '/putaway') {
    page = <PutawayQueuePage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/receive') {
    page = <ReceiveQueuePage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/picks') {
    page = <PickQueuePage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/transfers') {
    page = <TransferSelectorPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/transfers/history') {
    page = <TransferHistoryPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/audits/new') {
    page = <AuditPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/audit-discrepancies') {
    page = <AuditDiscrepancyPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/adjustment-decisions') {
    page = <AdjustmentDecisionPage onUnauthorized={onUnauthorized} />
  } else if (currentPath === '/adjustments') {
    page = <EligibleAdjustmentsPage onUnauthorized={onUnauthorized} />
  } else if (selectedReceiveId) {
    page = (
      <ReceivePage receiveId={selectedReceiveId} onUnauthorized={onUnauthorized} />
    )
  } else if (selectedReceiveLineId) {
    page = (
      <PutawayPage
        receiveLineId={selectedReceiveLineId}
        onUnauthorized={onUnauthorized}
      />
    )
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
