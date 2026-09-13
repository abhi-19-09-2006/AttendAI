'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useAttendance, useStudents } from '@/hooks/useApi'
import { AttendanceBadge } from '@/components/ui/Badge'
import { formatDate } from '@/lib/utils'
import Link from 'next/link'
import { useState } from 'react'

export default function AttendancePage() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const { data: records, isLoading } = useAttendance({ date_from: date, date_to: date, limit: 100 })
  const { data: students } = useStudents({ limit: 100 })
  const studentNames = new Map(
    (students ?? []).map((s) => [s.id, `${s.last_name}, ${s.first_name}`]),
  )

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Attendance</h1>
            <p className="text-gray-500 mt-1">Daily records view</p>
          </div>
          <div>
             <input
               type="date"
               value={date}
               onChange={(e) => setDate(e.target.value)}
               className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm text-gray-900 bg-white"
             />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
                  <th className="px-6 py-3">Student</th>
                  <th className="px-6 py-3">Period</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Recorded At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {isLoading ? (
                   <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">Loading records...</td></tr>
                ) : !records?.length ? (
                   <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">No attendance recorded on this date.</td></tr>
                ) : (
                  records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                       <td className="px-6 py-4 whitespace-nowrap text-sm">
                         <Link
                           href={`/students/${record.student_id}`}
                           className="font-medium text-gray-900 hover:text-primary-600"
                         >
                           {studentNames.get(record.student_id) ?? record.student_id.substring(0, 8) + '…'}
                         </Link>
                       </td>
                       <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                         {record.period || 'Full Day'}
                       </td>
                       <td className="px-6 py-4 whitespace-nowrap">
                         <AttendanceBadge status={record.status} />
                       </td>
                       <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 border-l border-transparent">
                          {formatDate(record.created_at)}
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
