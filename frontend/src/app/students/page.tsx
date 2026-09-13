'use client'

import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useStudents, useCreateStudent } from '@/hooks/useApi'
import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'

export default function StudentsPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [showAdd, setShowAdd] = useState(false)
  const limit = 20

  const { data: students, isLoading } = useStudents({ skip: page * limit, limit, search })

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Students</h1>
            <p className="text-gray-500 mt-1">Manage student directory</p>
          </div>
          <Button variant="primary" onClick={() => setShowAdd(true)}>
            Add Student
          </Button>
        </div>

        {showAdd && <AddStudentModal onClose={() => setShowAdd(false)} />}

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(0)
              }}
              className="w-full max-w-sm px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
                  <th className="px-6 py-3">Student ID</th>
                  <th className="px-6 py-3">Name</th>
                  <th className="px-6 py-3">Grade Level</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {isLoading ? (
                  <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">Loading...</td></tr>
                ) : !students?.length ? (
                  <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">No students found.</td></tr>
                ) : (
                  students.map((student) => (
                    <tr key={student.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">
                        {student.student_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {student.last_name}, {student.first_name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {student.grade_level}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <Link href={`/students/${student.id}`} className="text-primary-600 hover:text-primary-900">
                          View details
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
            <span className="text-sm text-gray-700">
              Showing page {page + 1}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => p + 1)}
                disabled={!students || students.length < limit}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function AddStudentModal({ onClose }: { onClose: () => void }) {
  const { mutateAsync: createStudent, isPending } = useCreateStudent()
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    student_id: '',
    first_name: '',
    last_name: '',
    date_of_birth: '',
    grade_level: '',
    department: '',
  })

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!form.student_id || !form.first_name || !form.last_name || !form.date_of_birth || !form.grade_level) {
      setError('Please fill in all required fields.')
      return
    }

    try {
      await createStudent({
        student_id: form.student_id.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        date_of_birth: form.date_of_birth,
        grade_level: Number(form.grade_level),
        department: form.department.trim() || undefined,
      })
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create student')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg shadow-xl border border-gray-200 w-full max-w-md">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">Add Student</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Student ID" required>
              <input
                type="text"
                value={form.student_id}
                onChange={set('student_id')}
                placeholder="e.g. 2026-001"
                className={inputCls}
              />
            </Field>
            <Field label="Grade Level" required>
              <input
                type="number"
                min={1}
                value={form.grade_level}
                onChange={set('grade_level')}
                placeholder="e.g. 12"
                className={inputCls}
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="First Name" required>
              <input
                type="text"
                value={form.first_name}
                onChange={set('first_name')}
                className={inputCls}
              />
            </Field>
            <Field label="Last Name" required>
              <input
                type="text"
                value={form.last_name}
                onChange={set('last_name')}
                className={inputCls}
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Date of Birth" required>
              <input
                type="date"
                value={form.date_of_birth}
                onChange={set('date_of_birth')}
                className={inputCls}
              />
            </Field>
            <Field label="Department">
              <input
                type="text"
                value={form.department}
                onChange={set('department')}
                placeholder="e.g. Computer Science"
                className={inputCls}
              />
            </Field>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving…' : 'Add Student'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

const inputCls =
  'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm text-gray-900 bg-white'

function Field({
  label,
  children,
  required,
}: {
  label: string
  children: React.ReactNode
  required?: boolean
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </span>
      <span className="mt-1 block">{children}</span>
    </label>
  )
}
