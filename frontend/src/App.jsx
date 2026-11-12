
const navigation = [
  { label: 'Overview', icon: 'grid', active: true },
  { label: 'Reconciliation Jobs', icon: 'layers' },
  { label: 'Transactions', icon: 'list' },
  { label: 'Exceptions', icon: 'alert' },
  { label: 'Human in the Loop', icon: 'shield' },
  { label: 'Reports & Audit', icon: 'file' },
]

function Icon({ name, size = 20 }) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.7,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  }

  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5" /><path d="m3 16 9 5 9-5" /></>,
    list: <><path d="M9 6h12M9 12h12M9 18h12" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></>,
    alert: <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6M8 13h8M8 17h8" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
    upload: <><path d="M12 16V4m-4 4 4-4 4 4" /><path d="M4 16v4h16v-4" /></>,
    arrow: <><path d="M7 17 17 7M7 7h10v10" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    check: <><path d="m5 12 4 4L19 6" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
  }

  return <svg {...common}>{paths[name] || paths.grid}</svg>
}

function App() {
  return (
    <div className="min-h-screen bg-background text-heading">
      <div className="flex min-h-screen">

        {/* Sidebar */}
        <aside className="hidden w-64 shrink-0 flex-col bg-brand-950 text-white lg:flex">
          <div className="flex h-20 items-center gap-3 border-b border-white/10 px-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500 text-lg font-bold shadow-lg shadow-blue-500/20">
              R
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-wide">RECON X</h1>
              <p className="text-[10px] tracking-[0.2em] text-slate-400">INTELLIGENT RECONCILIATION</p>
            </div>
          </div>

          <div className="px-5 pt-8">
            <p className="mb-4 px-3 text-[10px] font-semibold tracking-[0.18em] text-slate-500">
              WORKSPACE
            </p>

            <nav className="space-y-1">
              {navigation.map((item) => (
                <div
                  key={item.label}
                  className={`flex items-center gap-3 rounded-lg px-3 py-3 text-sm ${
                    item.active
                      ? 'bg-blue-600 font-semibold text-white shadow-lg shadow-blue-950/30'
                      : 'text-slate-400'
                  }`}
                >
                  <Icon name={item.icon} size={18} />
                  {item.label}
                </div>
              ))}
            </nav>
          </div>

          <div className="mt-auto p-5">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-200">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Platform status
              </div>
              <p className="text-xs leading-5 text-slate-400">
                Interface preview. Live service integration is not configured yet.
              </p>
            </div>
            <p className="mt-5 text-center text-[10px] text-slate-500">
              RECON X · Development Preview
            </p>
          </div>
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1">

          {/* Topbar */}
          <header className="sticky top-0 z-10 flex h-20 items-center justify-between border-b border-border bg-white/95 px-5 backdrop-blur md:px-8">
            <div className="flex items-center gap-3">
              <div className="rounded-lg p-2 text-muted lg:hidden">
                <Icon name="menu" size={22} />
              </div>
              <div>
                <p className="text-xs text-muted">Workspace / Overview</p>
                <h2 className="mt-1 text-lg font-bold text-heading">Dashboard</h2>
              </div>
            </div>

            <div className="flex items-center gap-3 md:gap-5">
              <div className="hidden items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm text-muted sm:flex">
                <Icon name="search" size={16} />
                <span>Search workspace</span>
              </div>

              <div className="relative rounded-lg p-2 text-muted">
                <Icon name="bell" size={20} />
              </div>

              <div className="flex items-center gap-3 border-l border-border pl-3 md:pl-5">
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-semibold text-heading">Workspace User</p>
                  <p className="text-xs text-muted">Development Preview</p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-800">
                  W
                </div>
              </div>
            </div>
          </header>

          {/* Dashboard content */}
          <div className="mx-auto max-w-[1440px] space-y-7 p-5 md:p-8">

            {/* Welcome section */}
            <section className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
              <div>
                <p className="mb-2 text-sm font-medium text-brand-600">
                  FINANCIAL OPERATIONS
                </p>
                <h2 className="text-2xl font-bold tracking-tight text-brand-950 md:text-3xl">
                  Reconciliation Overview
                </h2>
                <p className="mt-2 text-sm text-muted">
                  Monitor reconciliation activity, transactions and exceptions.
                </p>
              </div>

              <div className="flex items-center gap-2 self-start rounded-lg border border-border bg-white px-4 py-2.5 text-sm text-muted">
                <Icon name="clock" size={16} />
                Development preview
              </div>
            </section>

            {/* KPI cards */}
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { label: 'Total Reconciliation Jobs', icon: 'layers', note: 'Job activity' },
                { label: 'Matched Transactions', icon: 'check', note: 'Matching results' },
                { label: 'Open Exceptions', icon: 'alert', note: 'Needs investigation' },
                { label: 'Pending Reviews', icon: 'shield', note: 'Human review queue' },
              ].map((item) => (
                <div key={item.label} className="rx-surface p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-muted">{item.label}</p>
                    <div className="rounded-lg bg-brand-50 p-2.5 text-brand-600">
                      <Icon name={item.icon} size={19} />
                    </div>
                  </div>
                  <p className="mt-5 text-3xl font-bold text-brand-950">—</p>
                  <p className="mt-2 text-xs text-muted">{item.note} · Awaiting integration</p>
                </div>
              ))}
            </section>

            {/* Main dashboard panels */}
            <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">

              <div className="rx-surface p-6 xl:col-span-2">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-brand-950">Reconciliation Activity</h3>
                    <p className="mt-1 text-sm text-muted">
                      Overview of recent processing activity
                    </p>
                  </div>
                  <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
                    Activity overview
                  </span>
                </div>

                <div className="flex min-h-64 flex-col items-center justify-center text-center">
                  <div className="mb-4 rounded-2xl bg-brand-50 p-4 text-brand-600">
                    <Icon name="layers" size={28} />
                  </div>
                  <h4 className="font-semibold text-heading">No reconciliation activity yet</h4>
                  <p className="mt-2 max-w-sm text-sm leading-6 text-muted">
                    Reconciliation activity and processing trends will appear here once the backend workflow is integrated.
                  </p>
                </div>
              </div>

              <div className="rx-surface p-6">
                <h3 className="font-bold text-brand-950">Platform Overview</h3>
                <p className="mt-1 text-sm text-muted">Core operational areas</p>

                <div className="mt-6 space-y-5">
                  {[
                    ['Data ingestion', 'Bank, ledger and gateway files'],
                    ['Matching engine', 'Deterministic transaction matching'],
                    ['Investigation', 'Evidence-based exception analysis'],
                    ['Human in the Loop', 'Authorised review and approval'],
                    ['Reporting', 'Audit-ready reconciliation reports'],
                  ].map(([title, description]) => (
                    <div key={title} className="flex gap-3">
                      <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand-500" />
                      <div>
                        <p className="text-sm font-semibold text-heading">{title}</p>
                        <p className="mt-1 text-xs leading-5 text-muted">{description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* Upload preview */}
            <section className="rx-surface p-6">
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div>
                  <h3 className="font-bold text-brand-950">Source File Ingestion</h3>
                  <p className="mt-1 text-sm text-muted">
                    Reconciliation will process three financial data sources.
                  </p>
                </div>
                <span className="rounded-lg border border-border bg-background px-3 py-2 text-xs font-medium text-muted">
                  Upload functionality · Upcoming implementation
                </span>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                {[
                  ['Bank Statement', 'Bank transaction records'],
                  ['Company Ledger', 'Internal accounting records'],
                  ['Payment Gateway', 'Settlement and payment records'],
                ].map(([title, description]) => (
                  <div key={title} className="rounded-xl border border-dashed border-slate-300 bg-background p-5">
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-white text-brand-600 shadow-sm">
                      <Icon name="upload" size={19} />
                    </div>
                    <h4 className="text-sm font-semibold text-heading">{title}</h4>
                    <p className="mt-1 text-xs leading-5 text-muted">{description}</p>
                  </div>
                ))}
              </div>
            </section>

            <footer className="flex flex-col justify-between gap-2 border-t border-border py-5 text-xs text-muted sm:flex-row">
              <p>© 2026 RECON X · Financial Reconciliation Platform</p>
              <p>Secure · Auditable · Evidence-driven</p>
            </footer>

          </div>
        </main>
      </div>
    </div>
  )
}

export default App
