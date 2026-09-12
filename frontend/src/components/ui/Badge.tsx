/**
 * Reusable Badge component.
 */
import { cn } from '@/lib/utils'
import type { CallStatus, AbsenceCategory, FollowUpPriority, FollowUpStatus, AttendanceStatus } from '@/types'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

const variantStyles: Record<Variant, string> = {
  default: 'bg-gray-100 text-gray-700',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-yellow-100 text-yellow-700',
  danger: 'bg-red-100 text-red-700',
  info: 'bg-blue-100 text-blue-700',
  neutral: 'bg-slate-100 text-slate-600',
}

export function Badge({
  children,
  variant = 'default',
  className,
}: {
  children: React.ReactNode
  variant?: Variant
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}

// ─── Domain-specific badge helpers ────────────────────────────────────────────

export function CallStatusBadge({ status }: { status: CallStatus }) {
  const map: Record<CallStatus, { label: string; variant: Variant }> = {
    pending: { label: 'Pending', variant: 'neutral' },
    queued: { label: 'Queued', variant: 'info' },
    calling: { label: 'Calling', variant: 'info' },
    answered: { label: 'Answered', variant: 'success' },
    completed: { label: 'Completed', variant: 'success' },
    no_answer: { label: 'No Answer', variant: 'warning' },
    busy: { label: 'Busy', variant: 'warning' },
    failed: { label: 'Failed', variant: 'danger' },
    invalid_number: { label: 'Invalid Number', variant: 'danger' },
    callback_requested: { label: 'Callback Requested', variant: 'warning' },
    follow_up_required: { label: 'Follow-up Required', variant: 'warning' },
    unreachable: { label: 'Unreachable', variant: 'danger' },
  }
  const cfg = map[status] ?? { label: status, variant: 'default' as Variant }
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>
}

export function AttendanceBadge({ status }: { status: AttendanceStatus }) {
  const map: Record<AttendanceStatus, { label: string; variant: Variant }> = {
    present: { label: 'Present', variant: 'success' },
    absent: { label: 'Absent', variant: 'danger' },
    late: { label: 'Late', variant: 'warning' },
    excused: { label: 'Excused', variant: 'info' },
  }
  const cfg = map[status] ?? { label: status, variant: 'default' as Variant }
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>
}

export function AbsenceCategoryBadge({ category }: { category: AbsenceCategory }) {
  const map: Record<AbsenceCategory, { label: string; variant: Variant }> = {
    medical: { label: 'Medical', variant: 'danger' },
    family: { label: 'Family', variant: 'info' },
    personal: { label: 'Personal', variant: 'neutral' },
    other: { label: 'Other', variant: 'neutral' },
    unknown: { label: 'Unknown', variant: 'warning' },
  }
  const cfg = map[category] ?? { label: category, variant: 'default' as Variant }
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>
}

export function FollowUpPriorityBadge({ priority }: { priority: FollowUpPriority }) {
  const map: Record<FollowUpPriority, { label: string; variant: Variant }> = {
    high: { label: 'High', variant: 'danger' },
    medium: { label: 'Medium', variant: 'warning' },
    low: { label: 'Low', variant: 'neutral' },
  }
  const cfg = map[priority] ?? { label: priority, variant: 'default' as Variant }
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>
}

export function FollowUpStatusBadge({ status }: { status: FollowUpStatus }) {
  const map: Record<FollowUpStatus, { label: string; variant: Variant }> = {
    pending: { label: 'Pending', variant: 'warning' },
    in_progress: { label: 'In Progress', variant: 'info' },
    completed: { label: 'Completed', variant: 'success' },
    cancelled: { label: 'Cancelled', variant: 'neutral' },
  }
  const cfg = map[status] ?? { label: status, variant: 'default' as Variant }
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>
}

export function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const variant: Variant = pct >= 85 ? 'success' : pct >= 70 ? 'warning' : 'danger'
  return <Badge variant={variant}>{pct}%</Badge>
}
