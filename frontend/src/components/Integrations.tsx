import { useCallback, useEffect, useState } from 'react'
import * as api from '../api'
import type { IntegrationStatus } from '../types'

const STATE_LABELS: Record<IntegrationStatus['state'], string> = {
  connected: 'Connected',
  disconnected: 'Not connected',
  needs_setup: 'Setup needed',
}

export function Integrations({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [items, setItems] = useState<IntegrationStatus[]>([])
  const [agentHasSwiggy, setAgentHasSwiggy] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloading, setReloading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await api.listIntegrations()
      setItems(data.integrations)
      setAgentHasSwiggy(data.agent_has_swiggy)
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
      const result = await api.reloadAgent()
      setAgentHasSwiggy(result.agent_has_swiggy)
      await refresh()
    } finally {
      setReloading(false)
    }
  }

  const swiggyConnected = items.some((i) => i.name === 'swiggy' && i.state === 'connected')

  return (
    <section className="page">
      <h1>Integrations</h1>
      <p className="muted">
        Connect your own accounts. Logins open in a browser on the machine running Butler, and tokens
        are stored only in its <code>secrets/</code> folder.
      </p>

      {error && <div className="error">{error}</div>}

      {swiggyConnected && !agentHasSwiggy && (
        <div className="notice">
          Swiggy is connected but the agent was started without it.
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
            {item.state !== 'needs_setup' && (
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
