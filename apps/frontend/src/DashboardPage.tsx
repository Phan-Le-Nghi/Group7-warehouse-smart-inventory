import type { Role } from './auth'

type DashboardPageProps = {
  role: Role
  receiveContextAvailable: boolean
  putawayContextAvailable: boolean
}

type DashboardAction = {
  title: string
  description: string
  href: string
  available: boolean
}

const managerActions: DashboardAction[] = [
  {
    title: 'Transfer History',
    description: 'Review confirmed internal stock transfers.',
    href: '/transfers/history',
    available: true,
  },
  {
    title: 'Audit Discrepancies',
    description: 'Review discrepancies and record Manager rechecks.',
    href: '/audit-discrepancies',
    available: true,
  },
  {
    title: 'Adjust Decisions',
    description: 'Review pending Adjust requests.',
    href: '/adjustment-decisions',
    available: true,
  },
]

function staffActions(
  receiveContextAvailable: boolean,
  putawayContextAvailable: boolean,
): DashboardAction[] {
  return [
    {
      title: 'Receive',
      description: receiveContextAvailable
        ? 'Record the prepared Receive context.'
        : 'Requires prepared context.',
      href: '/receive',
      available: receiveContextAvailable,
    },
    {
      title: 'Putaway',
      description: putawayContextAvailable
        ? 'Place stock from the prepared Receive line.'
        : 'Requires prepared context.',
      href: '/putaway',
      available: putawayContextAvailable,
    },
    {
      title: 'New Audit',
      description: 'Count selected stock and record the result.',
      href: '/audits/new',
      available: true,
    },
    {
      title: 'Adjust Requests',
      description: 'Create requests from manager-confirmed inventory discrepancies.',
      href: '/adjustments',
      available: true,
    },
  ]
}

export default function DashboardPage({
  role,
  receiveContextAvailable,
  putawayContextAvailable,
}: DashboardPageProps) {
  const actions =
    role === 'WAREHOUSE_STAFF'
      ? staffActions(receiveContextAvailable, putawayContextAvailable)
      : role === 'MANAGER'
        ? managerActions
        : []

  return (
    <section className="dashboard" aria-labelledby="dashboard-title">
      <p className="eyebrow">Home</p>
      <h1 id="dashboard-title">Warehouse Dashboard</h1>
      <p className="supporting-copy">
        Choose an available action for your current role.
      </p>

      {actions.length > 0 ? (
        <div className="dashboard-grid">
          {actions.map((action) =>
            action.available ? (
              <a className="dashboard-action" href={action.href} key={action.href}>
                <h2>{action.title}</h2>
                <p>{action.description}</p>
                <span>Open {action.title}</span>
              </a>
            ) : (
              <article
                className="dashboard-action dashboard-action-unavailable"
                key={action.href}
              >
                <h2>{action.title}</h2>
                <p>{action.description}</p>
                <span>Unavailable</span>
              </article>
            ),
          )}
        </div>
      ) : (
        <p className="status-panel dashboard-empty-state">
          No dashboard actions are available for this role in the current MVP.
        </p>
      )}
    </section>
  )
}
