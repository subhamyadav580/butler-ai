import { useState, type FormEvent, type KeyboardEvent } from 'react'

interface Props {
  disabled: boolean
  onSend: (text: string) => void
}

export function Composer({ disabled, onSend }: Props) {
  const [text, setText] = useState('')

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    const message = text.trim()
    if (!message || disabled) return
    onSend(message)
    setText('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) submit(event)
  }

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask about your mail, order food, or anything else…"
        rows={1}
        aria-label="Message"
      />
      <button className="btn primary" type="submit" disabled={disabled || !text.trim()}>
        Send
      </button>
    </form>
  )
}
