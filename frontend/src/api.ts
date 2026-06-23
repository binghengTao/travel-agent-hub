/**
 * 本文件属于前端 TypeScript 逻辑层，注释说明状态、请求和路由等关键职责。
 * 注释只解释工程意图和边界，不修改任何输入输出结构。
 */
import { useAuthStore } from './stores/auth'
import { useSessionStore } from './stores/session'

export type Source = {
  source: string
  city?: string
  page?: number
  chunk_id: string
  score?: number
  preview: string
  scope?: string
  owner_id?: string
  source_type?: string
  trust_level?: string
}
// 说明：apiGet 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
export async function apiGet<T>(path: string, headers: Record<string, string> = {}): Promise<T> {
  const session = useSessionStore()
  // 所有请求都从 session store 读取 apiBase，方便本地、Docker、服务器部署切换。
  const response = await fetch(`${session.apiBase}${path}`, { headers: authHeaders(headers) })
  return handleResponse<T>(response)
}
// 说明：apiPost 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
export async function apiPost<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  const session = useSessionStore()
  const response = await fetch(`${session.apiBase}${path}`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json', ...headers }),
    body: JSON.stringify(body)
  })
  return handleResponse<T>(response)
}
// 说明：apiPut 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
export async function apiPut<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  const session = useSessionStore()
  const response = await fetch(`${session.apiBase}${path}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json', ...headers }),
    body: JSON.stringify(body)
  })
  return handleResponse<T>(response)
}
// 说明：apiDelete 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
export async function apiDelete<T>(path: string, headers: Record<string, string> = {}): Promise<T> {
  const session = useSessionStore()
  const response = await fetch(`${session.apiBase}${path}`, { method: 'DELETE', headers: authHeaders(headers) })
  return handleResponse<T>(response)
}
// 说明：apiUpload 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
export async function apiUpload<T>(path: string, fieldName: string, file: File, headers: Record<string, string> = {}): Promise<T> {
  const session = useSessionStore()
  const data = new FormData()
  data.append(fieldName, file)
  const response = await fetch(`${session.apiBase}${path}`, { method: 'POST', body: data, headers: authHeaders(headers) })
  return handleResponse<T>(response)
}
// 说明：apiUploadForm 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
export async function apiUploadForm<T>(path: string, data: FormData, headers: Record<string, string> = {}): Promise<T> {
  const session = useSessionStore()
  const response = await fetch(`${session.apiBase}${path}`, { method: 'POST', body: data, headers: authHeaders(headers) })
  return handleResponse<T>(response)
}
// 说明：streamPost 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
export async function streamPost(path: string, body: unknown, onToken: (token: string, payload: any) => void): Promise<any> {
  const session = useSessionStore()
  // SSE/流式接口仍然复用统一鉴权头，后端 401 时会触发前端退出登录。
  const response = await fetch(`${session.apiBase}${path}`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body)
  })
  if (!response.ok || !response.body) {
    if (response.status === 401) useAuthStore().logout()
    throw new Error(await readableError(response))
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let donePayload: any = null
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    // 后端按 SSE 协议用空行分隔事件，这里保留 buffer 处理半包。
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const event of events) {
      const dataLine = event.split('\n').find((line) => line.startsWith('data: '))
      const eventLine = event.split('\n').find((line) => line.startsWith('event: '))
      if (!dataLine) continue
      let payload: any
      try { payload = JSON.parse(dataLine.slice(6)) } catch { continue }
      if (eventLine?.includes('token')) onToken(payload.token || '', payload)
      if (eventLine?.includes('done')) donePayload = payload
    }
  }
  return donePayload
}
// 说明：authHeaders 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
function authHeaders(headers: Record<string, string> = {}) {
  const auth = useAuthStore()
  // JWT 只在请求头中透传，具体用户身份由后端 current_user 解析，前端不信任本地 user 字段。
  return auth.accessToken ? { ...headers, Authorization: `Bearer ${auth.accessToken}` } : headers
}
// 说明：handleResponse 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    // 认证失效时主动清理本地 token，路由守卫会把用户带回登录页。
    if (response.status === 401) useAuthStore().logout()
    throw new Error(await readableError(response))
  }
  return unwrapEnvelope(await response.json())
}
// 说明：readableError 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
async function readableError(response: Response) {
  const raw = await response.text()
  try {
    const payload = JSON.parse(raw)
    return payload.detail || payload.message || raw || '请求失败'
  } catch {
    return raw || '请求失败'
  }
}
// 说明：unwrapEnvelope 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
function unwrapEnvelope<T>(payload: T | { code: number; message: string; data: T }): T {
  // 后端新接口统一返回 {code,message,data}，旧接口可能直接返回业务对象，这里同时兼容。
  if (payload && typeof payload === 'object' && 'code' in payload && 'data' in payload) {
    const envelope = payload as { code: number; message: string; data: T }
    if (envelope.code !== 0) throw new Error(envelope.message)
    return envelope.data
  }
  return payload as T
}
