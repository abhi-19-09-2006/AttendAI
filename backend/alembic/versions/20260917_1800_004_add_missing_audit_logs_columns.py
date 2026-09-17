"""add missing audit_logs columns (changes, ip_address, user_agent)

Revision ID: 004
Revises: 003
Create Date: 2026-09-17 18:00:00.000000

This migration adds the missing columns to audit_logs that are required by
the AuditLog model but were not present in the original schema.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing audit_logs columns if they don't exist."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get current columns in audit_logs
    audit_logs_columns = [col['name'] for col in inspector.get_columns('audit_logs')]
    
    # Add 'changes' column if missing
    if 'changes' not in audit_logs_columns:
        op.add_column('audit_logs', 
            sa.Column('changes', sa.JSON(), nullable=True)
        )
    
    # Add 'ip_address' column if missing
    if 'ip_address' not in audit_logs_columns:
        op.add_column('audit_logs',
            sa.Column('ip_address', sa.String(length=45), nullable=True)
        )
    
    # Add 'user_agent' column if missing
    if 'user_agent' not in audit_logs_columns:
        op.add_column('audit_logs',
            sa.Column('user_agent', sa.Text(), nullable=True)
        )


def downgrade() -> None:
    """Remove the added columns (for rollback)."""
    # Note: In production, you typically wouldn't drop these columns
    # as they contain audit data. This is provided for completeness.
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'ip_address')
    op.drop_column('audit_logs', 'changes')
