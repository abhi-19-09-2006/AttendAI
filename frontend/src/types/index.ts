/**
 * TypeScript types mirroring the FastAPI Pydantic schemas.
 */

// ─── Enums ────────────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'faculty' | 'staff'

export type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused'

export type CallStatus =
  | 'pending'
  | 'queued'
  | 'calling'
  | 'answered'
  | 'completed'
  | 'no_answer'
  | 'busy'
  | 'failed'
  | 'invalid_number'
  | 'callback_requested'
  | 'follow_up_required'
  | 'unreachable'

export type CampaignStatus = 'draft' | 'active' | 'paused' | 'completed'

export type AbsenceCategory = 'medical' | 'family' | 'personal' | 'other' | 'unknown'

export type FollowUpType = 'callback_requested' | 'low_confidence' | 'medical_verification' | 'other'

export type FollowUpPriority = 'low' | 'medium' | 'high'

export type FollowUpStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'

export type ParentRelationship = 'mother' | 'father' | 'guardian' | 'stepmother' | 'stepfather' | 'grandparent' | 'other'

export type ContactMethod = 'phone' | 'email' | 'sms'

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

// ─── User ─────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string
  email: string
  full_name: string
  role: UserRole
  department: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

// ─── Student ──────────────────────────────────────────────────────────────────

export interface StudentResponse {
  id: string
  student_id: string
  first_name: string
  last_name: string
  date_of_birth: string
  grade_level: number
  department: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StudentCreate {
  student_id: string
  first_name: string
  last_name: string
  date_of_birth: string
  grade_level: number
  department?: string
}

export interface StudentUpdate {
  first_name?: string
  last_name?: string
  grade_level?: number
  department?: string
  is_active?: boolean
}

// ─── Parent ───────────────────────────────────────────────────────────────────

export interface ParentResponse {
  id: string
  student_id: string
  relationship: ParentRelationship
  first_name: string
  last_name: string
  primary_phone: string
  secondary_phone: string | null
  email: string | null
  preferred_contact_method: ContactMethod
  preferred_language: string
  is_primary_contact: boolean
  created_at: string
  updated_at: string
}

// ─── Attendance ───────────────────────────────────────────────────────────────

export interface AttendanceResponse {
  id: string
  student_id: string
  date: string
  status: AttendanceStatus
  period: string | null
  notes: string | null
  recorded_by: string
  created_at: string
  updated_at: string
}

export interface AttendanceCreate {
  student_id: string
  date: string
  status: AttendanceStatus
  period?: string
  notes?: string
}

export interface AbsenteeResponse {
  attendance_id: string
  student_id: string
  student_name: string
  grade_level: number
  date: string
  status: AttendanceStatus
  has_call: boolean
  call_status: CallStatus | null
}

// ─── Call Campaign ────────────────────────────────────────────────────────────

export interface CampaignResponse {
  id: string
  name: string
  description: string | null
  scheduled_start: string | null
  status: CampaignStatus
  created_by: string
  created_at: string
  updated_at: string
}

// ─── Call ─────────────────────────────────────────────────────────────────────

export interface CallResponse {
  id: string
  student_id: string
  parent_id: string
  attendance_id: string
  campaign_id: string | null
  status: CallStatus
  phone_number_called: string
  vapi_call_id: string | null
  scheduled_time: string | null
  initiated_at: string | null
  answered_at: string | null
  ended_at: string | null
  duration_seconds: number | null
  retry_count: number
  max_retries: number
  created_at: string
  updated_at: string
}

// ─── Absence Report ───────────────────────────────────────────────────────────

export interface AbsenceReportResponse {
  id: string
  call_id: string
  student_id: string
  attendance_id: string
  reason: string | null
  category: AbsenceCategory
  duration: string | null
  expected_return_date: string | null
  parent_confirmed: boolean
  follow_up_required: boolean
  confidence_score: number
  transcript: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  created_at: string
  updated_at: string
}

export interface AbsenceReportUpdate {
  reason?: string
  category?: AbsenceCategory
  duration?: string
  expected_return_date?: string
  parent_confirmed?: boolean
  follow_up_required?: boolean
  review_notes?: string
}

// ─── Follow-up ────────────────────────────────────────────────────────────────

export interface FollowUpResponse {
  id: string
  student_id: string
  absence_report_id: string | null
  call_id: string | null
  type: FollowUpType
  priority: FollowUpPriority
  description: string
  due_date: string | null
  assigned_to: string | null
  status: FollowUpStatus
  resolution_notes: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface FollowUpCreate {
  student_id: string
  type: FollowUpType
  priority?: FollowUpPriority
  description: string
  due_date?: string
  absence_report_id?: string
  call_id?: string
  assigned_to?: string
}

export interface FollowUpUpdate {
  status?: FollowUpStatus
  priority?: FollowUpPriority
  due_date?: string
  assigned_to?: string
  description?: string
  resolution_notes?: string
}

// ─── Dashboard summary (assembled on the frontend) ───────────────────────────

export interface DashboardStats {
  todayAbsentees: number
  completedCalls: number
  noAnswerCalls: number
  failedCalls: number
  pendingFollowUps: number
  lowConfidenceReports: number
}

// ─── Analytics ──────────────────────────────────────────────────────────────

export interface AnalyticsSummary {
  date_from: string
  date_to: string
  total_attendance: number
  total_absentees: number
  total_calls: number
  completed_calls: number
  no_answer_calls: number
  busy_calls: number
  failed_calls: number
  unreachable_calls: number
  pending_calls: number
  answer_rate: number
  no_answer_rate: number
  failure_rate: number
  average_duration_seconds: number | null
  total_followups: number
  pending_followups: number
  completed_followups: number
}

export interface DailyTrend {
  date: string
  total_attendance: number
  absentees: number
  calls: number
  completed_calls: number
}

export interface CallMetrics {
  date_from: string
  date_to: string
  total_calls: number
  status_distribution: Record<string, number>
  answer_rate: number
  completion_rate: number
  retry_rate: number
  average_duration_seconds: number | null
}

export interface AbsenceReason {
  category: string
  count: number
}

export interface UnreachableEntry {
  call_id: string
  student_id: string
  phone_number: string
  retry_count: number
  last_updated: string | null
}

export interface UnreachableReport {
  report_type: 'unreachable'
  date_from: string
  date_to: string
  total: number
  entries: UnreachableEntry[]
}

export interface FollowUpReport {
  report_type: 'followup'
  date_from: string
  date_to: string
  total: number
  by_type: Record<string, number>
  by_priority: Record<string, number>
  by_status: Record<string, number>
}
