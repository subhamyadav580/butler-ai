import { useCallback, useEffect, useState } from 'react'
import * as api from '../api'
import type { IntegrationStatus } from '../types'
import { WebSearchProviders } from './WebSearchProviders'

const STATE_LABELS: Record<IntegrationStatus['state'], string> = {
  connected: 'Connected',
  disconnected: 'Not connected',
  needs_setup: 'Setup needed',
}

export function Integrations({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [items, setItems] = useState<IntegrationStatus[]>([])
  const [error, setError] = useState<string | null>(null)
  const [reloading, setReloading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await api.listIntegrations()
      setItems(data.integrations)
      setError(null)
    } catch (err) {
      if (err instanceof api.UnauthorizedError) onUnauthorized()
      else setError(err instanceof Error ? err.message : String(err))
    }
  }, [onUnauthorized])

  useEffect(() => {
    void refresh()
  }, [refresh])

  // Poll while a login is running in the background
  const anyConnecting = items.some((item) => item.connecting)
  useEffect(() => {
    if (!anyConnecting) return
    const timer = setInterval(() => void refresh(), 2000)
    return () => clearInterval(timer)
  }, [anyConnecting, refresh])

  const connect = async (name: string) => {
    try {
      await api.connectIntegration(name)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const reload = async () => {
    setReloading(true)
    try {
      await api.reloadAgent()
      await refresh()
    } finally {
      setReloading(false)
    }
  }

  const needsReload = items.filter((i) => i.needs_reload).map((i) => i.title)

  return (
    <section className="page">
      <h1>Integrations</h1>
      <p className="muted">
        Connect your own accounts. Logins open in a browser on the machine running Butler, and tokens
        are stored only in its <code>secrets/</code> folder.
      </p>

      {error && <div className="error">{error}</div>}

      {needsReload.length > 0 && (
        <div className="notice">
          {needsReload.join(', ')}: connected, but the agent needs a reload to use it.
          <button className="btn small" onClick={reload} disabled={reloading}>
            {reloading ? 'Reloading…' : 'Reload agent'}
          </button>
        </div>
      )}

      <div className="integrations">
        {items.map((item) => (
          <article key={item.name} className="integration">
            <header>
              <h2>{item.title}</h2>
              <span className={`badge ${item.state}`}>{STATE_LABELS[item.state]}</span>
            </header>
            <p>{item.description}</p>
            <p className="muted small">{item.detail}</p>
            {item.error && <p className="error small">{item.error}</p>}
            {item.name === 'web_search' && item.state !== 'needs_setup' && (
              <WebSearchProviders onChange={() => void refresh()} />
            )}
            {item.can_connect && item.state !== 'needs_setup' && (
              <button
                className={`btn ${item.state === 'connected' ? 'ghost' : 'primary'}`}
                disabled={item.connecting}
                onClick={() => connect(item.name)}
              >
                {item.connecting
                  ? 'Waiting for login in the browser…'
                  : item.state === 'connected'
                    ? 'Reconnect'
                    : 'Connect'}
              </button>
            )}
          </article>
        ))}
      </div>

      <p className="muted small">
        Reconnecting resets open conversations, because the agent reloads its tools.
      </p>
    </section>
  )
}
