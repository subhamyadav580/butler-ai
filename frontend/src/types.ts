export type Role = 'user' | 'assistant'

export interface ChatMessage {
  role: Role
  content: string
}

export interface EmailSummary {
  id: string
  from: string
  to: string
  subject: string
  date: string
  snippet: string
  unread: boolean
}

export interface PickEmailPayload {
  type: 'pick_email'
  question: string
  emails: EmailSummary[]
}

export interface ConfirmActionPayload {
  type: 'confirm_action'
  question: string
  tool: string
  args: Record<string, unknown>
  details: string | null
}

export type InterruptPayload = PickEmailPayload | ConfirmActionPayload

export type StreamEvent =
  | { type: 'token'; content: string }
  | { type: 'tool'; name: string }
  | { type: 'interrupt'; payload: InterruptPayload }
  | { type: 'done'; content: string }
  | { type: 'error'; message: string }

export interface Thread {
  id: string
  title: string
  updatedAt: number
}

export interface IntegrationStatus {
  name: string
  title: string
  description: string
  state: 'connected' | 'disconnected' | 'needs_setup'
  detail: string
  connecting: boolean
  error: string | null
  expires_at: number | null
}
