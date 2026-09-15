"""add job table for rq background jobs

Revision ID: 002
Revises: 001
Create Date: 2026-09-14 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create jobs table (without foreign keys for now, as they're optional)
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rq_job_id', sa.String(length=255), nullable=True),
        sa.Column('job_type', sa.Enum('SCHEDULE_CAMPAIGN_CALLS', 'INITIATE_CALL', 'RETRY_CALL', 'CREATE_FOLLOWUP_CALLS', 'GENERATE_REPORT', 'PROCESS_COMPLETION', name='jobtype'), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'STARTED', 'COMPLETED', 'FAILED', 'DEFERRED', name='jobstatus'), nullable=False, server_default='QUEUED'),
        sa.Column('call_id', sa.String(length=36), nullable=True),
        sa.Column('campaign_id', sa.String(length=36), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rq_job_id', name='uq_jobs_rq_job_id'),
        sa.UniqueConstraint('idempotency_key', name='uq_jobs_idempotency_key'),
    )
    # Create indexes
    op.create_index('ix_jobs_rq_id', 'jobs', ['rq_job_id'], unique=False)
    op.create_index('ix_jobs_type', 'jobs', ['job_type'], unique=False)
    op.create_index('ix_jobs_status', 'jobs', ['status'], unique=False)
    op.create_index('ix_jobs_call_id', 'jobs', ['call_id'], unique=False)
    op.create_index('ix_jobs_campaign_id', 'jobs', ['campaign_id'], unique=False)
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_campaign_id', table_name='jobs')
    op.drop_index('ix_jobs_call_id', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_type', table_name='jobs')
    op.drop_index('ix_jobs_rq_id', table_name='jobs')

    # Drop table
    op.drop_table('jobs')
