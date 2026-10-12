import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import * as api from '../api'
import type { Priority, Todo, TodoList } from '../types'

const FILTERS: { value: api.TodoStatus; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'done', label: 'Done' },
  { value: 'all', label: 'All' },
]

export function Todos({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [todos, setTodos] = useState<Todo[]>([])
  const [lists, setLists] = useState<TodoList[]>([])
  const [filter, setFilter] = useState<api.TodoStatus>('open')
  const [error, setError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)

  const [title, setTitle] = useState('')
  const [due, setDue] = useState('')
  const [listName, setListName] = useState('')
  const [priority, setPriority] = useState<Priority>('normal')

  const handleError = useCallback(
    (err: unknown) => {
      if (err instanceof api.UnauthorizedError) onUnauthorized()
      else setError(err instanceof Error ? err.message : String(err))
    },
    [onUnauthorized],
  )

  const refresh = useCallback(async () => {
    try {
      const [{ todos }, { lists }] = await Promise.all([api.listTodos(filter), api.listTodoLists()])
      setTodos(todos)
      setLists(lists)
      setError(null)
    } catch (err) {
      handleError(err)
    } finally {
      setLoaded(true)
    }
  }, [filter, handleError])

  useEffect(() => {
    void refresh()
    // Butler may change todos from the chat or Telegram: refresh on return
    const onFocus = () => void refresh()
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [refresh])

  const add = async (event: FormEvent) => {
    event.preventDefault()
    if (!title.trim()) return
    try {
      await api.createTodo({
        title: title.trim(),
        due: due || null,
        list: listName.trim() || undefined,
        priority,
      })
      setTitle('')
      setDue('')
      setPriority('normal')
      await refresh()
    } catch (err) {
      handleError(err)
    }
  }

  const toggle = async (todo: Todo) => {
    // Optimistic: tick immediately, then reload in the server's order
    setTodos((all) => all.map((t) => (t.id === todo.id ? { ...t, done: !t.done } : t)))
    try {
      await api.updateTodo(todo.id, { done: !todo.done })
      await refresh()
    } catch (err) {
      handleError(err)
    }
  }

  const remove = async (todo: Todo) => {
    setTodos((all) => all.filter((t) => t.id !== todo.id))
    try {
      await api.deleteTodo(todo.id)
      await refresh()
    } catch (err) {
      handleError(err)
    }
  }

  // Group by list, keeping the server's order (overdue and soonest first)
  const groups = useMemo(() => {
    const byList = new Map<string, Todo[]>()
    for (const todo of todos) byList.set(todo.list, [...(byList.get(todo.list) ?? []), todo])
    return [...byList.entries()]
  }, [todos])

  const openCount = lists.reduce((sum, l) => sum + l.open, 0)

  return (
    <section className="page">
      <h1>Todos</h1>
      <p className="muted">
        {openCount} open · You can also ask Butler: <em>"remind me to pay rent on Friday"</em>,{' '}
        <em>"what's on my list?"</em>, <em>"mark the rent one done"</em>.
      </p>

      <form className="todo-add" onSubmit={add}>
        <input
          className="todo-title-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Add a todo…"
          aria-label="New todo"
        />
        <div className="todo-add-options">
          <input type="date" value={due} onChange={(e) => setDue(e.target.value)} aria-label="Due date" />
          <input
            list="todo-lists"
            value={listName}
            onChange={(e) => setListName(e.target.value)}
            placeholder="List (Inbox)"
            aria-label="List"
          />
          <datalist id="todo-lists">
            {lists.map((l) => (
              <option key={l.name} value={l.name} />
            ))}
          </datalist>
          <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)} aria-label="Priority">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </select>
          <button className="btn primary" type="submit" disabled={!title.trim()}>
            Add
          </button>
        </div>
      </form>

      <div className="todo-filters" role="tablist" aria-label="Show">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            role="tab"
            aria-selected={filter === f.value}
            className={`chip ${filter === f.value ? 'active' : ''}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="error">{error}</div>}

      {loaded && !todos.length && (
        <p className="muted empty-todos">
          {filter === 'done' ? 'Nothing completed yet.' : 'Nothing to do. Add one above, or ask Butler.'}
        </p>
      )}

      {groups.map(([list, items]) => (
        <div key={list} className="todo-group">
          <h2>
            {list} <span className="muted small">{items.filter((t) => !t.done).length} open</span>
          </h2>
          <ul className="todo-list">
            {items.map((todo) => (
              <li key={todo.id} className={`todo ${todo.done ? 'done' : ''}`}>
                <input
                  type="checkbox"
                  checked={todo.done}
                  onChange={() => void toggle(todo)}
                  aria-label={`Mark "${todo.title}" ${todo.done ? 'not done' : 'done'}`}
                />
                <div className="todo-body">
                  <span className="todo-title">
                    {todo.priority === 'high' && <span className="prio high" title="High priority">!</span>}
                    {todo.title}
                  </span>
                  <span className="todo-meta">
                    <span className="muted">#{todo.id}</span>
                    {todo.due_human && (
                      <span className={todo.overdue ? 'overdue' : 'muted'}>
                        {todo.overdue ? 'Overdue · ' : 'Due '}
                        {todo.due_human}
                      </span>
                    )}
                    {todo.priority === 'low' && <span className="muted">Low priority</span>}
                  </span>
                  {todo.notes && <span className="todo-notes muted">{todo.notes}</span>}
                </div>
                <button className="todo-delete" aria-label={`Delete "${todo.title}"`} onClick={() => void remove(todo)}>
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}
