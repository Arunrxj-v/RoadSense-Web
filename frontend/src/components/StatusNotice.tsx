import { Icon } from './Icon'

interface StatusNoticeProps {
  title: string
  message?: string
  tone?: 'neutral' | 'error'
  actionLabel?: string
  onAction?: () => void
}

export function StatusNotice({
  title,
  message,
  tone = 'neutral',
  actionLabel,
  onAction,
}: StatusNoticeProps) {
  return (
    <div className={`status-banner${tone === 'error' ? ' status-banner--error' : ''}`} role={tone === 'error' ? 'alert' : undefined}>
      <Icon name={tone === 'error' ? 'error' : 'info'} size={16} />
      <span>
        <strong>{title}</strong>
        {message ? ` ${message}` : ''}
      </span>
      {actionLabel && onAction ? (
        <button type="button" className="inline-link inline-link--primary" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
}
