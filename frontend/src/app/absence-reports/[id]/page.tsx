'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useAbsenceReport, useReviewAbsenceReport, useUpdateAbsenceReport } from '@/hooks/useApi'
import { Badge, AbsenceCategoryBadge, ConfidenceBadge } from '@/components/ui/Badge'
import { formatDate, formatDateTime } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function AbsenceReportDetailsPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { data: report, isLoading } = useAbsenceReport(params.id)
  const { mutateAsync: reviewReport, isPending: isReviewing } = useReviewAbsenceReport(params.id)
  const { mutateAsync: updateReport, isPending: isUpdating } = useUpdateAbsenceReport(params.id)

  const [notes, setNotes] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [editReason, setEditReason] = useState('')

  if (isLoading) return (
    <ProtectedRoute>
      <DashboardLayout><div className="p-8 text-center text-gray-500">Loading report...</div></DashboardLayout>
    </ProtectedRoute>
  )

  if (!report) return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="p-8 text-center bg-white rounded shadow-sm border border-gray-200">
          <h2 className="text-xl font-medium mb-4">Report not found</h2>
          <Button variant="outline" onClick={() => router.back()}>Go back</Button>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )

  const handleReview = async () => {
    try {
      await reviewReport(notes)
      router.push('/absence-reports')
    } catch (e) {
      console.error(e)
    }
  }

  const handleSaveEdit = async () => {
    try {
      await updateReport({ reason: editReason })
      setIsEditing(false)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">Absence Report</h1>
              {report.reviewed_by ? <Badge variant="success">Reviewed</Badge> : <Badge variant="warning">Pending Review</Badge>}
            </div>
            <p className="text-sm text-gray-500 mt-1 font-mono">{report.id}</p>
          </div>
          <Button variant="outline" onClick={() => router.back()}>Back to List</Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
                <h3 className="text-lg font-medium text-gray-900">Extracted Information</h3>
                <ConfidenceBadge score={report.confidence_score} />
              </div>

              <dl className="space-y-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Category</dt>
                  <dd className="mt-1"><AbsenceCategoryBadge category={report.category} /></dd>
                </div>

                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1 flex justify-between">
                    <span>Reason</span>
                    {!isEditing && <button onClick={() => { setIsEditing(true); setEditReason(report.reason || ''); }} className="text-primary-600 hover:underline">Edit</button>}
                  </dt>
                  <dd className="mt-1 bg-gray-50 rounded-md p-3 text-sm text-gray-900 border border-gray-200 min-h-[80px]">
                    {isEditing ? (
                      <div className="space-y-2">
                        <textarea
                          className="w-full border-gray-300 rounded focus:ring-primary-500 focus:border-primary-500 p-2 text-sm bg-white"
                          rows={3}
                          value={editReason}
                          onChange={e => setEditReason(e.target.value)}
                        />
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="ghost" onClick={() => setIsEditing(false)}>Cancel</Button>
                          <Button size="sm" variant="primary" onClick={handleSaveEdit} disabled={isUpdating}>Save</Button>
                        </div>
                      </div>
                    ) : (
                      report.reason || <span className="text-gray-400 italic">No reason extracted</span>
                    )}
                  </dd>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Expected Return</dt>
                    <dd className="mt-1 text-sm text-gray-900">{formatDate(report.expected_return_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Duration</dt>
                    <dd className="mt-1 text-sm text-gray-900">{report.duration || '—'}</dd>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Parent Confirmed</dt>
                    <dd className="mt-1 text-sm">
                      {report.parent_confirmed ? <span className="text-green-600 font-medium">Yes</span> : <span className="text-red-500">No / Unclear</span>}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Requires Follow-up</dt>
                    <dd className="mt-1 text-sm">
                      {report.follow_up_required ? <span className="text-red-500 font-medium">Yes</span> : <span className="text-green-600">No</span>}
                    </dd>
                  </div>
                </div>
              </dl>
            </div>

            {!report.reviewed_by && (
              <div className="bg-yellow-50 rounded-lg shadow-sm border border-yellow-200 p-6">
                <h3 className="text-lg font-medium text-yellow-800 mb-2">Faculty Review Needed</h3>
                <p className="text-sm text-yellow-700 mb-4">
                  Please review the transcript and AI extraction. Approve if correct, or edit above.
                </p>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="notes" className="block text-sm font-medium text-yellow-800 mb-1">Review Notes (Optional)</label>
                    <textarea
                      id="notes"
                      rows={3}
                      className="shadow-sm block w-full focus:ring-yellow-500 focus:border-yellow-500 sm:text-sm border border-yellow-300 rounded-md"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Add any internal notes..."
                    />
                  </div>
                  <Button variant="primary" onClick={handleReview} disabled={isReviewing} className="w-full bg-yellow-600 hover:bg-yellow-700">
                    {isReviewing ? 'Marking as Reviewed...' : 'Approve & Mark Reviewed'}
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-12rem)] min-h-[500px]">
             <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Call Transcript</h3>
                <p className="text-xs text-gray-500 mt-1">From call {formatDateTime(report.created_at)}</p>
             </div>
             <div className="flex-1 p-6 overflow-y-auto bg-gray-50 relative">
                {report.transcript ? (
                  <div className="whitespace-pre-wrap text-sm text-gray-700 font-serif leading-relaxed">
                    {report.transcript}
                  </div>
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm italic">
                    No transcript available for this call.
                  </div>
                )}
             </div>
          </div>

        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
