import { useEffect, useState } from 'react'
import * as api from '../api'
import type { WebSearchProvider } from '../types'

interface Props {
  /** Called after a change, so the card's status line refreshes. */
  onChange: () => void
}

/** Switch web search providers on/off and pick which one is tried first. */
export function WebSearchProviders({ onChange }: Props) {
  const [providers, setProviders] = useState<WebSearchProvider[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getWebSearchProviders()
      .then(({ providers }) => setProviders(providers))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const save = async (changes: { enabled?: Record<string, boolean>; primary?: string }) => {
    // Optimistic: flip the switch now; the server's answer then fixes the
    // "used first" badge (e.g. when the first provider was just switched off)
    const previous = providers
    setProviders((all) =>
      all.map((p) => ({
        ...p,
        enabled: changes.enabled?.[p.name] ?? p.enabled,
        primary: changes.primary ? p.name === changes.primary : p.primary,
      })),
    )
    setSaving(true)
    setError(null)
    try {
      const { providers } = await api.updateWebSearchProviders(changes)
      setProviders(providers)
      onChange()
    } catch (err) {
      setProviders(previous) // roll back
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  if (!providers.length) return null

  return (
    <div className="providers">
      <ul className="provider-list">
        {providers.map((p) => (
          <li key={p.name} className={`provider ${p.configured ? '' : 'unconfigured'}`}>
            <div className="provider-info">
              <span className="provider-title">
                {p.title}
                {p.primary && <span className="badge connected">Used first</span>}
              </span>
              <span className="muted small">
                {p.configured ? (p.enabled ? 'On' : 'Off') : `No API key. Add ${p.key_setting} to .env`}
              </span>
            </div>

            {p.configured && p.enabled && !p.primary && (
              <button className="btn small ghost" disabled={saving} onClick={() => save({ primary: p.name })}>
                Use first
              </button>
            )}

            <label className="switch" title={p.configured ? undefined : 'Add an API key first'}>
              <input
                type="checkbox"
                role="switch"
                checked={p.configured && p.enabled}
                disabled={!p.configured || saving}
                onChange={(e) => save({ enabled: { [p.name]: e.target.checked } })}
                aria-label={`${p.title} web search`}
              />
              <span className="slider" aria-hidden />
            </label>
          </li>
        ))}
      </ul>
      <p className="muted small">
        Butler tries the provider marked <em>Used first</em>; other enabled ones are fallbacks if it fails.
        Changes apply immediately, on the web and Telegram.
      </p>
      {error && <p className="error small">{error}</p>}
    </div>
  )
}
