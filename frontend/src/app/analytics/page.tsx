'use client'

import { useState } from 'react'
import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import {
  useAnalyticsSummary,
  useAnalyticsTrends,
  useCallMetrics,
  useAbsenceReasons,
  useFollowUpReport,
  useUnreachableReport,
} from '@/hooks/useApi'
import { formatDate } from '@/lib/utils'
import { format, subDays } from 'date-fns'

type ReportTab = 'overview' | 'calls' | 'reasons' | 'followups' | 'unreachable'

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<ReportTab>('overview')
  const [dateFrom, setDateFrom] = useState(format(subDays(new Date(), 29), 'yyyy-MM-dd'))
  const [dateTo, setDateTo] = useState(format(new Date(), 'yyyy-MM-dd'))

  const { data: summary, isLoading: loadingSummary } = useAnalyticsSummary({
    date_from: dateFrom,
    date_to: dateTo,
  })
  const { data: trends } = useAnalyticsTrends({ date_from: dateFrom, date_to: dateTo })
  const { data: callMetrics } = useCallMetrics({ date_from: dateFrom, date_to: dateTo })
  const { data: reasons } = useAbsenceReasons({ date_from: dateFrom, date_to: dateTo })
  const { data: followupReport } = useFollowUpReport({ date_from: dateFrom, date_to: dateTo })
  const { data: unreachableReport } = useUnreachableReport({ date_from: dateFrom, date_to: dateTo })

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Analytics & Reports</h1>
          <p className="text-gray-500 mt-1">Attendance and call metrics overview.</p>
        </div>

        {/* Date Range Selector */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Date Range:</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            />
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
              Overview
            </TabButton>
            <TabButton active={activeTab === 'calls'} onClick={() => setActiveTab('calls')}>
              Call Metrics
            </TabButton>
            <TabButton active={activeTab === 'reasons'} onClick={() => setActiveTab('reasons')}>
              Absence Reasons
            </TabButton>
            <TabButton active={activeTab === 'followups'} onClick={() => setActiveTab('followups')}>
              Follow-ups
            </TabButton>
            <TabButton active={activeTab === 'unreachable'} onClick={() => setActiveTab('unreachable')}>
              Unreachable
            </TabButton>
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && summary && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <StatCard title="Total Absences" value={summary.total_absentees} />
              <StatCard title="Total Calls" value={summary.total_calls} />
              <StatCard title="Completed" value={summary.completed_calls} className="border-l-4 border-green-500" />
              <StatCard title="No Answer" value={summary.no_answer_calls} className="border-l-4 border-yellow-500" />
              <StatCard title="Failed" value={summary.failed_calls} className="border-l-4 border-red-500" />
              <StatCard title="Unreachable" value={summary.unreachable_calls} className="border-l-4 border-red-600" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Rates</h3>
                <div className="space-y-3">
                  <MetricRow label="Answer Rate" value={`${summary.answer_rate}%`} />
                  <MetricRow label="No Answer Rate" value={`${summary.no_answer_rate}%`} />
                  <MetricRow label="Failure Rate" value={`${summary.failure_rate}%`} />
                  <MetricRow
                    label="Avg Duration"
                    value={summary.average_duration_seconds ? `${summary.average_duration_seconds}s` : '—'}
                  />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Follow-ups</h3>
                <div className="space-y-3">
                  <MetricRow label="Total" value={summary.total_followups} />
                  <MetricRow label="Pending" value={summary.pending_followups} />
                  <MetricRow label="Completed" value={summary.completed_followups} />
                </div>
              </div>
            </div>

            {trends && trends.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Daily Trends</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Absences
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Calls
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Completed
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {trends.map((t) => (
                        <tr key={t.date}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatDate(t.date)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.absentees}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.calls}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.completed_calls}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'calls' && callMetrics && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard title="Total Calls" value={callMetrics.total_calls} />
              <StatCard title="Answer Rate" value={`${callMetrics.answer_rate}%`} className="border-l-4 border-green-500" />
              <StatCard title="Completion Rate" value={`${callMetrics.completion_rate}%`} className="border-l-4 border-blue-500" />
              <StatCard title="Retry Rate" value={`${callMetrics.retry_rate}%`} className="border-l-4 border-yellow-500" />
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Status Distribution</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {Object.entries(callMetrics.status_distribution).map(([status, count]) => (
                  <div key={status} className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-500 capitalize">{status.replace('_', ' ')}</div>
                    <div className="text-2xl font-semibold text-gray-900">{count}</div>
                  </div>
                ))}
              </div>
            </div>

            {callMetrics.average_duration_seconds && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Average Call Duration</h3>
                <div className="text-3xl font-bold text-gray-900">
                  {callMetrics.average_duration_seconds}s
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'reasons' && reasons && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Absence Reason Distribution</h3>
            {reasons.length > 0 ? (
              <div className="space-y-3">
                {reasons.map((r) => {
                  const total = reasons.reduce((sum, item) => sum + item.count, 0)
                  const pct = total > 0 ? (r.count / total) * 100 : 0
                  return (
                    <div key={r.category}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-gray-700 capitalize">{r.category}</span>
                        <span className="text-gray-500">
                          {r.count} ({pct.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-gray-500">No absence reports in this date range.</p>
            )}
          </div>
        )}

        {activeTab === 'followups' && followupReport && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Follow-up Summary</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">{followupReport.total} Total</div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">By Type</h4>
                  <div className="space-y-1">
                    {Object.entries(followupReport.by_type).map(([type, count]) => (
                      <div key={type} className="flex justify-between text-sm">
                        <span className="text-gray-600 capitalize">{type.replace('_', ' ')}</span>
                        <span className="font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">By Priority</h4>
                  <div className="space-y-1">
                    {Object.entries(followupReport.by_priority).map(([priority, count]) => (
                      <div key={priority} className="flex justify-between text-sm">
                        <span className="text-gray-600 capitalize">{priority}</span>
                        <span className="font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">By Status</h4>
                  <div className="space-y-1">
                    {Object.entries(followupReport.by_status).map(([status, count]) => (
                      <div key={status} className="flex justify-between text-sm">
                        <span className="text-gray-600 capitalize">{status.replace('_', ' ')}</span>
                        <span className="font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'unreachable' && unreachableReport && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Unreachable Parents ({unreachableReport.total})
            </h3>
            {unreachableReport.entries.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Call ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Phone Number
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Retries
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Last Updated
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {unreachableReport.entries.map((entry) => (
                      <tr key={entry.call_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                          {entry.call_id.slice(0, 8)}...
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {entry.phone_number}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {entry.retry_count}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {entry.last_updated ? formatDate(entry.last_updated) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500">No unreachable parents in this date range.</p>
            )}
          </div>
        )}

        {loadingSummary && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-500">Loading analytics...</p>
          </div>
        )}
      </DashboardLayout>
    </ProtectedRoute>
  )
}

// ── Helper Components ────────────────────────────────────────────────────────

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
        active
          ? 'border-primary-500 text-primary-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
      }`}
    >
      {children}
    </button>
  )
}

function StatCard({
  title,
  value,
  className = '',
}: {
  title: string
  value: number | string
  className?: string
}) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-semibold text-gray-900 mt-1">{value}</div>
    </div>
  )
}

function MetricRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  )
}
