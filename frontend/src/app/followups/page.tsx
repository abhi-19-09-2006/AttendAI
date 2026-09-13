'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useFollowUps, useCompleteFollowUp, useStudents } from '@/hooks/useApi'
import type { FollowUpResponse } from '@/types'
import { Badge, FollowUpPriorityBadge, FollowUpStatusBadge } from '@/components/ui/Badge'
import { formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import Link from 'next/link'
import { useState } from 'react'

export default function FollowupsPage() {
  const [filter, setFilter] = useState<'pending' | 'all'>('pending')
  const { data: followUps, isLoading } = useFollowUps(
    filter === 'pending' ? { status: 'pending', limit: 50 } : { limit: 50 }
  )
  const { data: students } = useStudents({ limit: 100 })
  const studentNames = new Map(
    (students ?? []).map((s) => [s.id, `${s.first_name} ${s.last_name}`]),
  )

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Follow-up Tasks</h1>
            <p className="text-gray-500 mt-1">Manual intervention required</p>
          </div>
          <div className="flex bg-gray-100 p-1 rounded-md">
            <button
              onClick={() => setFilter('pending')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                filter === 'pending' ? 'bg-white shadow text-primary-600' : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              Pending Tasks
            </button>
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                filter === 'all' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              All Tasks
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading ? (
            <div className="col-span-full p-8 text-center text-gray-500">Loading tasks...</div>
          ) : !followUps?.length ? (
            <div className="col-span-full p-8 text-center text-gray-500 bg-white rounded-lg border border-gray-200">
              {filter === 'pending' ? 'All caught up! No pending tasks.' : 'No tasks found.'}
            </div>
          ) : (
            followUps.map(task => (
              <FollowUpCard key={task.id} task={task} studentNames={studentNames} />
            ))
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function FollowUpCard({
  task,
  studentNames,
}: {
  task: FollowUpResponse
  studentNames: Map<string, string>
}) {
  const { mutateAsync: completeTask, isPending } = useCompleteFollowUp(task.id)
  const [showForm, setShowForm] = useState(false)
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  const canResolve = task.status !== 'completed' && task.status !== 'cancelled'
  const studentName = studentNames.get(task.student_id) ?? task.student_id.substring(0, 8) + '…'

  const handleResolve = async () => {
    setError('')
    try {
      await completeTask(notes || 'Resolved from dashboard UI')
      setShowForm(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to complete task')
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden flex flex-col">
      <div
        className={`h-1 w-full ${
          task.priority === 'high'
            ? 'bg-red-500'
            : task.priority === 'medium'
              ? 'bg-yellow-400'
              : 'bg-gray-300'
        }`}
      />
      <div className="p-5 flex-1 flex flex-col">
        <div className="flex justify-between items-start mb-3">
          <Badge variant="neutral" className="uppercase">
            {task.type.replace('_', ' ')}
          </Badge>
          <FollowUpStatusBadge status={task.status} />
        </div>
        <h3 className="font-medium text-gray-900 text-base mb-2">
          {task.description}
        </h3>
        <div className="text-sm text-gray-600 mb-2">
          Student:{' '}
          <Link href={`/students/${task.student_id}`} className="text-primary-600 hover:underline">
            {studentName}
          </Link>
        </div>
        <div className="flex items-center gap-2 mt-auto pt-4 text-xs text-gray-500">
          <span>Due: {formatDate(task.due_date)}</span>
          {task.priority && <FollowUpPriorityBadge priority={task.priority} />}
        </div>
      </div>

      {canResolve && (
        <div className="px-5 py-3 border-t border-gray-100 bg-gray-50">
          {showForm ? (
            <div className="space-y-3">
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="How was this resolved? (optional)"
                className="w-full border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 bg-white"
              />
              {error && <p className="text-xs text-red-600">{error}</p>}
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowForm(false)
                    setNotes('')
                    setError('')
                  }}
                  disabled={isPending}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleResolve}
                  disabled={isPending}
                >
                  {isPending ? 'Completing…' : 'Confirm'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setShowForm(true)}>
                Mark Complete
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
