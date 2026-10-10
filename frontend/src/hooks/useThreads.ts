import { useCallback, useEffect, useState } from 'react'
import type { Thread } from '../types'

const KEY = 'butler.threads'

function load(): Thread[] {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Thread[]) : []
  } catch {
    return []
  }
}

function newThread(): Thread {
  return { id: crypto.randomUUID(), title: 'New chat', updatedAt: Date.now() }
}

/** Conversation list, kept in this browser. Messages themselves live on the server. */
export function useThreads() {
  const [threads, setThreads] = useState<Thread[]>(() => {
    const saved = load()
    return saved.length ? saved : [newThread()]
  })
  const [activeId, setActiveId] = useState(() => threads[0].id)

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(threads))
    } catch {
      /* not persisted in this browser; still works for the session */
    }
  }, [threads])

  const create = useCallback(() => {
    const thread = newThread()
    setThreads((all) => [thread, ...all])
    setActiveId(thread.id)
  }, [])

  const touch = useCallback((id: string, firstMessage?: string) => {
    setThreads((all) =>
      all
        .map((t) =>
          t.id === id
            ? {
                ...t,
                updatedAt: Date.now(),
                title: t.title === 'New chat' && firstMessage ? firstMessage.slice(0, 48) : t.title,
              }
            : t,
        )
        .sort((a, b) => b.updatedAt - a.updatedAt),
    )
  }, [])

  const remove = useCallback(
    (id: string) => {
      setThreads((all) => {
        const rest = all.filter((t) => t.id !== id)
        const next = rest.length ? rest : [newThread()]
        if (id === activeId) setActiveId(next[0].id)
        return next
      })
    },
    [activeId],
  )

  return { threads, activeId, setActiveId, create, touch, remove }
}
