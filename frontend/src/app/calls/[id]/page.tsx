'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import {
  useCall,
  useStudent,
  useAbsenceReports,
  useRetryCall,
} from '@/hooks/useApi'
import {
  Badge,
  CallStatusBadge,
  AbsenceCategoryBadge,
  ConfidenceBadge,
} from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { formatDateTime, formatDuration } from '@/lib/utils'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useState } from 'react'

const RETRYABLE_STATUSES = new Set(['failed', 'no_answer', 'busy', 'invalid_number'])

export default function CallDetailsPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { data: call, isLoading: loadingCall } = useCall(params.id)
  const { data: student } = useStudent(call?.student_id ?? '')
  const { data: reports } = useAbsenceReports({ call_id: params.id, limit: 1 })
  const report = reports?.[0] ?? null

  const canRetry =
    !!call &&
    RETRYABLE_STATUSES.has(call.status) &&
    call.retry_count < call.max_retries

  const { mutateAsync: retryCall, isPending: isRetrying } = useRetryCall(params.id)
  const [retryError, setRetryError] = useState('')

  const handleRetry = async () => {
    setRetryError('')
    try {
      await retryCall()
    } catch (err: any) {
      setRetryError(
        err.response?.data?.detail || 'Failed to start retry — please try again.',
      )
    }
  }

  if (loadingCall)
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="p-8 text-center text-gray-500">Loading call…</div>
        </DashboardLayout>
      </ProtectedRoute>
    )

  if (!call)
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="p-8 text-center bg-white rounded-lg shadow-sm border border-gray-200">
            <h2 className="text-xl font-medium text-gray-900 mb-4">Call not found</h2>
            <Button variant="outline" onClick={() => router.back()}>
              Go back
            </Button>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )

  return (
    <ProtectedRoute>
      <DashboardLayout>
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-gray-900">Call Details</h1>
              <CallStatusBadge status={call.status} />
            </div>
            <p className="text-sm text-gray-500 mt-1 font-mono">{call.id}</p>
          </div>
          <div className="flex items-center gap-3">
            {canRetry && (
              <>
                {retryError && (
                  <span className="text-sm text-red-600 max-w-xs">{retryError}</span>
                )}
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleRetry}
                  disabled={isRetrying}
                >
                  {isRetrying
                    ? 'Starting retry…'
                    : `Retry call (${call.retry_count + 1}/${call.max_retries})`}
                </Button>
              </>
            )}
            <Button variant="outline" size="sm" onClick={() => router.back()}>
              Back
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left column — metadata + report summary */}
          <div className="space-y-6">
            {/* Call info card */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4 border-b border-gray-100 pb-3">
                Call Information
              </h3>
              <dl className="space-y-4 text-sm">
                <Row label="Phone Number" value={call.phone_number_called} mono />
                <Row
                  label="Student"
                  value={
                    student ? (
                      <Link
                        href={`/students/${student.id}`}
                        className="text-primary-600 hover:text-primary-800 font-medium"
                      >
                        {student.first_name} {student.last_name}
                      </Link>
                    ) : (
                      <span className="font-mono text-gray-500">
                        {call.student_id.substring(0, 8)}…
                      </span>
                    )
                  }
                />
                <Row label="Retry Count" value={`${call.retry_count} / ${call.max_retries}`} />

                <div className="border-t border-gray-100 pt-4 mt-4" />

                <Row label="Initiated" value={formatDateTime(call.initiated_at)} />
                <Row label="Answered" value={formatDateTime(call.answered_at)} />
                <Row label="Ended" value={formatDateTime(call.ended_at)} />
                <Row label="Duration" value={formatDuration(call.duration_seconds)} />

                {call.vapi_call_id && (
                  <>
                    <div className="border-t border-gray-100 pt-4 mt-4" />
                    <Row
                      label="Provider Call ID"
                      value={call.vapi_call_id}
                      mono
                    />
                  </>
                )}
              </dl>
            </div>

            {/* Absence report summary (if exists) */}
            {report && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4 border-b border-gray-100 pb-3">
                  <h3 className="text-lg font-medium text-gray-900">Absence Report</h3>
                  <ConfidenceBadge score={report.confidence_score} />
                </div>
                <dl className="space-y-4 text-sm">
                  <Row
                    label="Category"
                    value={<AbsenceCategoryBadge category={report.category} />}
                  />
                  <div>
                    <dt className="text-gray-500 mb-1">Reason</dt>
                    <dd className="bg-gray-50 rounded-md p-3 border border-gray-200 text-gray-900 min-h-[60px] whitespace-pre-wrap">
                      {report.reason || (
                        <span className="text-gray-400 italic">No reason extracted</span>
                      )}
                    </dd>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <Row
                      label="Parent Confirmed"
                      value={
                        report.parent_confirmed ? (
                          <span className="text-green-600 font-medium">Yes</span>
                        ) : (
                          <span className="text-red-500">No</span>
                        )
                      }
                    />
                    <Row
                      label="Follow-up Required"
                      value={
                        report.follow_up_required ? (
                          <span className="text-red-500 font-medium">Yes</span>
                        ) : (
                          <span className="text-green-600">No</span>
                        )
                      }
                    />
                  </div>
                  <div className="flex justify-end pt-2 border-t border-gray-100">
                    <Link href={`/absence-reports/${report.id}`}>
                      <Button variant="outline" size="sm">
                        View full report →
                      </Button>
                    </Link>
                  </div>
                </dl>
              </div>
            )}
          </div>

          {/* Right column — transcript */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-12rem)] min-h-[500px]">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Call Transcript</h3>
                <p className="text-xs text-gray-500 mt-1">
                  {call.initiated_at
                    ? `Started ${formatDateTime(call.initiated_at)}`
                    : 'No call initiated'}
                </p>
              </div>
              <Badge variant="neutral">
                {report ? 'Transcript available' : 'No report yet'}
              </Badge>
            </div>
            <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
              {report?.transcript ? (
                <TranscriptView transcript={report.transcript} />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400 text-sm italic">
                  {call.status === 'completed'
                    ? 'Transcript not available — processing may still be in progress.'
                    : 'Transcript only available after a completed call.'}
                </div>
              )}
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

/* ── Tiny helpers ───────────────────────────────────────────────────────────── */

function Row({
  label,
  value,
  mono,
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-gray-500 shrink-0">{label}</dt>
      <dd className={`text-gray-900 text-right ${mono ? 'font-mono text-xs break-all' : ''}`}>
        {value || '—'}
      </dd>
    </div>
  )
}

/** Splits the raw transcript string into speaker / text lines. */
function TranscriptView({ transcript }: { transcript: string }) {
  return (
    <div className="space-y-4 text-sm leading-relaxed">
      {transcript.split('\n').map((line, i) => {
        const speakerMatch = line.match(/^(Assistant|Parent|Student|Unknown):\s*(.*)$/i)
        if (speakerMatch) {
          const [, speaker, text] = speakerMatch
          const isAssistant = speaker.toLowerCase() === 'assistant'
          return (
            <div key={i} className={`flex gap-3 ${isAssistant ? '' : 'flex-row-reverse'}`}>
              <span
                className={`shrink-0 mt-0.5 inline-flex items-center justify-center h-7 w-7 rounded-full text-xs font-bold ${
                  isAssistant
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-emerald-100 text-emerald-700'
                }`}
              >
                {speaker.charAt(0)}
              </span>
              <div
                className={`rounded-lg px-4 py-2.5 max-w-[85%] whitespace-pre-wrap ${
                  isAssistant
                    ? 'bg-primary-50 text-gray-800 border border-primary-100'
                    : 'bg-emerald-50 text-gray-800 border border-emerald-100'
                }`}
              >
                {text}
              </div>
            </div>
          )
        }
        // Generic / unlabeled line
        return line.trim() ? (
          <p key={i} className="text-gray-600 italic pl-10">
            {line}
          </p>
        ) : null
      })}
    </div>
  )
}
