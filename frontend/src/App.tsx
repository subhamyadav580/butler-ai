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
  const { threads, activeId, setActiveId, create, touch, remove } = useThreads()

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
  const onFirstMessage = useCallback((text: string) => touch(activeId, text), [touch, activeId])

  const deleteThread = async (id: string) => {
    await api.resetThread(id).catch(() => undefined)
    remove(id)
  }

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
          {threads.map((thread) => (
            <div key={thread.id} className={`thread ${thread.id === activeId && view === 'chat' ? 'active' : ''}`}>
              <button
                className="thread-title"
                onClick={() => {
                  setActiveId(thread.id)
                  setView('chat')
                  setSidebarOpen(false)
                }}
              >
                {thread.title}
              </button>
              <button className="thread-delete" aria-label="Delete conversation" onClick={() => deleteThread(thread.id)}>
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
          <span>{view === 'chat' ? threads.find((t) => t.id === activeId)?.title : 'Integrations'}</span>
        </header>

        {view === 'chat' ? (
          <Chat key={activeId} threadId={activeId} onFirstMessage={onFirstMessage} onUnauthorized={onUnauthorized} />
        ) : (
          <Integrations onUnauthorized={onUnauthorized} />
        )}
      </main>
    </div>
  )
}
