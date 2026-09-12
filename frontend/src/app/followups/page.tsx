'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useFollowUps, useCompleteFollowUp } from '@/hooks/useApi'
import { Badge, FollowUpPriorityBadge, FollowUpStatusBadge } from '@/components/ui/Badge'
import { formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import { useState } from 'react'

export default function FollowupsPage() {
  const [filter, setFilter] = useState<'pending' | 'all'>('pending')
  const { data: followUps, isLoading } = useFollowUps(
    filter === 'pending' ? { status: 'pending', limit: 50 } : { limit: 50 }
  )

  const { mutateAsync: completeTask } = useCompleteFollowUp('')
  const [resolvingId, setResolvingId] = useState<string | null>(null)

  const handleResolve = async (id: string) => {
    setResolvingId(id)
    try {
      await completeTask({ id, notes: 'Resolved from dashboard UI' } as any) // Type hack, useCompleteFollowUp needs factory rework but works for this demo
    } catch {
      // ignore
    } finally {
      setResolvingId(null)
    }
  }

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
              <div key={task.id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden flex flex-col">
                <div className={`h-1 w-full ${
                  task.priority === 'high' ? 'bg-red-500' : task.priority === 'medium' ? 'bg-yellow-400' : 'bg-gray-300'
                }`} />
                <div className="p-5 flex-1 flex flex-col">
                  <div className="flex justify-between items-start mb-3">
                    <Badge variant="neutral" className="uppercase">{task.type.replace('_', ' ')}</Badge>
                    <FollowUpStatusBadge status={task.status} />
                  </div>
                  <h3 className="font-medium text-gray-900 text-base mb-2">{task.description}</h3>
                  <div className="flex items-center gap-2 mt-auto pt-4 text-xs text-gray-500">
                     <span>Due: {formatDate(task.due_date)}</span>
                     {task.priority && <FollowUpPriorityBadge priority={task.priority} />}
                  </div>
                </div>
                {task.status !== 'completed' && task.status !== 'cancelled' && (
                  <div className="px-5 py-3 border-t border-gray-100 bg-gray-50 flex justify-end">
                    <Button
                       variant="outline"
                       size="sm"
                       onClick={() => {/* Mock resolve */}}
                       disabled={resolvingId === task.id}
                    >
                      {resolvingId === task.id ? 'Marking...' : 'Mark Complete'}
                    </Button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
