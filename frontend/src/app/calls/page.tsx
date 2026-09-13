'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useCalls, useRetryCall } from '@/hooks/useApi'
import type { CallResponse } from '@/types'
import { CallStatusBadge } from '@/components/ui/Badge'
import { formatDateTime, formatDuration } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import Link from 'next/link'
import { useState } from 'react'

const RETRYABLE_STATUSES = new Set(['failed', 'no_answer', 'busy', 'invalid_number'])

export default function CallsPage() {
  const { data: calls, isLoading } = useCalls({ limit: 50 })

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Call Log</h1>
            <p className="text-gray-500 mt-1">History of all AI voice communications</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
                  <th className="px-6 py-3">Time</th>
                  <th className="px-6 py-3">Number called</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Duration</th>
                  <th className="px-6 py-3">Retries</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {isLoading ? (
                  <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-500">Loading calls...</td></tr>
                ) : !calls?.length ? (
                  <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-500">No calls found.</td></tr>
                ) : (
                  calls.map((call) => <CallRow key={call.id} call={call} />)
                )}
              </tbody>
            </table>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function CallRow({ call }: { call: CallResponse }) {
  const { mutateAsync: retryCall, isPending: isRetrying } = useRetryCall(call.id)
  const [error, setError] = useState('')

  const canRetry =
    RETRYABLE_STATUSES.has(call.status) && call.retry_count < call.max_retries

  const handleRetry = async () => {
    setError('')
    try {
      await retryCall()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Retry failed')
    }
  }

  return (
    <tr key={call.id} className="hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {formatDateTime(call.created_at)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
        {call.phone_number_called}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <CallStatusBadge status={call.status} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {formatDuration(call.duration_seconds)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {call.retry_count} / {call.max_retries}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
        <div className="flex items-center justify-end gap-2">
          {canRetry && (
            <>
              {error && (
                <span className="text-xs text-red-600 max-w-[140px] truncate" title={error}>
                  {error}
                </span>
              )}
              <Button
                variant="outline"
                size="sm"
                disabled={isRetrying}
                onClick={handleRetry}
              >
                {isRetrying ? 'Retrying…' : `Retry (${call.retry_count}/${call.max_retries})`}
              </Button>
            </>
          )}
          <Link href={`/calls/${call.id}`}>
            <Button variant="ghost" size="sm">
              Details
            </Button>
          </Link>
        </div>
      </td>
    </tr>
  )
}
