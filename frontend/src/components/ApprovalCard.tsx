import type { ConfirmActionPayload } from '../types'

interface Props {
  payload: ConfirmActionPayload
  disabled: boolean
  onAnswer: (approved: boolean) => void
}

export function ApprovalCard({ payload, disabled, onAnswer }: Props) {
  const args = Object.keys(payload.args).length ? JSON.stringify(payload.args, null, 2) : null

  return (
    <div className="card warning">
      <div className="card-title">⚠️ {payload.question}</div>
      {args && <pre className="code">{args}</pre>}
      {payload.details && <pre className="code details">{payload.details}</pre>}
      <div className="card-actions">
        <button className="btn ghost" disabled={disabled} onClick={() => onAnswer(false)}>
          Reject
        </button>
        <button className="btn primary" disabled={disabled} onClick={() => onAnswer(true)}>
          Approve
        </button>
      </div>
    </div>
  )
}
