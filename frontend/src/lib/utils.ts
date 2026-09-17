/**
 * Shared utility functions.
 */
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, parseISO, isValid } from 'date-fns'

/**
 * Merge Tailwind CSS classes with conflict resolution.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/**
 * Format an ISO date string as a human-readable date.
 * Returns "—" for null/undefined/invalid inputs.
 */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  try {
    const date = parseISO(value)
    if (!isValid(date)) return '—'
    return format(date, 'MMM d, yyyy')
  } catch {
    return '—'
  }
}

/**
 * Format an ISO datetime string as a human-readable date + time.
 * Returns "—" for null/undefined/invalid inputs.
 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  try {
    const date = parseISO(value)
    if (!isValid(date)) return '—'
    return format(date, 'MMM d, yyyy h:mm a')
  } catch {
    return '—'
  }
}

/**
 * Format a duration in seconds as a human-readable string.
 * e.g. 90 → "1m 30s", 3661 → "1h 1m 1s"
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return '—'
  if (seconds === 0) return '0s'

  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60

  const parts: string[] = []
  if (h > 0) parts.push(`${h}h`)
  if (m > 0) parts.push(`${m}m`)
  if (s > 0 || parts.length === 0) parts.push(`${s}s`)

  return parts.join(' ')
}
