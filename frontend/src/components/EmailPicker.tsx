import type { PickEmailPayload } from '../types'

interface Props {
  payload: PickEmailPayload
  disabled: boolean
  onPick: (emailId: string | null) => void
}

export function EmailPicker({ payload, disabled, onPick }: Props) {
  return (
    <div className="card">
      <div className="card-title">{payload.question}</div>
      <ul className="email-list">
        {payload.emails.map((email) => (
          <li key={email.id}>
            <button className="email-item" disabled={disabled} onClick={() => onPick(email.id)}>
              <span className="email-from">
                {email.unread && <span className="dot" aria-label="unread" />}
                {email.from.replace(/<.*>/, '').trim() || email.from}
              </span>
              <span className="email-subject">{email.subject || '(no subject)'}</span>
              <span className="email-snippet">{email.snippet}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="card-actions">
        <button className="btn ghost" disabled={disabled} onClick={() => onPick(null)}>
          Cancel
        </button>
      </div>
    </div>
  )
}
