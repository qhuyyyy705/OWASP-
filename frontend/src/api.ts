const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8765'
export type Dashboard = { projects: number; websites: number; requests: number; vulnerabilities: number; severity: Record<string, number>; recent_activity: unknown[]; traffic: unknown[]; implemented: string[] }
export type Project = { id: number; name: string; description: string; created_at: string }
export type ProxyStatus = { running: boolean; host: string; port: number; project_id: number | null; started_at: string | null; ca_available: boolean }
export type Target = { id: number; project_id: number; origin: string; created_at: string }
export type Traffic = { id: string; project_id: number; target_id: number | null; timestamp: string; method: string; url: string; hostname: string; path: string; query_params: string; http_version: string; status_code: number | null; request_headers: string; response_headers: string; request_body?: string; response_body?: string; request_size: number; response_size: number; content_type: string; duration_ms: number | null; error: string }
export type RepeaterResponse = { status_code: number; duration_ms: number | null; response_headers: Record<string,string>; response_body: string; response_size: number; content_type: string }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/api${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? `API error ${response.status}`) }
  return response.json()
}
export const api = {
  dashboard: () => request<Dashboard>('/dashboard'),
  projects: () => request<Project[]>('/projects'),
  createProject: (name: string, description: string) => request<Project>('/projects', { method: 'POST', body: JSON.stringify({ name, description }) }),
  addTarget: (id: number, origin: string) => request(`/projects/${id}/targets`, { method: 'POST', body: JSON.stringify({ origin }) }),
  targets: (id: number) => request<Target[]>(`/projects/${id}/targets`),
  traffic: (filters = '') => request<Traffic[]>(`/traffic${filters}`),
  trafficDetail: (id: string) => request<Traffic>(`/traffic/${id}`),
  repeaterSend: (value: { project_id:number; parent_id:string; name?:string; method:string; url:string; http_version:string; headers:Record<string,string>; body:string }) => request<RepeaterResponse>('/repeater/send',{method:'POST',body:JSON.stringify(value)}),
  clearTraffic: (projectId?: number) => request<{ deleted: number }>(`/traffic${projectId ? `?project_id=${projectId}` : ''}`, { method: 'DELETE' }),
  proxyStatus: () => request<ProxyStatus>('/proxy/status'),
  startProxy: (project_id: number, port: number) => request<ProxyStatus>('/proxy/start', { method: 'POST', body: JSON.stringify({ project_id, host: '127.0.0.1', port }) }),
  stopProxy: () => request<ProxyStatus>('/proxy/stop', { method: 'POST' }),
  downloadProxyCA: async () => {
    const response = await fetch(`${API}/api/proxy/ca`)
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? `API error ${response.status}`) }
    const link = document.createElement('a')
    link.href = URL.createObjectURL(await response.blob())
    link.download = 'mitmproxy-ca-cert.pem'
    link.click()
    URL.revokeObjectURL(link.href)
  },
}
