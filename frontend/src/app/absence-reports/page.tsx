'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useAbsenceReports } from '@/hooks/useApi'
import { Badge, AbsenceCategoryBadge, ConfidenceBadge } from '@/components/ui/Badge'
import { formatDate } from '@/lib/utils'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'
import { useState } from 'react'

export default function AbsenceReportsPage() {
  const [filter, setFilter] = useState<'all' | 'needs_review'>('all')
  const { data: reports, isLoading } = useAbsenceReports(
    filter === 'needs_review' ? { requires_review: true, limit: 50 } : { limit: 50 }
  )

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Absence Reports</h1>
            <p className="text-gray-500 mt-1">AI-extracted reasons from parent calls</p>
          </div>
          <div className="flex bg-gray-100 p-1 rounded-md">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                filter === 'all' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              All Reports
            </button>
            <button
              onClick={() => setFilter('needs_review')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                filter === 'needs_review' ? 'bg-white shadow text-primary-600' : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              Needs Review
            </button>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
                  <th className="px-6 py-3">Date / ID</th>
                  <th className="px-6 py-3">Category & Reason</th>
                  <th className="px-6 py-3">Expected Return</th>
                  <th className="px-6 py-3">Confidence</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {isLoading ? (
                  <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-500">Loading reports...</td></tr>
                ) : !reports?.length ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                      {filter === 'needs_review' ? 'No reports currently require review. Great job!' : 'No reports found.'}
                    </td>
                  </tr>
                ) : (
                  reports.map((report) => {
                    const needsReview = !report.reviewed_by && (report.confidence_score < 0.85 || report.follow_up_required)
                    return (
                      <tr key={report.id} className={`hover:bg-gray-50 ${needsReview ? 'bg-yellow-50/30' : ''}`}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{formatDate(report.created_at)}</div>
                          <div className="text-xs text-gray-400 font-mono mt-1">
                             <Link href={`/students/${report.student_id}`} className="hover:underline">Student Profile</Link>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <AbsenceCategoryBadge category={report.category} />
                          <div className="text-sm text-gray-900 mt-2 line-clamp-2 max-w-xs" title={report.reason || ''}>
                            {report.reason || <span className="text-gray-400 italic">No reason extracted</span>}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                           {formatDate(report.expected_return_date)}
                           {report.duration && <div className="text-xs text-gray-400 mt-1">({report.duration})</div>}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <ConfidenceBadge score={report.confidence_score} />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {report.reviewed_by ? (
                            <Badge variant="success">Reviewed</Badge>
                          ) : report.follow_up_required ? (
                            <Badge variant="warning">Requires Follow-up</Badge>
                          ) : report.confidence_score < 0.85 ? (
                            <Badge variant="warning">Review Needed</Badge>
                          ) : (
                            <Badge variant="neutral">Auto-Accepted</Badge>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                          <Link href={`/absence-reports/${report.id}`}>
                            <Button variant={needsReview ? 'primary' : 'outline'} size="sm">
                              {needsReview ? 'Review' : 'View'}
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
