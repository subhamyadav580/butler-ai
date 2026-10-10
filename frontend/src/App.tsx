import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import { Chat } from './components/Chat'
import { Integrations } from './components/Integrations'
import { Login } from './components/Login'
import { useThreads } from './hooks/useThreads'

type View = 'chat' | 'integrations'
type AuthState = 'checking' | 'needs_login' | 'ok'

export default function App() {
  const [auth, setAuth] = useState<AuthState>('checking')
  const [view, setView] = useState<View>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Ask the server whether a password is needed, then verify our token works
  useEffect(() => {
    api
      .authStatus()
      .then(async ({ auth_required }) => {
        if (!auth_required) return setAuth('ok')
        try {
          await api.listIntegrations()
          setAuth('ok')
        } catch {
          setAuth('needs_login')
        }
      })
      .catch(() => setAuth('ok'))
  }, [])

  const onUnauthorized = useCallback(() => setAuth('needs_login'), [])
  const { threads, activeId, isDraft, setActiveId, create, remove, rename, refresh, noteSent } =
    useThreads(onUnauthorized)
  const [editingId, setEditingId] = useState<string | null>(null)

  const onSent = useCallback((text: string) => noteSent(activeId, text), [noteSent, activeId])
  const onTurnFinished = useCallback(() => void refresh(), [refresh])

  const finishRename = (id: string, title: string) => {
    setEditingId(null)
    const clean = title.trim()
    const current = threads.find((t) => t.id === id)?.title
    if (clean && clean !== current) void rename(id, clean)
  }

  const activeTitle = isDraft ? 'New chat' : threads.find((t) => t.id === activeId)?.title

  if (auth === 'checking') return null
  if (auth === 'needs_login') return <Login onLoggedIn={() => setAuth('ok')} />

  return (
    <div className="app">
      {sidebarOpen && <div className="backdrop" onClick={() => setSidebarOpen(false)} aria-hidden />}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand">Butler</div>
        <button
          className="btn primary block"
          onClick={() => {
            create()
            setView('chat')
            setSidebarOpen(false)
          }}
        >
          + New chat
        </button>

        <nav className="threads" aria-label="Conversations">
          {isDraft && view === 'chat' && (
            <div className="thread active">
              <span className="thread-title draft">New chat</span>
            </div>
          )}
          {threads.map((thread) => (
            <div key={thread.id} className={`thread ${thread.id === activeId && view === 'chat' ? 'active' : ''}`}>
              {editingId === thread.id ? (
                <input
                  className="thread-rename"
                  defaultValue={thread.title}
                  aria-label="Conversation name"
                  autoFocus
                  onBlur={(e) => finishRename(thread.id, e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') finishRename(thread.id, e.currentTarget.value)
                    if (e.key === 'Escape') setEditingId(null)
                  }}
                />
              ) : (
                <button
                  className="thread-title"
                  title="Double-click to rename"
                  onClick={() => {
                    setActiveId(thread.id)
                    setView('chat')
                    setSidebarOpen(false)
                  }}
                  onDoubleClick={() => setEditingId(thread.id)}
                >
                  {thread.title}
                </button>
              )}
              <button className="thread-delete" aria-label="Delete conversation" onClick={() => void remove(thread.id)}>
                ×
              </button>
            </div>
          ))}
        </nav>

        <button
          className={`nav-link ${view === 'integrations' ? 'active' : ''}`}
          onClick={() => {
            setView('integrations')
            setSidebarOpen(false)
          }}
        >
          ⚙ Integrations
        </button>
      </aside>

      <main className="main">
        <header className="topbar">
          <button className="menu" aria-label="Open menu" onClick={() => setSidebarOpen((open) => !open)}>
            ☰
          </button>
          <span>{view === 'chat' ? activeTitle : 'Integrations'}</span>
        </header>

        {view === 'chat' ? (
          <Chat
            key={activeId}
            threadId={activeId}
            onSent={onSent}
            onTurnFinished={onTurnFinished}
            onUnauthorized={onUnauthorized}
          />
        ) : (
          <Integrations onUnauthorized={onUnauthorized} />
        )}
      </main>
    </div>
  )
}
