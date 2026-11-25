import { useEffect, useMemo, useRef, useState } from 'react'
import { api, type Project, type Target, type Traffic, type RepeaterResponse } from './api'
import './history.css'

const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8765'
const pretty = (text?: string) => {
  if (!text) return '(empty)'
  try { return JSON.stringify(JSON.parse(text), null, 2) } catch { return text }
}
function safeHeaders(text: string) {
  try { return JSON.stringify(JSON.parse(text), null, 2) } catch { return text }
}
function RequestEditor({ entry, projectId, onResponse }: { entry: Traffic; projectId: number; onResponse: (value: RepeaterResponse) => void }) {
  const [method,setMethod]=useState(entry.method), [url,setUrl]=useState(entry.url), [body,setBody]=useState(entry.request_body??'')
  const [headers,setHeaders]=useState<Record<string,string>>(()=>{try{return JSON.parse(entry.request_headers)}catch{return {}}})
  const [pane,setPane]=useState<'Pretty'|'Raw'|'Headers'|'Params'|'Body'>('Pretty'), [raw,setRaw]=useState(''), [error,setError]=useState(''), [busy,setBusy]=useState(false)
  const [response,setResponse]=useState<RepeaterResponse|null>(null)
  const composeRaw=()=>`${method} ${url} HTTP/1.1\n${Object.entries(headers).map(([k,v])=>`${k}: ${v}`).join('\n')}\n\n${body}`
  const send=async()=>{setError('');setBusy(true);try{
    let nextMethod=method,nextUrl=url,nextHeaders=headers,nextBody=body
    if(pane==='Raw'&&raw){const [line,...rest]=raw.replace(/\r/g,'').split('\n');const match=line.match(/^(\S+)\s+(\S+)\s+(HTTP\/\d(?:\.\d)?)$/);if(!match)throw new Error('Malformed request line. Use METHOD URL HTTP/1.1.');nextMethod=match[1];nextUrl=match[2].startsWith('/')?new URL(match[2],url).toString():match[2];const divider=rest.indexOf('');const headerLines=divider<0?rest:rest.slice(0,divider);nextHeaders={};for(const h of headerLines){const i=h.indexOf(':');if(i<1)throw new Error(`Malformed header: ${h}`);nextHeaders[h.slice(0,i).trim()]=h.slice(i+1).trim()}nextBody=divider<0?'':rest.slice(divider+1).join('\n')}
    const result=await api.repeaterSend({project_id:projectId,parent_id:entry.id,method:nextMethod,url:nextUrl,http_version:'HTTP/1.1',headers:nextHeaders,body:nextBody});setResponse(result);onResponse(result)
  }catch(e){setError(e instanceof Error?e.message:'Send failed')}finally{setBusy(false)}}
  const prettyBody=()=>{try{return JSON.stringify(JSON.parse(body),null,2)}catch{return body}}
  return <div className="request-editor"><div className="repeater-toolbar"><select value={method} onChange={e=>setMethod(e.target.value)}>{['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'].map(m=><option key={m}>{m}</option>)}</select><input aria-label="Request URL" value={url} onChange={e=>setUrl(e.target.value)}/><button className="send-request" disabled={busy} onClick={()=>void send()}>{busy?'Sending…':'Send'}</button></div><div className="editor-tabs">{(['Pretty','Raw','Headers','Params','Body'] as const).map(x=><button className={pane===x?'current':''} onClick={()=>{if(x==='Raw'&&!raw)setRaw(composeRaw());setPane(x)}} key={x}>{x}</button>)}</div>{pane==='Headers'?<textarea value={JSON.stringify(headers,null,2)} onChange={e=>{try{setHeaders(JSON.parse(e.target.value));setError('')}catch{setError('Headers must be a JSON object')}}}/>:pane==='Params'?<div className="param-editor">{(()=>{try{return new URL(url).searchParams.toString()||'No query parameters. Edit the URL to change its parameters.'}catch{return 'Enter a valid URL to inspect query parameters.'}})()}</div>:pane==='Raw'?<textarea aria-label="Raw HTTP request" value={raw||composeRaw()} onChange={e=>setRaw(e.target.value)}/>:pane==='Body'?<textarea value={body} onChange={e=>setBody(e.target.value)}/>:<><div className="copy-line"><b>Headers</b><button onClick={()=>setPane('Headers')}>Edit headers</button></div><pre>{JSON.stringify(headers,null,2)}</pre><div className="copy-line"><b>Body</b><button onClick={()=>setPane('Body')}>Edit body</button></div><textarea value={prettyBody()} onChange={e=>setBody(e.target.value)}/></>}{error&&<p className="repeater-error">{error}</p>}{response&&<div className="repeater-response"><h3>Response · {response.status_code} · {response.response_size.toLocaleString()} B</h3><pre>{JSON.stringify(response.response_headers,null,2)}</pre><pre>{pretty(response.response_body)}</pre></div>}</div>
}

export default function History({ projects }: { projects: Project[] }) {
  const [rows, setRows] = useState<Traffic[]>([])
  const [selected, setSelected] = useState<Traffic | null>(null)
  const [projectId, setProjectId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [targets, setTargets] = useState<Target[]>([])
  const [method, setMethod] = useState('')
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [paused, setPaused] = useState(false)
  const [tab, setTab] = useState<'Choose'|'Request'|'Response'|'Repeater'|'Details'>('Choose')
  const [sort, setSort] = useState<'timestamp'|'duration'|'status'>('timestamp')
  const selectedId = useRef<string | null>(null)
  const filters = useRef({ method, status, search, paused, targetId })
  selectedId.current = selected?.id ?? null
  filters.current = { method, status, search, paused, targetId }

  useEffect(() => { if (!projectId && projects.length) setProjectId(String(projects[0].id)) }, [projectId, projects])
  useEffect(() => {
    setTargetId('')
    if (projectId) void api.targets(Number(projectId)).then(setTargets).catch(() => setTargets([]))
    else setTargets([])
  }, [projectId])
  useEffect(() => {
    let live = true
    const params = new URLSearchParams()
    if (projectId) params.set('project_id', projectId)
    if (targetId) params.set('target_id', targetId)
    if (method) params.set('method', method)
    if (status) params.set('status_code', status)
    if (search) params.set('search', search)
    void api.traffic(`?${params}`).then(data => { if (live) setRows(data) }).catch(() => {})
    return () => { live = false }
  }, [projectId, targetId, method, status, search])

  useEffect(() => {
    let live = true
    const eventParams = new URLSearchParams()
    if (projectId) eventParams.set('project_id', projectId)
    if (targetId) eventParams.set('target_id', targetId)
    const stream = new EventSource(`${API}/api/traffic/events?${eventParams}`)
    stream.onmessage = event => {
      const incoming = JSON.parse(event.data) as Traffic
      if (!live) return
      const filter = filters.current
      const matches = !filter.paused && (!filter.targetId || String(incoming.target_id ?? '') === filter.targetId) && (!filter.method || incoming.method === filter.method) && (!filter.status || String(incoming.status_code ?? '') === filter.status) && (!filter.search || `${incoming.url} ${incoming.hostname}`.toLowerCase().includes(filter.search.toLowerCase()))
      if (matches) setRows(old => [incoming, ...old.filter(row => row.id !== incoming.id)].slice(0, 1000))
      if (selectedId.current === incoming.id) void api.trafficDetail(incoming.id).then(setSelected).catch(() => {})
    }
    return () => { live = false; stream.close() }
  }, [projectId, targetId])

  const sorted = useMemo(() => [...rows].sort((a,b) => sort === 'duration' ? (b.duration_ms ?? 0) - (a.duration_ms ?? 0) : sort === 'status' ? (b.status_code ?? 0) - (a.status_code ?? 0) : b.timestamp.localeCompare(a.timestamp)), [rows, sort])
  const select = async (row: Traffic) => { setTab('Choose'); setSelected(await api.trafficDetail(row.id)) }
  const clear = async () => { if (!window.confirm('Delete the stored traffic history for this project?')) return; await api.clearTraffic(projectId ? Number(projectId) : undefined); setRows([]); setSelected(null) }
  const copy = (value: string) => { void navigator.clipboard?.writeText(value) }

  return <div className="history-page">
    <div className="heading-row"><div><div className="eyebrow"><span className="green-dot"/> LIVE HTTP TRAFFIC</div><h1>History / HTTP Traffic</h1><p className="subtitle">Requests captured by the active scoped proxy.</p></div><div className="traffic-actions"><button className="secondary-button" onClick={() => setPaused(!paused)}>{paused ? 'Resume live' : 'Pause live'}</button><button className="clear-traffic" onClick={() => void clear()}>Clear history</button></div></div>
    <section className="panel traffic-browser"><div className="traffic-filters"><input placeholder="Search URL or host" value={search} onChange={e=>setSearch(e.target.value)}/><select value={projectId} onChange={e=>setProjectId(e.target.value)}><option value="">All projects</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select><select value={targetId} onChange={e=>setTargetId(e.target.value)}><option value="">All targets</option>{targets.map(t=><option key={t.id} value={t.id}>{t.origin}</option>)}</select><select value={method} onChange={e=>setMethod(e.target.value)}><option value="">All methods</option>{['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'].map(x=><option key={x}>{x}</option>)}</select><select value={status} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option>{[200,201,204,301,302,400,401,403,404,500,502,503].map(x=><option key={x}>{x}</option>)}</select><select value={sort} onChange={e=>setSort(e.target.value as typeof sort)}><option value="timestamp">Newest</option><option value="duration">Duration</option><option value="status">Status</option></select></div>
      <div className="traffic-table-wrap"><table className="traffic-table"><thead><tr>{['ID','Method','Status','URL','Host','Content Type','Size','Duration','Timestamp'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{sorted.map(row=><tr key={row.id} className={selected?.id===row.id?'active':''} onClick={()=>void select(row)}><td className="id-cell">{row.id.slice(0,8)}</td><td><span className={`method-tag ${row.method.toLowerCase()}`}>{row.method}</span></td><td><span className={`status-tag s${Math.floor((row.status_code??0)/100)}`}>{row.status_code??'…'}</span></td><td className="url-cell" title={row.url}>{row.url}</td><td>{row.hostname}</td><td>{row.content_type||'—'}</td><td>{(row.request_size+row.response_size).toLocaleString()} B</td><td>{row.duration_ms == null?'…':`${row.duration_ms} ms`}</td><td>{new Date(row.timestamp).toLocaleTimeString()}</td></tr>)}</tbody></table>{!sorted.length&&<div className="traffic-empty">No captured requests. Start the scoped proxy and browse through it.</div>}</div>
    </section>
    {selected&&<section className="panel inspector"><div className="inspector-head"><div><b>{selected.method} {selected.url}</b><small>Traffic ID {selected.id}</small></div><button className="clear-traffic" onClick={()=>setSelected(null)}>Close</button></div>{tab==='Choose'?<div className="entry-actions"><span>Chọn nội dung muốn mở:</span><button onClick={()=>setTab('Request')}>Request</button><button onClick={()=>setTab('Response')}>Response</button><button className="send-request" onClick={()=>setTab('Repeater')}>Open in Repeater</button></div>:<><div className="inspector-tabs">{(['Request','Response','Repeater','Details'] as const).map(x=><button className={tab===x?'current':''} onClick={()=>setTab(x)} key={x}>{x}</button>)}<button onClick={()=>setTab('Choose')}>← Lựa chọn</button></div>
      {(tab==='Request'||tab==='Repeater')&&<div className="inspector-grid"><article><h3>{tab==='Repeater'?'Repeater':'Request editor'} · original {selected.id.slice(0,8)}</h3><RequestEditor key={selected.id} entry={selected} projectId={selected.project_id} onResponse={()=>{void api.traffic(`?project_id=${selected.project_id}`).then(setRows).catch(()=>{})}}/></article></div>}
      {tab==='Response'&&<article className="response-pane"><h3>Status: {selected.status_code??'Pending'} {selected.error&&`· ${selected.error}`}</h3><div className="copy-line"><h3>Headers</h3><button onClick={()=>copy(safeHeaders(selected.response_headers))}>Copy</button></div><pre>{safeHeaders(selected.response_headers)}</pre><div className="copy-line"><h3>Body</h3><button onClick={()=>copy(selected.response_body??'')}>Copy</button></div><pre>{pretty(selected.response_body)}</pre></article>}
      {tab==='Details'&&<dl className="details-list">{[['ID',selected.id],['Project',projects.find(p=>p.id===selected.project_id)?.name??selected.project_id],['Target ID',selected.target_id??'—'],['Timestamp',selected.timestamp],['Duration',selected.duration_ms==null?'Pending':`${selected.duration_ms} ms`],['Request size',selected.request_size],['Response size',selected.response_size],['Content type',selected.content_type||'—'],['Hostname',selected.hostname]].map(([k,v])=><div key={String(k)}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>}
    </>}</section>}
  </div>
}
