'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import {
  useTodaysAbsentees,
  useCalls,
  useFollowUps,
  useAbsenceReports,
} from '@/hooks/useApi'
import { CallStatusBadge, ConfidenceBadge } from '@/components/ui/Badge'
import Link from 'next/link'

export default function DashboardPage() {
  const { data: absentees, isLoading: loadingAbs } = useTodaysAbsentees()

  // Basic stats counts (in a larger app we'd have a specific backend dashboard endpoint)
  const { data: calls } = useCalls({ limit: 100 })
  const completedCalls = calls?.filter(c => c.status === 'completed').length ?? 0
  const noAnswerCalls = calls?.filter(c => c.status === 'no_answer').length ?? 0
  const failedCalls = calls?.filter(c => c.status === 'failed' || c.status === 'invalid_number').length ?? 0

  const { data: followUps } = useFollowUps({ status: 'pending', limit: 100 })
  const pendingFollowUps = followUps?.length ?? 0

  const { data: reports } = useAbsenceReports({ requires_review: true, limit: 10 })

  // Calculate summary metrics
  const todayCount = absentees?.length ?? 0
  const uncalledCount = absentees?.filter(a => !a.has_call).length ?? 0

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Overview of today&apos;s attendance communication.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          <StatCard title="Today's Absences" value={todayCount} />
          <StatCard title="Needs Calling" value={uncalledCount} className="border-l-4 border-yellow-500" />
          <StatCard title="Calls Completed" value={completedCalls} className="border-l-4 border-green-500" />
          <StatCard title="No Answer" value={noAnswerCalls} />
          <StatCard title="Failed Calls" value={failedCalls} className="border-l-4 border-red-500" />
          <StatCard title="Pending Follow-ups" value={pendingFollowUps} className="border-l-4 border-purple-500" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Today's Absentees */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-lg font-medium text-gray-900">Today&apos;s Absentees</h2>
              <Link href="/attendance" className="text-sm font-medium text-primary-600 hover:text-primary-700">
                View all &rarr;
              </Link>
            </div>
            <div className="p-0">
              {loadingAbs ? (
                <div className="p-6 text-center text-gray-500">Loading...</div>
              ) : absentees && absentees.length > 0 ? (
                <ul className="divide-y divide-gray-200">
                  {absentees.slice(0, 5).map((a) => (
                    <li key={a.attendance_id} className="p-4 hover:bg-gray-50 flex items-center justify-between">
                      <div>
                        <div className="font-medium text-gray-900">{a.student_name}</div>
                        <div className="text-sm text-gray-500 font-mono">Grade {a.grade_level}</div>
                      </div>
                      <div>
                        {a.has_call && a.call_status ? (
                          <CallStatusBadge status={a.call_status} />
                        ) : (
                          <span className="text-sm text-gray-400">Not called yet</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="p-6 text-center text-gray-500">No absentees recorded today.</div>
              )}
            </div>
          </div>

          {/* Pending Reviews */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-lg font-medium text-gray-900">Require Review</h2>
              <Link href="/absence-reports" className="text-sm font-medium text-primary-600 hover:text-primary-700">
                View all &rarr;
              </Link>
            </div>
            <div className="p-0">
              {reports && reports.length > 0 ? (
                <ul className="divide-y divide-gray-200">
                  {reports.map((report) => (
                    <li key={report.id} className="p-4 hover:bg-gray-50 flex justify-between">
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900 truncate max-w-[200px] mb-1">
                          {report.reason || 'No reason provided'}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">
                          {report.id.substring(0, 8)}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <ConfidenceBadge score={report.confidence_score} />
                        <Link href={`/absence-reports/${report.id}`} className="text-xs font-medium text-primary-600">
                          Review
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="p-6 text-center text-gray-500 bg-gray-50/50">
                  <span className="inline-block h-8 w-8 rounded-full bg-green-100 text-green-600 text-lg leading-8 text-center mb-2">✓</span>
                  <p>All reports reviewed!</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function StatCard({ title, value, className = '' }: { title: string; value: number | string; className?: string }) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      <dt className="text-xs font-medium text-gray-500 uppercase truncate mb-1">{title}</dt>
      <dd className="text-2xl font-semibold text-gray-900">{value}</dd>
    </div>
  )
}
