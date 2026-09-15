#!/usr/bin/env python
"""Create test database schema."""
import asyncio
import asyncpg

async def create_schema():
    conn = await asyncpg.connect('postgresql://attendai:attendai_dev_password@localhost:5432/attendai_db')
    try:
        # Check if enum exists before creating
        async def create_enum_if_not_exists(enum_name, values):
            result = await conn.fetch(
                "SELECT 1 FROM pg_type WHERE typname = $1",
                enum_name
            )
            if not result:
                await conn.execute(f"CREATE TYPE {enum_name} AS ENUM ({', '.join(repr(v) for v in values)})")
                print(f"Created enum {enum_name}")

        await create_enum_if_not_exists("userrole", ["ADMIN", "FACULTY", "STAFF"])
        await create_enum_if_not_exists("parentrelationship", ["MOTHER", "FATHER", "GUARDIAN", "STEPMOTHER", "STEPFATHER", "GRANDPARENT", "OTHER"])
        await create_enum_if_not_exists("contactmethod", ["PHONE", "EMAIL", "SMS"])
        await create_enum_if_not_exists("attendancestatus", ["PRESENT", "ABSENT", "LATE", "EXCUSED"])
        await create_enum_if_not_exists("campaignstatus", ["DRAFT", "ACTIVE", "PAUSED", "COMPLETED"])
        await create_enum_if_not_exists("callstatus", ["PENDING", "QUEUED", "CALLING", "ANSWERED", "COMPLETED", "NO_ANSWER", "BUSY", "FAILED", "INVALID_NUMBER", "CALLBACK_REQUESTED", "FOLLOW_UP_REQUIRED", "UNREACHABLE"])
        await create_enum_if_not_exists("absencecategory", ["MEDICAL", "FAMILY", "PERSONAL", "OTHER", "UNKNOWN"])
        await create_enum_if_not_exists("followuptype", ["CALLBACK_REQUESTED", "LOW_CONFIDENCE", "MEDICAL_VERIFICATION", "OTHER"])
        await create_enum_if_not_exists("followuppriority", ["LOW", "MEDIUM", "HIGH"])
        await create_enum_if_not_exists("followupstatus", ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"])
        await create_enum_if_not_exists("jobtype", ["SCHEDULE_CAMPAIGN_CALLS", "INITIATE_CALL", "RETRY_CALL", "CREATE_FOLLOWUP_CALLS", "GENERATE_REPORT", "PROCESS_COMPLETION"])
        await create_enum_if_not_exists("jobstatus", ["QUEUED", "STARTED", "COMPLETED", "FAILED", "DEFERRED"])

        print('Enums created')

        # Create tables with IF NOT EXISTS
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                hashed_password VARCHAR(255),
                full_name VARCHAR(255),
                role userrole,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id VARCHAR(36) PRIMARY KEY,
                student_id VARCHAR(50) NOT NULL UNIQUE,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                date_of_birth DATE,
                grade_level INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS parents (
                id VARCHAR(36) PRIMARY KEY,
                student_id VARCHAR(36),
                relationship parentrelationship,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                primary_phone VARCHAR(20),
                is_primary_contact BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id VARCHAR(36) PRIMARY KEY,
                student_id VARCHAR(36),
                recorded_by VARCHAR(36),
                date DATE,
                status attendancestatus,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS call_campaigns (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255),
                status campaignstatus DEFAULT 'DRAFT',
                created_by VARCHAR(36),
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS calls (
                id VARCHAR(36) PRIMARY KEY,
                campaign_id VARCHAR(36),
                student_id VARCHAR(36),
                parent_id VARCHAR(36),
                attendance_id VARCHAR(36),
                status callstatus DEFAULT 'PENDING',
                phone_number_called VARCHAR(20),
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS absence_reports (
                id VARCHAR(36) PRIMARY KEY,
                call_id VARCHAR(36) UNIQUE,
                student_id VARCHAR(36),
                attendance_id VARCHAR(36),
                category absencecategory,
                confidence_score FLOAT,
                follow_up_required BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS followups (
                id VARCHAR(36) PRIMARY KEY,
                absence_report_id VARCHAR(36),
                call_id VARCHAR(36),
                student_id VARCHAR(36),
                type followuptype,
                priority followuppriority,
                status followupstatus DEFAULT 'PENDING',
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36),
                action VARCHAR(100),
                entity_type VARCHAR(50),
                entity_id VARCHAR(36),
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        print('Tables created')

        # Create indexes with IF NOT EXISTS
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_students_student_id ON students (student_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_parents_student_id ON parents (student_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_attendance_date ON attendance (date)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_attendance_status ON attendance (status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_attendance_student_date ON attendance (student_id, date)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_calls_status ON calls (status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_calls_student_id ON calls (student_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_followups_status ON followups (status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_followups_priority ON followups (priority)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs (status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_type ON jobs (job_type)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_call_id ON jobs (call_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_campaign_id ON jobs (campaign_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_created_at ON jobs (created_at)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_rq_id ON jobs (rq_job_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_idempotency_key ON jobs (idempotency_key)')

        print('Indexes created')

        # List all tables
        result = await conn.fetch('''
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        ''')
        print(f'All {len(result)} tables:')
        for r in result:
            print(f'  {r[0]}')

    finally:
        await conn.close()

asyncio.run(create_schema())
