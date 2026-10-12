import type { ConfirmActionPayload } from '../types'

interface Props {
  payload: ConfirmActionPayload
  disabled: boolean
  onAnswer: (approved: boolean) => void
}

export function ApprovalCard({ payload, disabled, onAnswer }: Props) {
  // Same rule as butler/agent/human.py show_raw_args(): calendar and todo
  // approvals have a readable summary; Swiggy's raw args add payment details
  const isSwiggy = /^(food|instamart|dineout)_/.test(payload.tool)
  const showArgs = Object.keys(payload.args).length > 0 && (!payload.details || isSwiggy)
  const args = showArgs ? JSON.stringify(payload.args, null, 2) : null

  return (
    <div className="card warning">
      <div className="card-title">⚠️ {payload.question}</div>
      {payload.details && <pre className="code details">{payload.details}</pre>}
      {args && <pre className="code">{args}</pre>}
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
