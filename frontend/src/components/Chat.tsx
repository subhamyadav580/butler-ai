import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../api'
import type { ChatMessage, InterruptPayload, Meta, StreamEvent } from '../types'
import { ApprovalCard } from './ApprovalCard'
import { Composer } from './Composer'
import { EmailPicker } from './EmailPicker'
import { Markdown } from './Markdown'
import { Logo } from './Logo'

const EMPTY_META: Meta = { tool_labels: {}, examples: [] }

interface Props {
  threadId: string
  onSent: (text: string) => void
  onTurnFinished: () => void
  onUnauthorized: () => void
}

export function Chat({ threadId, onSent, onTurnFinished, onUnauthorized }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [pending, setPending] = useState<InterruptPayload | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [meta, setMeta] = useState<Meta>(EMPTY_META)

  // Status labels and example prompts come from the integrations (backend)
  useEffect(() => {
    api.getMeta().then(setMeta).catch(() => undefined)
  }, [])

  const handleError = useCallback(
    (err: unknown) => {
      if (err instanceof api.UnauthorizedError) onUnauthorized()
      else setError(err instanceof Error ? err.message : String(err))
    },
    [onUnauthorized],
  )

  // Load this conversation from the server when switching threads
  useEffect(() => {
    let cancelled = false
    setMessages([])
    setPending(null)
    setError(null)
    api
      .getHistory(threadId)
      .then((history) => {
        if (cancelled) return
        setMessages(history.messages)
        setPending(history.pending)
      })
      .catch(handleError)
    return () => {
      cancelled = true
    }
  }, [threadId, handleError])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming, pending, status])

  /** Run one streamed turn (a new message or an answer to a question). */
  const run = async (start: (onEvent: (e: StreamEvent) => void) => Promise<void>) => {
    setBusy(true)
    setError(null)
    setStatus('Thinking')
    let text = ''

    const flush = () => {
      // Copy before resetting: React runs the updater later, after `text = ''`
      const content = text
      if (content.trim()) setMessages((all) => [...all, { role: 'assistant', content }])
      text = ''
      setStreaming('')
    }

    try {
      await start((event) => {
        switch (event.type) {
          case 'token':
            text += event.content
            setStreaming(text)
            setStatus(null)
            break
          case 'tool':
            setStatus(meta.tool_labels[event.name] ?? `Using ${event.name.replaceAll('_', ' ')}`)
            break
          case 'interrupt':
            flush()
            setPending(event.payload)
            break
          case 'done':
            flush()
            break
          case 'error':
            setError(event.message)
            break
        }
      })
    } catch (err) {
      handleError(err)
    } finally {
      flush()
      setStatus(null)
      setBusy(false)
      onTurnFinished()
    }
  }

  const send = (text: string) => {
    onSent(text)
    setMessages((all) => [...all, { role: 'user', content: text }])
    setPending(null) // sending a new message cancels an open question
    void run((onEvent) => api.sendMessage(threadId, text, onEvent))
  }

  const answer = (answerValue: Record<string, unknown>) => {
    if (!pending) return
    const type = pending.type
    setPending(null)
    void run((onEvent) => api.resume(threadId, type, answerValue, onEvent))
  }

  const empty = !messages.length && !streaming && !pending

  return (
    <section className="chat">
      <div className="messages">
        {empty && (
          <div className="empty">
            <Logo size={52} />
            <h1>How can I help?</h1>
            <p>Ask me anything, or about your own mail, calendar, todos and more. Try one of these:</p>
            <div className="examples">
              {meta.examples.slice(0, 6).map((example) => (
                <button key={example} className="example" onClick={() => send(example)} disabled={busy}>
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, i) => (
          <div key={i} className={`message ${message.role}`}>
            {message.role === 'assistant' ? <Markdown text={message.content} /> : message.content}
          </div>
        ))}

        {streaming && (
          <div className="message assistant">
            <Markdown text={streaming} />
          </div>
        )}

        {status && (
          <div className="status" role="status">
            <span className="spinner" aria-hidden /> {status}…
          </div>
        )}

        {pending?.type === 'pick_email' && (
          <EmailPicker payload={pending} disabled={busy} onPick={(id) => answer({ email_id: id })} />
        )}
        {pending?.type === 'confirm_action' && (
          <ApprovalCard payload={pending} disabled={busy} onAnswer={(ok) => answer({ approved: ok })} />
        )}

        {error && <div className="error">{error}</div>}
        <div ref={bottomRef} />
      </div>

      <Composer disabled={busy} onSend={send} />
    </section>
  )
}
