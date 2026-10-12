import type {
  ChatMessage,
  IntegrationStatus,
  InterruptPayload,
  Priority,
  StreamEvent,
  Thread,
  Todo,
  Meta,
  TodoList,
  WebSearchProvider,
} from './types'

const TOKEN_KEY = 'butler.token'

function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    /* storage unavailable: stay logged in for this tab only */
  }
}

export class UnauthorizedError extends Error {}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
      ...init.headers,
    },
  })
  if (response.status === 401) throw new UnauthorizedError('Login required')
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

// --- Auth ----------------------------------------------------------------

export const authStatus = () => request<{ auth_required: boolean }>('/api/auth/status')

export async function login(password: string) {
  const { token } = await request<{ token: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
  setToken(token)
}

// --- Chat ----------------------------------------------------------------

export const getHistory = (threadId: string) =>
  request<{ messages: ChatMessage[]; pending: InterruptPayload | null }>(
    `/api/chat/threads/${encodeURIComponent(threadId)}`,
  )

export const listThreads = () => request<{ threads: Thread[] }>('/api/chat/threads')

export const renameThread = (threadId: string, title: string) =>
  request<Thread>(`/api/chat/threads/${encodeURIComponent(threadId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })

export const deleteThread = (threadId: string) =>
  request<{ ok: boolean }>(`/api/chat/threads/${encodeURIComponent(threadId)}`, { method: 'DELETE' })

/** POST and read the Server-Sent Events stream, calling onEvent per event. */
async function streamEvents(path: string, body: unknown, onEvent: (event: StreamEvent) => void) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify(body),
  })
  if (response.status === 401) throw new UnauthorizedError('Login required')
  if (!response.ok || !response.body) {
    const detail = await response.json().catch(() => ({}))
    throw new Error(typeof detail.detail === 'string' ? detail.detail : `Request failed (${response.status})`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      for (const line of frame.split('\n')) {
        if (line.startsWith('data: ')) onEvent(JSON.parse(line.slice(6)) as StreamEvent)
      }
    }
  }
}

export const sendMessage = (threadId: string, message: string, onEvent: (e: StreamEvent) => void) =>
  streamEvents('/api/chat/messages', { thread_id: threadId, message }, onEvent)

export const resume = (
  threadId: string,
  type: InterruptPayload['type'],
  answer: Record<string, unknown>,
  onEvent: (e: StreamEvent) => void,
) => streamEvents('/api/chat/resume', { thread_id: threadId, type, answer }, onEvent)

// --- Integrations ----------------------------------------------------------

export const listIntegrations = () =>
  request<{ integrations: IntegrationStatus[] }>('/api/integrations')

export const connectIntegration = (name: string) =>
  request<{ started: boolean }>(`/api/integrations/${name}/connect`, { method: 'POST' })

export const reloadAgent = () =>
  request<{ ok: boolean }>('/api/integrations/reload', { method: 'POST' })

// --- Todos -------------------------------------------------------------------

export type TodoStatus = 'open' | 'done' | 'all'

export interface TodoInput {
  title?: string
  due?: string | null
  clear_due?: boolean
  list?: string
  priority?: Priority
  notes?: string
  done?: boolean
}

export const listTodos = (status: TodoStatus) =>
  request<{ todos: Todo[] }>(`/api/todos?status=${status}`)

export const listTodoLists = () => request<{ lists: TodoList[] }>('/api/todos/lists')

export const createTodo = (todo: TodoInput & { title: string }) =>
  request<Todo>('/api/todos', { method: 'POST', body: JSON.stringify(todo) })

export const updateTodo = (id: number, changes: TodoInput) =>
  request<Todo>(`/api/todos/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })

export const deleteTodo = (id: number) =>
  request<{ ok: boolean }>(`/api/todos/${id}`, { method: 'DELETE' })

// --- Web search providers -----------------------------------------------------

export const getWebSearchProviders = () =>
  request<{ providers: WebSearchProvider[] }>('/api/integrations/web-search')

export const updateWebSearchProviders = (changes: { enabled?: Record<string, boolean>; primary?: string }) =>
  request<{ providers: WebSearchProvider[] }>('/api/integrations/web-search', {
    method: 'PUT',
    body: JSON.stringify(changes),
  })

// --- Meta: tool status labels and example prompts from every integration -------

let metaPromise: Promise<Meta> | null = null

/** Fetched once per page load and shared. */
export function getMeta(): Promise<Meta> {
  metaPromise ??= request<Meta>('/api/integrations/meta').catch((err) => {
    metaPromise = null // retry next time
    throw err
  })
  return metaPromise
}
