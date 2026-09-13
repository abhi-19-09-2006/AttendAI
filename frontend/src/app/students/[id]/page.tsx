'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import {
  useStudent,
  useStudentParents,
  useAttendance,
  useCalls
} from '@/hooks/useApi'
import { Badge, CallStatusBadge, AttendanceBadge } from '@/components/ui/Badge'
import { formatDate, formatDateTime } from '@/lib/utils'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function StudentDetailsPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { data: student, isLoading } = useStudent(params.id)
  const { data: parents } = useStudentParents(params.id)
  const { data: attendanceHistory } = useAttendance({ student_id: params.id, limit: 10 })
  const { data: calls } = useCalls({ student_id: params.id, limit: 5 })

  if (isLoading) return (
    <ProtectedRoute>
      <DashboardLayout><div className="p-8 text-center text-gray-500">Loading student...</div></DashboardLayout>
    </ProtectedRoute>
  )

  if (!student) return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="p-8 text-center bg-white rounded shadow-sm border border-gray-200">
          <h2 className="text-xl font-medium mb-4">Student not found</h2>
          <button className="text-primary-600 underline" onClick={() => router.back()}>Go back</button>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {student.first_name} {student.last_name}
            </h1>
            <p className="text-sm text-gray-500 mt-1 font-mono">{student.student_id}</p>
          </div>
          <div>
            <Badge variant={student.is_active ? 'success' : 'neutral'}>
              {student.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Profile Card */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h3 className="text-lg font-medium text-gray-900 mb-4 border-b pb-2">Profile</h3>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Grade Level</dt>
                  <dd className="font-medium text-gray-900">{student.grade_level}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">DOB</dt>
                  <dd className="font-medium text-gray-900">{formatDate(student.date_of_birth)}</dd>
                </div>
                {student.department && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Department</dt>
                    <dd className="font-medium text-gray-900">{student.department}</dd>
                  </div>
                )}
              </dl>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h3 className="text-lg font-medium text-gray-900 mb-4 border-b pb-2">Contacts</h3>
              {parents && parents.length > 0 ? (
                <ul className="space-y-4">
                  {parents.map((p) => (
                    <li key={p.id} className="text-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-gray-900">{p.first_name} {p.last_name}</span>
                        <span className="text-xs text-gray-500 uppercase tracking-wider">({p.relationship})</span>
                        {p.is_primary_contact && <Badge variant="info" className="scale-75 origin-left">Primary</Badge>}
                      </div>
                      <div className="text-gray-600 font-mono text-xs">{p.primary_phone}</div>
                      {p.email && <div className="text-gray-600 text-xs">{p.email}</div>}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-sm text-gray-500">No contacts recorded.</div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {/* Recent Attendance */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Recent Attendance</h3>
              </div>
              <ul className="divide-y divide-gray-200">
                {!attendanceHistory?.length ? (
                  <li className="p-5 text-gray-500 text-sm text-center">No attendance records found.</li>
                ) : (
                  attendanceHistory.map((record) => (
                    <li key={record.id} className="px-5 py-3 hover:bg-gray-50 flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{formatDate(record.date)}</div>
                        {record.period && <div className="text-xs text-gray-500">Period {record.period}</div>}
                      </div>
                      <AttendanceBadge status={record.status} />
                    </li>
                  ))
                )}
              </ul>
            </div>

            {/* Recent Calls */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Recent Communication</h3>
              </div>
              <ul className="divide-y divide-gray-200">
                {!calls?.length ? (
                  <li className="p-5 text-gray-500 text-sm text-center">No calls recorded.</li>
                ) : (
                  calls.map((call) => (
                    <li key={call.id} className="px-5 py-3 hover:bg-gray-50">
                      <Link href={`/calls/${call.id}`} className="block">
                        <div className="flex items-center justify-between mb-1">
                          <div className="text-sm font-medium text-gray-900">
                            Called: <span className="font-mono text-xs">{call.phone_number_called}</span>
                          </div>
                          <CallStatusBadge status={call.status} />
                        </div>
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>{formatDateTime(call.created_at)}</span>
                          {call.duration_seconds && <span>{call.duration_seconds}s</span>}
                        </div>
                      </Link>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
