import { useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowUpRight, Bug, Compass, FileText,
  Globe2, History, LayoutDashboard, Network, Plus, Radio, Send, Settings,
  Shield, ShieldCheck, SquareTerminal, Wifi,
} from 'lucide-react'
import { api, type Dashboard, type Project, type ProxyStatus, type Target } from './api'
import HistoryPage from './History'
import './proxy.css'

const nav = [
  { title: 'Workspace', items: [['Dashboard', LayoutDashboard], ['Proxy', Radio], ['Sites', Globe2], ['History / HTTP Traffic', History]] },
  { title: 'Testing', items: [['Request editor', SquareTerminal], ['Repeater', Send], ['Scanner', Shield], ['Spider / Crawler', Network]] },
  { title: 'Assessment', items: [['Vulnerabilities', Bug], ['Scope', Compass], ['Reports', FileText]] },
] as const
const notImplemented = new Set([
  'Proxy', 'Sites', 'History / HTTP Traffic', 'Request editor', 'Repeater', 'Scanner',
  'Spider / Crawler', 'Vulnerabilities', 'Scope', 'Reports', 'Settings',
])

function App() {
  const [page, setPage] = useState('Dashboard')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [origin, setOrigin] = useState('')

  const refresh = async () => {
    setLoading(true)
    setError('')
    try {
      const [data, projectList] = await Promise.all([api.dashboard(), api.projects()])
      setDashboard(data)
      setProjects(projectList)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to reach the local API')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [])

  const createProject = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      const project = await api.createProject(projectName, '')
      if (origin.trim()) await api.addTarget(project.id, origin.trim())
      setProjectName('')
      setOrigin('')
      setModal(false)
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create project')
    }
  }

  const cards = [
    { label: 'HTTP requests', value: dashboard?.requests ?? 0, icon: Activity, note: 'Captured traffic' },
    { label: 'Websites', value: dashboard?.websites ?? 0, icon: Globe2, note: 'Configured targets' },
    { label: 'Vulnerabilities', value: dashboard?.vulnerabilities ?? 0, icon: Bug, note: 'Persisted findings' },
    { label: 'Critical findings', value: dashboard?.severity.critical ?? 0, icon: AlertTriangle, note: 'Requires attention' },
  ]

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><ShieldCheck size={20} /></div>
        <div><b>websentinel</b><small>SECURITY WORKSPACE</small></div>
      </div>
      <div className="project-switch">
        <span className="project-dot" />
        <span className="switch-text">{projects[0]?.name ?? 'All projects'}
          <small>{projects.length ? `${projects.length} project${projects.length === 1 ? '' : 's'}` : 'No projects yet'}</small>
        </span>
      </div>
      <button className="new-project" onClick={() => setModal(true)}><Plus size={16} /> New project</button>
      <div className="nav-groups">
        {nav.map(group => <section key={group.title}>
          <div className="nav-title">{group.title}</div>
          {group.items.map(([name, Icon]) => <button key={name}
            className={`nav-item ${page === name ? 'selected' : ''}`} onClick={() => setPage(name)}>
            <Icon size={17} /><span>{name}</span>{notImplemented.has(name) && <i className="soon-dot" />}
          </button>)}
        </section>)}
      </div>
      <div className="sidebar-bottom">
        <button className="nav-item" onClick={() => setPage('Settings')}><Settings size={17} /><span>Settings</span><i className="soon-dot" /></button>
        <div className="user-card"><div className="avatar">W</div><div><b>Local workspace</b><small>Single-user mode</small></div></div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><span>Workspace</span><span className="slash">/</span><b>{page}</b></div>
        <div className="top-actions"><span className="api-status"><i className={error ? 'offline' : 'online'} />{error ? 'API offline' : 'Local API'}</span></div>
      </header>
      <div className="content">
        {page === 'Dashboard' ? <>
          <div className="heading-row">
            <div><div className="eyebrow"><span className="green-dot" /> SECURITY OVERVIEW</div><h1>Dashboard</h1>
              <p className="subtitle">A live view of your authorized security assessments.</p></div>
            <button className="primary-button" onClick={() => setModal(true)}><Plus size={16} /> New project</button>
          </div>
          {error && <div className="error-banner"><Wifi size={17} /><div><b>Backend unavailable</b>
            <p>{error}. Start the FastAPI service to load persisted workspace data.</p></div>
            <button onClick={() => void refresh()}>Retry</button></div>}
          <div className="metric-grid">{cards.map(({ label, value, icon: Icon, note }) => <div className="metric-card" key={label}>
            <div className="metric-top"><span>{label}</span><Icon size={17} /></div>
            <div className="metric-value">{loading ? '—' : value.toLocaleString()}</div>
            <div className="metric-note"><span className="positive">Live data</span><span>{note}</span></div>
          </div>)}</div>
          <div className="section-grid">
            <section className="panel traffic-panel"><div className="panel-heading"><div><h2>Request traffic</h2>
              <p>Requests captured during your assessments</p></div><span className="range-label">Last 7 days</span></div>
              <div className="empty-chart"><div className="chart-grid"><div /><div /><div /><div /></div>
                <div className="chart-center"><div className="chart-icon"><Activity size={20} /></div>
                  <b>No traffic captured yet</b><span>Start a proxy session to see request activity here.</span>
                  <button onClick={() => setPage('Proxy')}>Open proxy <ArrowUpRight size={14} /></button>
                </div><div className="chart-labels"><span>MON</span><span>TUE</span><span>WED</span><span>THU</span><span>FRI</span><span>SAT</span><span>SUN</span></div>
              </div>
            </section>
            <section className="panel severity-panel"><div className="panel-heading"><div><h2>Findings by severity</h2><p>Assessment overview</p></div></div>
              <div className="severity-empty"><div className="donut"><div><b>{loading ? '—' : dashboard?.vulnerabilities ?? 0}</b><small>total</small></div></div>
                <div className="severity-list">{[['Critical', '#f05b67'], ['High', '#f48c57'], ['Medium', '#e9bf63'], ['Low', '#5da9dd'], ['Informational', '#8794a5']].map(([name, color]) =>
                  <div key={name} className="severity-row"><i style={{ background: color }} /><span>{name}</span><b>{loading ? '—' : dashboard?.severity[name.toLowerCase()] ?? 0}</b></div>)}
                </div>
              </div>
            </section>
          </div>
          <section className="panel activity-panel"><div className="panel-heading"><div><h2>Recent activity</h2>
            <p>Latest scans and workspace events</p></div><button className="text-button" onClick={() => setPage('History / HTTP Traffic')}>View history <ArrowUpRight size={14} /></button></div>
            <div className="activity-empty"><div className="activity-symbol"><Activity size={17} /></div>
              <span>{loading ? 'Loading workspace data…' : 'No activity yet'}</span><small>Activity will appear here as you work with targets.</small>
            </div>
          </section>
          <footer className="footer"><span><i className={error ? 'offline' : 'online'} />{error ? 'Disconnected' : 'All systems operational'}</span>
            <span>WebSentinel <b>v0.1.0 · Phase 2</b></span></footer>
        </> : page === 'Proxy' ? <ProxyWorkspace projects={projects} /> : page === 'History / HTTP Traffic' ? <HistoryPage projects={projects} /> : <div className="module-state"><div className="heading-row"><div><div className="eyebrow">WORKSPACE MODULE</div><h1>{page}</h1>
          <p className="subtitle">{page === 'Scope' ? 'Basic origin checks run in the backend; scope management is not implemented yet.' : 'This module has not been implemented yet.'}</p>
        </div></div><div className="panel not-implemented"><div className="module-icon"><Shield size={20} /></div>
          <b>Not implemented</b><span>This workspace does not simulate module activity or findings.</span></div></div>}
      </div>
    </main>

    {modal && <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setModal(false) }}>
      <form className="modal" onSubmit={createProject}><div className="modal-head"><div className="brand-mark"><Plus size={18} /></div>
        <button type="button" className="icon-button" onClick={() => setModal(false)}>×</button></div>
        <h2>Create a project</h2><p>Projects keep targets and assessment data organized.</p>
        <label>Project name<input autoFocus required maxLength={120} value={projectName} onChange={event => setProjectName(event.target.value)} placeholder="e.g. Acme staging" /></label>
        <label>Initial target origin <span className="optional">OPTIONAL</span><input type="url" value={origin} onChange={event => setOrigin(event.target.value)} placeholder="https://staging.example.com" /></label>
        {error && <div className="form-error">{error}</div>}
        <button className="primary-button full" type="submit"><Plus size={16} /> Create project</button>
        <small className="scope-hint"><Shield size={13} /> Only add systems you own or are authorized to assess.</small>
      </form>
    </div>}
  </div>
}

function ProxyWorkspace({ projects }: { projects: Project[] }) {
  const [status, setStatus] = useState<ProxyStatus | null>(null)
  const [projectId, setProjectId] = useState('')
  const [port, setPort] = useState('8080')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [targets, setTargets] = useState<Target[]>([])
  const [targetId, setTargetId] = useState('')

  useEffect(() => {
    if (!projectId && projects.length) setProjectId(String(projects[0].id))
  }, [projectId, projects])

  useEffect(() => {
    if (!projectId) { setTargets([]); return }
    void api.targets(Number(projectId)).then(items => { setTargets(items); setTargetId(items[0] ? String(items[0].id) : '') }).catch(() => setTargets([]))
  }, [projectId])

  useEffect(() => {
    let alive = true
    const loadStatus = async () => {
      try { const current = await api.proxyStatus(); if (alive) setStatus(current) }
      catch (cause) { if (alive) setError(cause instanceof Error ? cause.message : 'Unable to load proxy status') }
    }
    void loadStatus()
    const timer = window.setInterval(() => void loadStatus(), 2500)
    return () => { alive = false; window.clearInterval(timer) }
  }, [])

  const run = async (action: () => Promise<ProxyStatus>) => {
    setBusy(true)
    setError('')
    try { setStatus(await action()) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Proxy operation failed') }
    finally { setBusy(false) }
  }

  const start = () => {
    const selectedProject = Number(projectId)
    const listenPort = Number(port)
    if (!selectedProject || !Number.isInteger(listenPort) || listenPort < 1024 || listenPort > 65535) {
      setError('Choose a project and a port from 1024 to 65535.')
      return
    }
    void run(() => api.startProxy(selectedProject, listenPort))
  }

  const openTarget = async () => {
    const target = targets.find(item => String(item.id) === targetId)
    if (!target) { setError('Select a configured target first.'); return }
    if (!status?.running || status.project_id !== Number(projectId)) { setError('Start the proxy for this project first.'); return }
    if (!window.websentinel) { setError('Open Target is available in the WebSentinel desktop app.'); return }
    try { await window.websentinel?.openTarget(Number(projectId), target.origin); setError('') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not open target') }
  }

  return <>
    <div className="heading-row">
      <div><div className="eyebrow"><span className={status?.running ? 'green-dot' : 'gray-dot'} /> LOCAL INTERCEPTING PROXY</div>
        <h1>HTTP Proxy</h1><p className="subtitle">Route an authorized test browser through WebSentinel.</p></div>
      <div className={`proxy-state ${status?.running ? 'is-running' : ''}`}><i className={status?.running ? 'online' : 'offline'} />{status?.running ? 'Running' : 'Stopped'}</div>
    </div>
    {error && <div className="error-banner"><Wifi size={17} /><div><b>Proxy operation failed</b><p>{error}</p></div><button onClick={() => setError('')}>Dismiss</button></div>}
    <div className="proxy-layout">
      <section className="panel proxy-config"><div className="panel-heading"><div><h2>Proxy listener</h2><p>Bound to this computer only</p></div></div>
        <label>Project scope<select value={projectId} disabled={status?.running || busy} onChange={event => setProjectId(event.target.value)}>
          <option value="">Select project</option>{projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}
        </select></label>
        <label>Configured target<select value={targetId} onChange={event => setTargetId(event.target.value)}><option value="">Select target</option>{targets.map(target => <option key={target.id} value={target.id}>{target.origin}</option>)}</select></label>
        <div className="proxy-fields"><label>Host<input value="127.0.0.1" readOnly /></label><label>Port<input type="number" min="1024" max="65535" value={port} disabled={status?.running || busy} onChange={event => setPort(event.target.value)} /></label></div>
        {status?.running
          ? <button className="stop-button" disabled={busy} onClick={() => void run(api.stopProxy)}>{busy ? 'Stopping…' : 'Stop proxy'}</button>
          : <button className="primary-button full" disabled={busy || !projects.length} onClick={start}>{busy ? 'Starting…' : 'Start proxy'}</button>}
        <div className="proxy-endpoint"><span>HTTP and HTTPS proxy</span><code>{status?.host ?? '127.0.0.1'}:{status?.port ?? port}</code></div>
        <button className="secondary-button open-target" disabled={!status?.running || status.project_id !== Number(projectId) || !targetId} onClick={() => void openTarget()}>Open Target in test browser</button>
        <p className="browser-note">The opened browser must already use this proxy in its disposable profile. WebSentinel does not change system proxy settings or browser certificates.</p>
      </section>
      <section className="panel proxy-help"><div className="panel-heading"><div><h2>Configure a test browser</h2><p>Use only a browser profile for your authorized lab.</p></div></div>
        <ol><li>Set both HTTP and HTTPS proxy fields to <code>127.0.0.1:{status?.port ?? port}</code>.</li>
          <li>Trust the mitmproxy CA only in the disposable test browser profile.</li>
          <li>Browse to a configured target. Other origins receive a local 403 response.</li></ol>
        {status?.ca_available
          ? <button className="secondary-button" onClick={() => { void api.downloadProxyCA().catch(cause => setError(cause instanceof Error ? cause.message : 'CA download failed')) }}>Download proxy CA</button>
          : <div className="ca-pending">The CA file is created when the proxy starts.</div>}
        <p className="ca-warning">WebSentinel never installs this certificate automatically. Remove it from the test profile when you finish.</p>
      </section>
    </div>
  </>
}

export default App
