# AttendAI Architecture Documentation

## Overview

AttendAI is an AI-powered automated student absence communication and faculty intelligence platform. When a student is marked absent, the system automatically initiates a voice call to the student's parent/guardian, gathers information about the absence, and stores structured data for faculty review and reporting.

## System Architecture

### High-Level Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   Next.js UI    │◄────────│  Faculty/Admin   │
│   Dashboard     │         └──────────────────┘
└────────┬────────┘
         │ REST API
         │
┌────────▼────────────────────────────────────────────┐
│              FastAPI Backend                        │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Auth    │  │  API     │  │  Webhook         │ │
│  │  Layer   │  │  Routers │  │  Handlers        │ │
│  └──────────┘  └──────────┘  └──────────────────┘ │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Business │  │  AI      │  │  Background      │ │
│  │ Services │  │ Services │  │  Jobs            │ │
│  └──────────┘  └──────────┘  └──────────────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         Repository Layer (SQLAlchemy)        │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │                          │
         │                          │
┌────────▼────────┐        ┌────────▼────────┐
│   PostgreSQL    │        │     Redis       │
│   (Primary DB)  │        │  (Cache/Queue)  │
└─────────────────┘        └─────────────────┘

         ┌──────────────────┐
         │   Vapi Voice AI  │
         │   (External API) │
         └────────┬─────────┘
                  │ Webhooks
                  ▼
         ┌──────────────────┐
         │  Parent/Guardian │
         │   Phone Call     │
         └──────────────────┘
```

## Core Components

### 1. Backend (FastAPI)

#### Layer Structure

**API Layer (Routers)**
- `auth.py` - Authentication endpoints
- `students.py` - Student management
- `parents.py` - Parent/guardian management
- `attendance.py` - Attendance recording and import
- `calls.py` - Call management and history
- `reports.py` - Absence reports and analytics
- `followups.py` - Follow-up task management
- `webhooks.py` - Vapi webhook handlers
- `health.py` - Health checks and monitoring

**Service Layer**
- `auth_service.py` - JWT, session management
- `student_service.py` - Student business logic
- `attendance_service.py` - Absence detection, trigger logic
- `call_orchestration_service.py` - Call queue, retry logic
- `vapi_service.py` - Vapi API integration
- `ai_extraction_service.py` - Transcript → structured data
- `llm_provider.py` - Provider abstraction (OpenAI/Anthropic)
- `report_service.py` - Analytics and reporting
- `followup_service.py` - Follow-up task management

**Repository Layer**
- `user_repository.py`
- `student_repository.py`
- `parent_repository.py`
- `attendance_repository.py`
- `call_repository.py`
- `absence_report_repository.py`
- `audit_repository.py`

**Background Jobs**
- Call queue processor
- Retry scheduler
- Follow-up notifications
- Data retention cleanup
- Daily report generation

### 2. Database Schema (PostgreSQL)

#### Core Tables

**users**
- `id` (UUID, PK)
- `email` (unique)
- `hashed_password`
- `full_name`
- `role` (enum: admin, faculty, staff)
- `department`
- `is_active`
- `created_at`, `updated_at`

**students**
- `id` (UUID, PK)
- `student_id` (unique identifier)
- `first_name`, `last_name`
- `date_of_birth`
- `grade_level`
- `department`
- `is_active`
- `created_at`, `updated_at`

**parents**
- `id` (UUID, PK)
- `student_id` (FK → students)
- `relationship` (mother, father, guardian, etc.)
- `first_name`, `last_name`
- `primary_phone`
- `secondary_phone`
- `email`
- `preferred_contact_method`
- `preferred_language`
- `is_primary_contact`
- `created_at`, `updated_at`

**attendance**
- `id` (UUID, PK)
- `student_id` (FK → students)
- `date`
- `status` (present, absent, late, excused)
- `period` (optional)
- `recorded_by` (FK → users)
- `notes`
- `created_at`, `updated_at`
- Unique constraint on (student_id, date, period)

**call_campaigns**
- `id` (UUID, PK)
- `name`
- `description`
- `status` (draft, active, paused, completed)
- `created_by` (FK → users)
- `scheduled_start`
- `created_at`, `updated_at`

**calls**
- `id` (UUID, PK)
- `campaign_id` (FK → call_campaigns, nullable)
- `student_id` (FK → students)
- `parent_id` (FK → parents)
- `attendance_id` (FK → attendance)
- `status` (enum: PENDING, QUEUED, CALLING, ANSWERED, COMPLETED, NO_ANSWER, BUSY, FAILED, etc.)
- `scheduled_time`
- `initiated_at`, `answered_at`, `ended_at`
- `duration_seconds`
- `vapi_call_id`
- `phone_number_called`
- `retry_count`
- `max_retries`
- `created_at`, `updated_at`

**call_attempts**
- `id` (UUID, PK)
- `call_id` (FK → calls)
- `attempt_number`
- `status`
- `initiated_at`, `ended_at`
- `duration_seconds`
- `vapi_call_id`
- `error_message`
- `created_at`

**absence_reports**
- `id` (UUID, PK)
- `call_id` (FK → calls)
- `student_id` (FK → students)
- `attendance_id` (FK → attendance)
- `reason` (text)
- `category` (medical, family, personal, other, unknown)
- `duration` (text, e.g., "1 day", "2-3 days")
- `expected_return_date`
- `parent_confirmed` (boolean)
- `follow_up_required` (boolean)
- `confidence_score` (float, 0.0-1.0)
- `transcript` (text)
- `raw_extraction` (JSONB)
- `reviewed_by` (FK → users, nullable)
- `reviewed_at`
- `review_notes`
- `created_at`, `updated_at`

**followups**
- `id` (UUID, PK)
- `absence_report_id` (FK → absence_reports, nullable)
- `call_id` (FK → calls, nullable)
- `student_id` (FK → students)
- `type` (callback_requested, low_confidence, medical_verification, other)
- `priority` (low, medium, high)
- `due_date`
- `assigned_to` (FK → users, nullable)
- `status` (pending, in_progress, completed, cancelled)
- `description`
- `resolution_notes`
- `completed_at`
- `created_at`, `updated_at`

**audit_logs**
- `id` (UUID, PK)
- `user_id` (FK → users, nullable)
- `action` (enum or string)
- `entity_type` (student, call, absence_report, etc.)
- `entity_id` (UUID)
- `changes` (JSONB)
- `ip_address`
- `user_agent`
- `created_at`

### 3. AI Components

#### Voice Agent (Vapi Integration)

**Purpose**: Conduct natural, administrative phone conversations with parents.

**Capabilities**:
- Greet parent appropriately
- Identify parent/guardian relationship
- Explain reason for call (student absence)
- Ask for absence reason
- Ask for expected return/duration
- Confirm information with parent
- Handle clarifications
- End call politely
- Never diagnose medical conditions
- Never invent information

**Configuration**:
```python
{
    "model": "gpt-4o",  # or equivalent
    "voice": "professional-friendly",
    "first_message": "Hello, this is AttendAI calling from [School Name] regarding [Student Name]...",
    "system_prompt": "[Detailed agent instructions]",
    "end_call_message": "Thank you for your time. Have a great day.",
    "max_duration_seconds": 300
}
```

#### Extraction Agent

**Purpose**: Convert unstructured call transcripts into validated structured data.

**Input**: Call transcript (text)

**Output**:
```json
{
    "reason": "Fever and headache",
    "category": "medical",
    "duration": "1-2 days",
    "expected_return": "2026-09-14",
    "parent_confirmed": true,
    "follow_up_required": false,
    "confidence": 0.94,
    "uncertain_fields": [],
    "extraction_notes": "Parent explicitly stated medical reason."
}
```

**LLM Provider Abstraction**:
```python
class LLMProvider(ABC):
    @abstractmethod
    async def extract_structured_data(
        self, 
        transcript: str, 
        schema: Dict
    ) -> Dict:
        pass

class OpenAIProvider(LLMProvider):
    # Implementation using structured outputs

class AnthropicProvider(LLMProvider):
    # Implementation using tool use
```

### 4. Frontend (Next.js)

#### Pages/Routes

- `/login` - Authentication
- `/dashboard` - Main dashboard (today's overview)
- `/students` - Student list and management
- `/students/[id]` - Student detail view
- `/attendance` - Attendance recording and import
- `/calls` - Call history and status
- `/calls/[id]` - Call detail with transcript
- `/reports` - Analytics and reports
- `/followups` - Follow-up task queue
- `/settings` - System configuration
- `/admin` - User and system management

#### Key Components

- `DashboardStats` - Today's metrics
- `AbsenteeList` - List of absentees with call status
- `CallStatusBadge` - Visual call status indicator
- `ConfidenceIndicator` - Visual confidence score
- `TranscriptViewer` - Formatted transcript display
- `AbsenceReportCard` - Structured absence information
- `FollowupQueue` - Prioritized follow-up list
- `ReportBuilder` - Custom report generation
- `StudentSearch` - Search and filter students

### 5. Security Architecture

**Authentication**:
- JWT-based authentication
- Refresh token rotation
- Password hashing with bcrypt
- Rate limiting on auth endpoints

**Authorization**:
- Role-based access control (RBAC)
- Permission decorators on endpoints
- Row-level security for multi-tenant scenarios

**Data Protection**:
- Webhook signature verification
- Input validation with Pydantic
- SQL injection prevention (SQLAlchemy ORM)
- CORS configuration
- Secrets in environment variables only
- Audit logging for sensitive operations

**Privacy**:
- Configurable data retention policies
- Automatic transcript/recording purging
- Parent contact information encryption (future)
- FERPA compliance considerations

## Call Flow Sequence

```
1. Attendance Recorded → Student Marked Absent
                           ↓
2. Attendance Service → Detects New Absence
                           ↓
3. Call Orchestration → Creates Call Record (PENDING)
                           ↓
4. Background Job → Picks Up Call (QUEUED)
                           ↓
5. Vapi Service → Initiates Call via Vapi API (CALLING)
                           ↓
6. Vapi → Calls Parent's Phone
                           ↓
7. Voice Agent → Conducts Conversation (ANSWERED)
                           ↓
8. Call Ends → Vapi Sends Webhook (COMPLETED/NO_ANSWER/etc.)
                           ↓
9. Webhook Handler → Verifies + Processes Webhook
                           ↓
10. Extraction Service → Retrieves Transcript
                           ↓
11. LLM Provider → Extracts Structured Data
                           ↓
12. Absence Report → Created with Confidence Score
                           ↓
13. Low Confidence? → Create Follow-up Task
                           ↓
14. Dashboard → Updates with New Data
                           ↓
15. Faculty → Reviews and Acts on Report
```

## Technology Decisions

### Why FastAPI?
- Modern async Python framework
- Automatic OpenAPI documentation
- Pydantic validation built-in
- High performance
- Excellent typing support

### Why PostgreSQL?
- ACID compliance for critical attendance data
- Rich data types (JSONB for flexible storage)
- Strong community support
- Proven reliability

### Why Redis?
- Fast caching layer
- Background job queue
- Session storage
- Rate limiting support

### Why Vapi?
- Purpose-built for voice AI
- Natural conversation handling
- Reliable webhook delivery
- Developer-friendly API

### Why LLM Provider Abstraction?
- Flexibility to switch providers
- Cost optimization
- Feature comparison
- Vendor independence

## Deployment Considerations

### Development
- Docker Compose for local environment
- Hot reload for both frontend and backend
- Seeded test data
- Mock Vapi integration for testing

### Production (Future)
- Container orchestration (Kubernetes/ECS)
- Managed PostgreSQL (RDS/Cloud SQL)
- Managed Redis (ElastiCache/Cloud Memorystore)
- CDN for frontend assets
- Load balancer for API
- Secrets management (AWS Secrets Manager/GCP Secret Manager)
- Monitoring (Prometheus/Grafana/Datadog)
- Centralized logging (ELK/CloudWatch)
- Automated backups
- SSL/TLS everywhere
- WAF for API protection

## Scalability Considerations

### Database
- Connection pooling
- Read replicas for analytics
- Partitioning for audit logs
- Archival strategy for old data

### API
- Horizontal scaling with load balancer
- Rate limiting per user/IP
- Response caching
- Async processing for heavy operations

### Background Jobs
- Distributed task queue
- Job prioritization
- Retry with exponential backoff
- Dead letter queue for failed jobs

## Testing Strategy

### Backend
- Unit tests for services and repositories
- Integration tests for API endpoints
- End-to-end tests for critical flows
- Mock external services (Vapi, LLM providers)
- Database transaction rollback in tests

### Frontend
- Component unit tests (Jest/Vitest)
- Integration tests (React Testing Library)
- E2E tests (Playwright)
- Visual regression testing (optional)

## Compliance & Privacy

### FERPA Considerations
- Access controls for student data
- Audit logging for data access
- Data retention policies
- Parent consent tracking (future)

### GDPR Considerations (if applicable)
- Right to access
- Right to deletion
- Data portability
- Consent management

## Future Enhancements

- Multi-language voice support
- SMS notifications
- Email summaries
- Parent portal for self-service
- Mobile app for faculty
- ML-based absence pattern detection
- Integration with student information systems (SIS)
- Calendar integration
- Advanced analytics and predictions
