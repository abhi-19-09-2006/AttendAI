"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-09-12 05:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('ADMIN', 'FACULTY', 'STAFF', name='userrole'), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create students table
    op.create_table('students',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('student_id', sa.String(length=50), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('date_of_birth', sa.Date(), nullable=False),
    sa.Column('grade_level', sa.Integer(), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_students_student_id'), 'students', ['student_id'], unique=True)

    # Create parents table
    op.create_table('parents',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('student_id', sa.String(length=36), nullable=False),
    sa.Column('relationship', sa.Enum('MOTHER', 'FATHER', 'GUARDIAN', 'STEPMOTHER', 'STEPFATHER', 'GRANDPARENT', 'OTHER', name='parentrelationship'), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('primary_phone', sa.String(length=20), nullable=False),
    sa.Column('secondary_phone', sa.String(length=20), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('preferred_contact_method', sa.Enum('PHONE', 'EMAIL', 'SMS', name='contactmethod'), nullable=False),
    sa.Column('preferred_language', sa.String(length=10), nullable=False),
    sa.Column('is_primary_contact', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parents_student_id'), 'parents', ['student_id'], unique=False)

    # Create attendance table
    op.create_table('attendance',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('student_id', sa.String(length=36), nullable=False),
    sa.Column('recorded_by', sa.String(length=36), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('PRESENT', 'ABSENT', 'LATE', 'EXCUSED', name='attendancestatus'), nullable=False),
    sa.Column('period', sa.String(length=20), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('student_id', 'date', 'period', name='uq_student_date_period')
    )
    op.create_index(op.f('ix_attendance_date'), 'attendance', ['date'], unique=False)
    op.create_index(op.f('ix_attendance_status'), 'attendance', ['status'], unique=False)
    op.create_index('ix_attendance_student_date', 'attendance', ['student_id', 'date'], unique=False)

    # Create call_campaigns table
    op.create_table('call_campaigns',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'PAUSED', 'COMPLETED', name='campaignstatus'), nullable=False),
    sa.Column('created_by', sa.String(length=36), nullable=False),
    sa.Column('scheduled_start', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create calls table
    op.create_table('calls',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('campaign_id', sa.String(length=36), nullable=True),
    sa.Column('student_id', sa.String(length=36), nullable=False),
    sa.Column('parent_id', sa.String(length=36), nullable=False),
    sa.Column('attendance_id', sa.String(length=36), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'QUEUED', 'CALLING', 'ANSWERED', 'COMPLETED', 'NO_ANSWER', 'BUSY', 'FAILED', 'INVALID_NUMBER', 'CALLBACK_REQUESTED', 'FOLLOW_UP_REQUIRED', 'UNREACHABLE', name='callstatus'), nullable=False),
    sa.Column('phone_number_called', sa.String(length=20), nullable=False),
    sa.Column('vapi_call_id', sa.String(length=255), nullable=True),
    sa.Column('scheduled_time', sa.DateTime(), nullable=True),
    sa.Column('initiated_at', sa.DateTime(), nullable=True),
    sa.Column('answered_at', sa.DateTime(), nullable=True),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('max_retries', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['attendance_id'], ['attendance.id'], ),
    sa.ForeignKeyConstraint(['campaign_id'], ['call_campaigns.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['parents.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calls_scheduled_time'), 'calls', ['scheduled_time'], unique=False)
    op.create_index(op.f('ix_calls_status'), 'calls', ['status'], unique=False)
    op.create_index(op.f('ix_calls_student_id'), 'calls', ['student_id'], unique=False)
    op.create_index(op.f('ix_calls_vapi_call_id'), 'calls', ['vapi_call_id'], unique=False)

    # Create call_attempts table
    op.create_table('call_attempts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('call_id', sa.String(length=36), nullable=False),
    sa.Column('attempt_number', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'QUEUED', 'CALLING', 'ANSWERED', 'COMPLETED', 'NO_ANSWER', 'BUSY', 'FAILED', 'INVALID_NUMBER', 'CALLBACK_REQUESTED', 'FOLLOW_UP_REQUIRED', 'UNREACHABLE', name='callstatus'), nullable=False),
    sa.Column('vapi_call_id', sa.String(length=255), nullable=True),
    sa.Column('initiated_at', sa.DateTime(), nullable=False),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_call_attempts_call_id', 'call_attempts', ['call_id'], unique=False)

    # Create absence_reports table
    op.create_table('absence_reports',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('call_id', sa.String(length=36), nullable=False),
    sa.Column('student_id', sa.String(length=36), nullable=False),
    sa.Column('attendance_id', sa.String(length=36), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('category', sa.Enum('MEDICAL', 'FAMILY', 'PERSONAL', 'OTHER', 'UNKNOWN', name='absencecategory'), nullable=False),
    sa.Column('duration', sa.String(length=100), nullable=True),
    sa.Column('expected_return_date', sa.Date(), nullable=True),
    sa.Column('parent_confirmed', sa.Boolean(), nullable=False),
    sa.Column('follow_up_required', sa.Boolean(), nullable=False),
    sa.Column('confidence_score', sa.Float(), nullable=False),
    sa.Column('transcript', sa.Text(), nullable=True),
    sa.Column('raw_extraction', sa.JSON(), nullable=True),
    sa.Column('reviewed_by', sa.String(length=36), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('review_notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['attendance_id'], ['attendance.id'], ),
    sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('call_id')
    )
    op.create_index('ix_absence_reports_confidence_score', 'absence_reports', ['confidence_score'], unique=False)
    op.create_index('ix_absence_reports_follow_up_required', 'absence_reports', ['follow_up_required'], unique=False)
    op.create_index('ix_absence_reports_reviewed_by', 'absence_reports', ['reviewed_by'], unique=False)

    # Create followups table
    op.create_table('followups',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('absence_report_id', sa.String(length=36), nullable=True),
    sa.Column('call_id', sa.String(length=36), nullable=True),
    sa.Column('student_id', sa.String(length=36), nullable=False),
    sa.Column('assigned_to', sa.String(length=36), nullable=True),
    sa.Column('type', sa.Enum('CALLBACK_REQUESTED', 'LOW_CONFIDENCE', 'MEDICAL_VERIFICATION', 'OTHER', name='followuptype'), nullable=False),
    sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='followuppriority'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='followupstatus'), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('resolution_notes', sa.Text(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['absence_report_id'], ['absence_reports.id'], ),
    sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
    sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_followups_assigned_to', 'followups', ['assigned_to'], unique=False)
    op.create_index('ix_followups_due_date', 'followups', ['due_date'], unique=False)
    op.create_index('ix_followups_priority', 'followups', ['priority'], unique=False)
    op.create_index('ix_followups_status', 'followups', ['status'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.String(length=36), nullable=False),
    sa.Column('changes', sa.JSON(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('followups')
    op.drop_table('absence_reports')
    op.drop_table('call_attempts')
    op.drop_table('calls')
    op.drop_table('call_campaigns')
    op.drop_table('attendance')
    op.drop_table('parents')
    op.drop_table('students')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS followupstatus')
    op.execute('DROP TYPE IF EXISTS followuppriority')
    op.execute('DROP TYPE IF EXISTS followuptype')
    op.execute('DROP TYPE IF EXISTS absencecategory')
    op.execute('DROP TYPE IF EXISTS callstatus')
    op.execute('DROP TYPE IF EXISTS campaignstatus')
    op.execute('DROP TYPE IF EXISTS attendancestatus')
    op.execute('DROP TYPE IF EXISTS contactmethod')
    op.execute('DROP TYPE IF EXISTS parentrelationship')
    op.execute('DROP TYPE IF EXISTS userrole')
