import type { ConfirmActionPayload } from '../types'
import { Markdown } from './Markdown'

interface Props {
  payload: ConfirmActionPayload
  disabled: boolean
  onAnswer: (approved: boolean) => void
}

export function ApprovalCard({ payload, disabled, onAnswer }: Props) {
  // Same rule as butler/agent/human.py show_raw_args(): the tool decides
  // (show_args), otherwise only when there's no readable summary
  const hasArgs = Object.keys(payload.args).length > 0
  const showArgs = hasArgs && (payload.show_args || !payload.details)
  const args = showArgs ? JSON.stringify(payload.args, null, 2) : null

  return (
    <div className="card warning">
      <div className="card-title">⚠️ {payload.question}</div>
      {payload.details &&
        (payload.details_markdown ? (
          <div className="details details-markdown">
            <Markdown text={payload.details} />
          </div>
        ) : (
          <pre className="code details">{payload.details}</pre>
        ))}
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
