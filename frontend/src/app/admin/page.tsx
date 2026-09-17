/**
 * Admin dashboard page with system overview, user management, and campaign management.
 */
'use client'

import { useState } from 'react'
import ProtectedRoute from '@/components/ProtectedRoute'
import { DashboardLayout } from '@/components/DashboardLayout'
import {
  useAdminDashboard,
  useAdminUsers,
  useAdminCampaigns,
  useAdminResetPassword,
  useAdminUpdateCampaignStatus,
} from '@/hooks/useApi'
import { formatDate } from '@/lib/utils'

type Tab = 'dashboard' | 'users' | 'campaigns'

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <TabButton active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')}>
                Dashboard
              </TabButton>
              <TabButton active={activeTab === 'users'} onClick={() => setActiveTab('users')}>
                User Management
              </TabButton>
              <TabButton active={activeTab === 'campaigns'} onClick={() => setActiveTab('campaigns')}>
                Campaign Management
              </TabButton>
            </nav>
          </div>

          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && <DashboardTab />}

          {/* Users Tab */}
          {activeTab === 'users' && <UsersTab />}

          {/* Campaigns Tab */}
          {activeTab === 'campaigns' && <CampaignsTab />}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

// ── Dashboard Tab ──────────────────────────────────────────────────────────

function DashboardTab() {
  const { data: dashboard, isLoading } = useAdminDashboard()

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading dashboard...</p>
      </div>
    )
  }

  if (!dashboard) return null

  return (
    <div className="space-y-6">
      {/* Users Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Users</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard value={dashboard.users.total} label="Total Users" color="blue" />
          <StatCard value={dashboard.users.admins} label="Admins" color="purple" />
          <StatCard value={dashboard.users.faculty} label="Faculty" color="green" />
          <StatCard value={dashboard.users.staff} label="Staff" color="yellow" />
        </div>
      </div>

      {/* Students Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Students</h2>
        <div className="grid grid-cols-2 gap-4">
          <StatCard value={dashboard.students.total} label="Total Students" color="blue" />
          <StatCard value={dashboard.students.active} label="Active" color="green" />
        </div>
      </div>

      {/* Campaigns Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Campaigns</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard value={dashboard.campaigns.total} label="Total" color="blue" />
          <StatCard value={dashboard.campaigns.active} label="Active" color="green" />
          <StatCard value={dashboard.campaigns.paused} label="Paused" color="yellow" />
          <StatCard value={dashboard.campaigns.completed} label="Completed" color="gray" />
        </div>
      </div>

      {/* Calls Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Calls</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard value={dashboard.calls.total} label="Total Calls" color="blue" />
          <StatCard value={dashboard.calls.completed} label="Completed" color="green" />
          <StatCard value={dashboard.calls.failed} label="Failed" color="red" />
          <StatCard value={dashboard.calls.pending} label="Pending" color="yellow" />
        </div>
      </div>

      {/* Jobs Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Background Jobs</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard value={dashboard.jobs.total} label="Total Jobs" color="blue" />
          <StatCard value={dashboard.jobs.queued} label="Queued" color="yellow" />
          <StatCard value={dashboard.jobs.started} label="Started" color="green" />
          <StatCard value={dashboard.jobs.failed} label="Failed" color="red" />
        </div>
      </div>
    </div>
  )
}

// ── Users Tab ──────────────────────────────────────────────────────────────

function UsersTab() {
  const { data: users, isLoading } = useAdminUsers()
  const resetPassword = useAdminResetPassword()

  const handleResetPassword = (userId: string) => {
    const newPassword = prompt('Enter new password (minimum 8 characters):')
    if (newPassword && newPassword.length >= 8) {
      resetPassword.mutate({ userId, newPassword })
    } else if (newPassword) {
      alert('Password must be at least 8 characters')
    }
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading users...</p>
      </div>
    )
  }

  if (!users) return null

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">User Management</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Role
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((user) => (
              <tr key={user.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {user.full_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                  {user.role}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      user.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(user.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleResetPassword(user.id)}
                    className="text-blue-600 hover:text-blue-900"
                    disabled={resetPassword.isPending}
                  >
                    Reset Password
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Campaigns Tab ──────────────────────────────────────────────────────────

function CampaignsTab() {
  const { data: campaigns, isLoading } = useAdminCampaigns()
  const updateStatus = useAdminUpdateCampaignStatus()

  const handleStatusChange = (campaignId: string, newStatus: string) => {
    if (confirm(`Change campaign status to ${newStatus}?`)) {
      updateStatus.mutate({ campaignId, status: newStatus })
    }
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading campaigns...</p>
      </div>
    )
  }

  if (!campaigns) return null

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">Campaign Management</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {campaigns.map((campaign) => (
              <tr key={campaign.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {campaign.name}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                  {campaign.description || '—'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      campaign.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : campaign.status === 'paused'
                        ? 'bg-yellow-100 text-yellow-800'
                        : campaign.status === 'completed'
                        ? 'bg-gray-100 text-gray-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {campaign.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(campaign.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                  {campaign.status === 'draft' && (
                    <>
                      <button
                        onClick={() => handleStatusChange(campaign.id, 'active')}
                        className="text-green-600 hover:text-green-900"
                      >
                        Activate
                      </button>
                      <button
                        onClick={() => handleStatusChange(campaign.id, 'paused')}
                        className="text-yellow-600 hover:text-yellow-900"
                      >
                        Pause
                      </button>
                    </>
                  )}
                  {campaign.status === 'active' && (
                    <>
                      <button
                        onClick={() => handleStatusChange(campaign.id, 'paused')}
                        className="text-yellow-600 hover:text-yellow-900"
                      >
                        Pause
                      </button>
                      <button
                        onClick={() => handleStatusChange(campaign.id, 'completed')}
                        className="text-gray-600 hover:text-gray-900"
                      >
                        Complete
                      </button>
                    </>
                  )}
                  {campaign.status === 'paused' && (
                    <>
                      <button
                        onClick={() => handleStatusChange(campaign.id, 'active')}
                        className="text-green-600 hover:text-green-900"
                      >
                        Resume
                      </button>
                      <button
                        onClick={() => handleStatusChange(campaign.id, 'completed')}
                        className="text-gray-600 hover:text-gray-900"
                      >
                        Complete
                      </button>
                    </>
                  )}
                  {campaign.status === 'completed' && (
                    <span className="text-gray-400">No actions available</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Helper Components ──────────────────────────────────────────────────────

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
          ? 'border-blue-500 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
      }`}
    >
      {children}
    </button>
  )
}

function StatCard({ value, label, color }: { value: number; label: string; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-900',
    green: 'bg-green-50 text-green-900',
    yellow: 'bg-yellow-50 text-yellow-900',
    red: 'bg-red-50 text-red-900',
    purple: 'bg-purple-50 text-purple-900',
    gray: 'bg-gray-50 text-gray-900',
  }

  return (
    <div className={`rounded-lg p-4 ${colorClasses[color] || colorClasses.blue}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm opacity-75">{label}</div>
    </div>
  )
}
