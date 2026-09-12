'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useCalls } from '@/hooks/useApi'
import { CallStatusBadge } from '@/components/ui/Badge'
import { formatDateTime, formatDuration } from '@/lib/utils'
import { Button } from '@/components/ui/Button'

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
                  calls.map((call) => (
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
                        {/* Action buttons would connect to API to retry logic or view call specifics */}
                        {call.status === 'failed' || call.status === 'no_answer' || call.status === 'busy' ? (
                           <Button variant="outline" size="sm">Retry</Button>
                        ) : null}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
