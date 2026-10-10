import { useCallback, useEffect, useState } from 'react'
import * as api from '../api'
import type { Thread } from '../types'

// Only which chat is open is remembered per browser; the list itself lives
// in the server's database so it survives restarts and shows on any device.
const ACTIVE_KEY = 'butler.activeThread'

function loadActive(): string | null {
  try {
    return localStorage.getItem(ACTIVE_KEY)
  } catch {
    return null
  }
}

function saveActive(id: string) {
  try {
    localStorage.setItem(ACTIVE_KEY, id)
  } catch {
    /* not remembered across reloads; still works */
  }
}

/**
 * Sidebar conversations from the server.
 *
 * A new chat is a local "draft" id until its first message; the server
 * creates the thread then, so empty chats never clutter the list.
 */
export function useThreads(onUnauthorized: () => void) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [activeId, setActiveIdState] = useState<string>(() => loadActive() ?? crypto.randomUUID())

  const setActiveId = useCallback((id: string) => {
    setActiveIdState(id)
    saveActive(id)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const { threads } = await api.listThreads()
      setThreads(threads)
    } catch (err) {
      if (err instanceof api.UnauthorizedError) onUnauthorized()
    }
  }, [onUnauthorized])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const isDraft = !threads.some((t) => t.id === activeId)

  const create = useCallback(() => {
    // Already on an empty draft: nothing to do
    if (!isDraft) setActiveId(crypto.randomUUID())
  }, [isDraft, setActiveId])

  const remove = useCallback(
    async (id: string) => {
      await api.deleteThread(id).catch(() => undefined)
      setThreads((all) => all.filter((t) => t.id !== id))
      if (id === activeId) setActiveId(crypto.randomUUID())
    },
    [activeId, setActiveId],
  )

  const rename = useCallback(async (id: string, title: string) => {
    const updated = await api.renameThread(id, title)
    setThreads((all) => all.map((t) => (t.id === id ? updated : t)))
  }, [])

  /** Show the chat at the top of the list immediately; the server confirms on refresh. */
  const noteSent = useCallback((id: string, text: string) => {
    const now = Date.now() / 1000
    setThreads((all) => {
      const existing = all.find((t) => t.id === id)
      const thread = existing
        ? { ...existing, updated_at: now }
        : { id, title: text.replace(/\s+/g, ' ').trim().slice(0, 60), created_at: now, updated_at: now }
      return [thread, ...all.filter((t) => t.id !== id)]
    })
  }, [])

  return { threads, activeId, isDraft, setActiveId, create, remove, rename, refresh, noteSent }
}
