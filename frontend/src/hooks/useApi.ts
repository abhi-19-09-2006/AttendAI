/**
 * API query hooks using TanStack Query.
 * Each hook wraps one (or a few related) API endpoints.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api'
import type {
  UserResponse,
  StudentResponse,
  StudentCreate,
  StudentUpdate,
  ParentResponse,
  AttendanceResponse,
  AttendanceCreate,
  AbsenteeResponse,
  CallResponse,
  AbsenceReportResponse,
  AbsenceReportUpdate,
  FollowUpResponse,
  FollowUpCreate,
  FollowUpUpdate,
  CampaignResponse,
  CallStatus,
  AttendanceStatus,
  FollowUpStatus,
  AnalyticsSummary,
  DailyTrend,
  CallMetrics,
  AbsenceReason,
  UnreachableReport,
  FollowUpReport,
} from '@/types'

// ─── Users ────────────────────────────────────────────────────────────────────

export function useCurrentUser() {
  return useQuery({
    queryKey: ['users', 'me'],
    queryFn: () => apiClient.get<UserResponse>('/api/users/me').then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => apiClient.get<UserResponse[]>('/api/users').then((r) => r.data),
  })
}

// ─── Students ─────────────────────────────────────────────────────────────────

export function useStudents(params?: { skip?: number; limit?: number; search?: string }) {
  return useQuery({
    queryKey: ['students', params],
    queryFn: () =>
      apiClient
        .get<StudentResponse[]>('/api/students', { params })
        .then((r) => r.data),
  })
}

export function useStudent(id: string) {
  return useQuery({
    queryKey: ['students', id],
    queryFn: () => apiClient.get<StudentResponse>(`/api/students/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateStudent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: StudentCreate) => apiClient.post<StudentResponse>('/api/students', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['students'] }),
  })
}

export function useUpdateStudent(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: StudentUpdate) =>
      apiClient.put<StudentResponse>(`/api/students/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['students'] })
      qc.invalidateQueries({ queryKey: ['students', id] })
    },
  })
}

// ─── Parents ──────────────────────────────────────────────────────────────────

export function useStudentParents(studentId: string) {
  return useQuery({
    queryKey: ['parents', 'student', studentId],
    queryFn: () =>
      apiClient.get<ParentResponse[]>('/api/parents', { params: { student_id: studentId } }).then((r) => r.data),
    enabled: !!studentId,
  })
}

// ─── Attendance ───────────────────────────────────────────────────────────────

export function useAttendance(params?: {
  skip?: number
  limit?: number
  student_id?: string
  date_from?: string
  date_to?: string
  status?: AttendanceStatus
}) {
  return useQuery({
    queryKey: ['attendance', params],
    queryFn: () => apiClient.get<AttendanceResponse[]>('/api/attendance', { params }).then((r) => r.data),
  })
}

export function useTodaysAbsentees() {
  return useQuery({
    queryKey: ['attendance', 'absentees', 'today'],
    queryFn: () => apiClient.get<AbsenteeResponse[]>('/api/attendance/absentees/today').then((r) => r.data),
    refetchInterval: 60 * 1000, // refresh every minute
  })
}

export function useCreateAttendance() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AttendanceCreate) =>
      apiClient.post<AttendanceResponse>('/api/attendance', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['attendance'] }),
  })
}

export function useUpdateAttendance(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { status?: AttendanceStatus; notes?: string }) =>
      apiClient.put<AttendanceResponse>(`/api/attendance/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['attendance'] }),
  })
}

// ─── Calls ────────────────────────────────────────────────────────────────────

export function useCalls(params?: {
  skip?: number
  limit?: number
  student_id?: string
  campaign_id?: string
  status?: CallStatus
}) {
  return useQuery({
    queryKey: ['calls', params],
    queryFn: () => apiClient.get<CallResponse[]>('/api/calls', { params }).then((r) => r.data),
  })
}

export function useCall(id: string) {
  return useQuery({
    queryKey: ['calls', id],
    queryFn: () => apiClient.get<CallResponse>(`/api/calls/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCampaigns() {
  return useQuery({
    queryKey: ['campaigns'],
    queryFn: () => apiClient.get<CampaignResponse[]>('/api/calls/campaigns').then((r) => r.data),
  })
}

export function useRetryCall(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient.post<CallResponse>(`/api/calls/${id}/retry`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['calls'] })
      qc.invalidateQueries({ queryKey: ['calls', id] })
    },
  })
}

// ─── Absence Reports ──────────────────────────────────────────────────────────

export function useAbsenceReports(params?: {
  skip?: number
  limit?: number
  student_id?: string
  call_id?: string
  min_confidence?: number
  requires_review?: boolean
}) {
  return useQuery({
    queryKey: ['absence-reports', params],
    queryFn: () =>
      apiClient.get<AbsenceReportResponse[]>('/api/absence-reports', { params }).then((r) => r.data),
  })
}

export function useAbsenceReport(id: string) {
  return useQuery({
    queryKey: ['absence-reports', id],
    queryFn: () => apiClient.get<AbsenceReportResponse>(`/api/absence-reports/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useUpdateAbsenceReport(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AbsenceReportUpdate) =>
      apiClient.put<AbsenceReportResponse>(`/api/absence-reports/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['absence-reports'] })
      qc.invalidateQueries({ queryKey: ['absence-reports', id] })
    },
  })
}

export function useReviewAbsenceReport(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (notes: string) =>
      apiClient
        .post<AbsenceReportResponse>(`/api/absence-reports/${id}/review`, null, {
          params: { review_notes: notes },
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['absence-reports'] })
      qc.invalidateQueries({ queryKey: ['absence-reports', id] })
    },
  })
}

// ─── Follow-ups ───────────────────────────────────────────────────────────────

export function useFollowUps(params?: {
  skip?: number
  limit?: number
  student_id?: string
  assigned_to?: string
  status?: FollowUpStatus
  overdue?: boolean
}) {
  return useQuery({
    queryKey: ['followups', params],
    queryFn: () => apiClient.get<FollowUpResponse[]>('/api/followups', { params }).then((r) => r.data),
  })
}

export function useMyFollowUps(statusFilter?: FollowUpStatus) {
  return useQuery({
    queryKey: ['followups', 'my-tasks', statusFilter],
    queryFn: () =>
      apiClient
        .get<FollowUpResponse[]>('/api/followups/my-tasks', { params: statusFilter ? { status: statusFilter } : {} })
        .then((r) => r.data),
  })
}

export function useCreateFollowUp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: FollowUpCreate) =>
      apiClient.post<FollowUpResponse>('/api/followups', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['followups'] }),
  })
}

export function useUpdateFollowUp(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: FollowUpUpdate) =>
      apiClient.put<FollowUpResponse>(`/api/followups/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['followups'] }),
  })
}

export function useCompleteFollowUp(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (notes: string) =>
      apiClient
        .post<FollowUpResponse>(`/api/followups/${id}/complete`, null, {
          params: { resolution_notes: notes },
        })
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['followups'] }),
  })
}

// ─── Analytics ──────────────────────────────────────────────────────────────

export function useAnalyticsSummary(params?: { date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['analytics', 'summary', params],
    queryFn: () =>
      apiClient.get<AnalyticsSummary>('/api/analytics/summary', { params }).then((r) => r.data),
  })
}

export function useAnalyticsTrends(params?: { date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['analytics', 'trends', params],
    queryFn: () =>
      apiClient.get<DailyTrend[]>('/api/analytics/trends', { params }).then((r) => r.data),
  })
}

export function useCallMetrics(params?: { date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['analytics', 'call-metrics', params],
    queryFn: () =>
      apiClient.get<CallMetrics>('/api/analytics/call-metrics', { params }).then((r) => r.data),
  })
}

export function useAbsenceReasons(params?: { date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['analytics', 'absence-reasons', params],
    queryFn: () =>
      apiClient.get<AbsenceReason[]>('/api/analytics/absence-reasons', { params }).then((r) => r.data),
  })
}

export function useDailyReport(reportDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'reports', 'daily', reportDate],
    queryFn: () =>
      apiClient.get('/api/analytics/reports/daily', { params: { report_date: reportDate } }).then((r) => r.data),
    enabled: !!reportDate,
  })
}

export function useWeeklyReport(endDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'reports', 'weekly', endDate],
    queryFn: () =>
      apiClient.get('/api/analytics/reports/weekly', { params: { end_date: endDate } }).then((r) => r.data),
    enabled: !!endDate,
  })
}

export function useMonthlyReport(params?: { year?: number; month?: number }) {
  return useQuery({
    queryKey: ['analytics', 'reports', 'monthly', params],
    queryFn: () =>
      apiClient.get('/api/analytics/reports/monthly', { params }).then((r) => r.data),
  })
}

export function useFollowUpReport(params?: { date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['analytics', 'reports', 'followup', params],
    queryFn: () =>
      apiClient.get<FollowUpReport>('/api/analytics/reports/followup', { params }).then((r) => r.data),
  })
}

export function useUnreachableReport(params?: { date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['analytics', 'reports', 'unreachable', params],
    queryFn: () =>
      apiClient.get<UnreachableReport>('/api/analytics/reports/unreachable', { params }).then((r) => r.data),
  })
}
