# AttendAI Development Plan

## Project Phases

This document outlines the phased development approach for AttendAI. Each phase builds upon the previous one and includes clear deliverables and acceptance criteria.

---

## ✅ Phase 1: Foundation & Architecture (CURRENT)

**Goal**: Establish project structure, documentation, and development environment.

**Deliverables**:
- [x] Repository structure
- [x] ARCHITECTURE.md
- [x] DEVELOPMENT_PLAN.md
- [x] README.md
- [x] .gitignore
- [x] .env.example
- [ ] Docker Compose configuration
- [ ] Backend skeleton (FastAPI)
- [ ] Frontend skeleton (Next.js)
- [ ] Health check endpoints
- [ ] Basic configuration management

**Acceptance Criteria**:
- Docker Compose starts all services
- Backend health endpoint returns 200
- Frontend loads landing page
- Environment variables load correctly
- No secrets in Git

**Estimated Time**: 1-2 days

---

## Phase 2: Database Layer

**Goal**: Design and implement PostgreSQL schema with migrations.

**Deliverables**:
- SQLAlchemy models for all entities:
  - users, roles
  - students, parents
  - attendance
  - call_campaigns, calls, call_attempts
  - absence_reports
  - followups
  - audit_logs
- Alembic migration setup
- Initial migration creating all tables
- Seed data script for development
- Repository classes for each model
- Basic CRUD operations

**Acceptance Criteria**:
- `alembic upgrade head` creates all tables
- Seed script populates realistic test data
- Foreign key relationships work correctly
- Repositories tested with unit tests
- Database connection pooling configured

**Estimated Time**: 2-3 days

---

## Phase 3: Authentication & Core APIs

**Goal**: Implement secure authentication and foundational REST APIs.

**Deliverables**:
- JWT authentication system
- Password hashing with bcrypt
- Login/logout endpoints
- Token refresh mechanism
- Role-based authorization decorators
- User management API
- Student management API (CRUD)
- Parent management API (CRUD)
- API documentation (automatic via FastAPI)
- Input validation with Pydantic schemas

**Acceptance Criteria**:
- Users can register and login
- JWT tokens work correctly
- Authorization prevents unauthorized access
- All CRUD operations functional
- API docs accessible at /docs
- Validation errors return clear messages

**Estimated Time**: 3-4 days

---

## Phase 4: Attendance Management

**Goal**: Build attendance recording and absentee detection.

**Deliverables**:
- Attendance recording API
- Bulk attendance import (CSV)
- Attendance history API
- Absentee detection service
- Automatic call task creation for new absences
- Attendance statistics endpoints
- Date range queries
- Student attendance report

**Acceptance Criteria**:
- Attendance can be recorded manually
- CSV import works with error handling
- New absence triggers call task creation
- Attendance history retrieved correctly
- Statistics accurate and performant

**Estimated Time**: 2-3 days

---

## Phase 5: Voice Provider Integration

**Goal**: Integrate Vapi for AI voice calling with provider abstraction.

**Deliverables**:
- LLM provider abstraction layer
- OpenAI provider implementation
- Anthropic provider implementation
- Vapi service client
- Voice agent configuration
- Call initiation logic
- Dynamic variable injection (student name, parent name)
- Error handling for API failures
- Provider selection via environment variable

**Acceptance Criteria**:
- Call can be initiated via Vapi API
- Voice agent receives correct student/parent context
- Both OpenAI and Anthropic providers work
- Provider switching requires only env change
- Errors logged and handled gracefully

**Estimated Time**: 3-4 days

---

## Phase 6: Webhook Handling & Call Lifecycle

**Goal**: Process Vapi webhooks and manage complete call lifecycle.

**Deliverables**:
- Webhook endpoint with signature verification
- Webhook event handlers (call.started, call.ended, etc.)
- Call status state machine
- Call attempt tracking
- Transcript retrieval and storage
- Recording URL storage (optional)
- Call history API
- Call detail API with transcript

**Acceptance Criteria**:
- Webhooks verified and processed correctly
- Call status updates in real-time
- Transcripts stored in database
- Failed webhook signature returns 401
- Call history shows accurate timeline

**Estimated Time**: 2-3 days

---

## Phase 7: AI Extraction & Absence Reports

**Goal**: Extract structured data from transcripts using LLM.

**Acceptance Criteria**:
- Extraction service implemented for both providers
- Confidence scoring works accurately
- Low-confidence reports flagged for review
- Follow-up tasks created automatically
- Extraction handles edge cases (incomplete info)
- Schema validation on extraction output

**Deliverables**:
- AI extraction service
- Structured output schema
- Confidence calculation algorithm
- Absence report creation from extraction
- Low-confidence flagging logic
- Follow-up task creation
- Extraction testing with sample transcripts
- Provider-agnostic extraction interface

**Estimated Time**: 3-4 days

---

## Phase 8: Retry & Follow-up Engine

**Goal**: Handle call failures, retries, and follow-up management.

**Deliverables**:
- Retry logic for failed/no-answer calls
- Exponential backoff strategy
- Maximum retry limit enforcement
- Follow-up task management API
- Follow-up assignment to faculty
- Follow-up status tracking
- Follow-up notifications (future: email/SMS)
- Background job for retry scheduling

**Acceptance Criteria**:
- Failed calls automatically retry
- Retry delays respect configuration
- Max retries enforced correctly
- Follow-ups can be assigned and tracked
- Faculty can mark follow-ups complete

**Estimated Time**: 2-3 days

---

## Phase 9: Faculty Dashboard (Frontend)

**Goal**: Build Next.js dashboard for faculty to monitor and manage calls.

**Deliverables**:
- Login page with authentication
- Dashboard homepage with statistics
- Student list and search
- Student detail page with attendance history
- Call history page
- Call detail page with transcript viewer
- Absence report display
- Follow-up queue interface
- Responsive design (desktop + mobile)
- Dark mode support (optional)

**Acceptance Criteria**:
- Faculty can login and access dashboard
- Dashboard shows accurate real-time statistics
- All pages responsive and functional
- Call transcripts displayed clearly
- Confidence scores visualized
- Follow-up tasks manageable

**Estimated Time**: 5-7 days

---

## Phase 10: Analytics, Reports & Audit

**Goal**: Provide comprehensive reporting and audit capabilities.

**Deliverables**:
- Analytics service
- Dashboard statistics (daily/weekly/monthly)
- Absence reason trends
- Call completion rates
- Department/grade-level breakdowns
- Custom date range reports
- CSV export functionality
- PDF report generation (optional)
- Excel export (optional)
- Audit log API
- Audit log viewer in dashboard

**Acceptance Criteria**:
- Reports generate accurate data
- Exports work correctly
- Charts/graphs display trends
- Audit logs capture all sensitive actions
- Performance acceptable for large datasets

**Estimated Time**: 3-4 days

---

## Phase 11: Testing & Security Hardening

**Goal**: Comprehensive testing and security improvements.

**Deliverables**:
- Unit tests for all services (>80% coverage)
- Integration tests for API endpoints
- End-to-end test suite
- Security audit checklist
- Rate limiting implementation
- Input sanitization review
- CORS configuration hardening
- SQL injection testing
- XSS prevention testing
- Secrets scanning
- Security headers configuration
- Error handling improvements (no stack traces in production)

**Acceptance Criteria**:
- Test coverage >80%
- All critical paths covered by E2E tests
- Security audit passes
- Rate limiting prevents abuse
- No secrets in codebase
- Error messages safe for production

**Estimated Time**: 4-5 days

---

## Phase 12: End-to-End Validation

**Goal**: Test complete system with real phone calls (test numbers).

**Deliverables**:
- Test phone number setup
- End-to-end test scenarios
- Call flow validation
- Transcript accuracy verification
- Extraction accuracy validation
- Performance testing
- Load testing (optional)
- User acceptance testing (UAT) preparation
- Production deployment checklist
- Production configuration guide
- Backup and recovery procedures

**Acceptance Criteria**:
- Complete absence flow works end-to-end
- Voice agent performs well in test calls
- Extraction accuracy >90%
- System handles expected load
- Production deployment documented

**Estimated Time**: 3-4 days

---

## Total Estimated Timeline

**Minimum**: 30-38 days (6-8 weeks)  
**Realistic**: 40-50 days (8-10 weeks) accounting for learning curve, debugging, and iteration

---

## Phase Dependencies

```
Phase 1 (Foundation)
    ↓
Phase 2 (Database)
    ↓
Phase 3 (Auth & APIs)
    ↓
Phase 4 (Attendance) + Phase 5 (Voice Integration)
    ↓
Phase 6 (Webhooks)
    ↓
Phase 7 (AI Extraction)
    ↓
Phase 8 (Retry/Follow-up)
    ↓
Phase 9 (Dashboard) + Phase 10 (Analytics)
    ↓
Phase 11 (Testing/Security)
    ↓
Phase 12 (E2E Validation)
```

Phases 4 and 5 can be developed in parallel by different team members.  
Phases 9 and 10 can partially overlap once Phase 7 is complete.

---

## Success Metrics

### Phase Completion Metrics
- All deliverables completed
- All acceptance criteria met
- Code reviewed and merged
- Tests passing
- Documentation updated

### Project Success Metrics
- System successfully places calls
- Extraction accuracy >90%
- Faculty satisfaction score >4/5
- System uptime >99%
- Average call completion time <5 minutes
- Follow-up resolution time <24 hours

---

## Risk Management

### Technical Risks
- **Voice AI quality**: Mitigation - extensive testing, prompt engineering
- **LLM extraction accuracy**: Mitigation - confidence scoring, human review
- **Webhook reliability**: Mitigation - retry logic, idempotency
- **Scale**: Mitigation - load testing, optimization

### Project Risks
- **Scope creep**: Mitigation - strict phase boundaries, MVP focus
- **API changes**: Mitigation - provider abstraction, version pinning
- **Timeline slippage**: Mitigation - regular progress reviews, buffer time

---

## Post-Launch Roadmap

### Version 1.1
- Multi-language support
- SMS notifications
- Email integration
- Parent portal

### Version 1.2
- Mobile app for faculty
- Advanced analytics
- ML-based pattern detection
- SIS integration

### Version 2.0
- Multi-school/district support
- White-label capability
- Advanced AI features
- Predictive analytics

---

## Development Best Practices

1. **Version Control**
   - Meaningful commit messages
   - Feature branches
   - Pull request reviews
   - Conventional commits

2. **Code Quality**
   - Type hints in Python
   - Linting (ruff/black for Python, ESLint for TypeScript)
   - Code formatting automation
   - No commented-out code in production

3. **Documentation**
   - Inline code comments for complex logic
   - API documentation
   - README updates per phase
   - Architecture decision records (ADRs)

4. **Testing**
   - Write tests during development, not after
   - Test edge cases
   - Mock external services
   - Maintain test data fixtures

5. **Security**
   - Never commit secrets
   - Review all external input
   - Principle of least privilege
   - Regular dependency updates
