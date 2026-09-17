"""add refresh_tokens table and ensure audit_logs.changes column

Revision ID: 003
Revises: 002
Create Date: 2026-09-17 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if audit_logs.changes column exists, add it if not
    # This handles databases created by create_all() from older model versions
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    audit_logs_columns = [col['name'] for col in inspector.get_columns('audit_logs')]
    
    if 'changes' not in audit_logs_columns:
        op.add_column('audit_logs', 
            sa.Column('changes', sa.JSON(), nullable=True)
        )
    
    # Create refresh_tokens table for Phase 14 authentication hardening
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('replaced_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_refresh_tokens_token_hash')
    )
    
    # Create indexes for refresh_tokens
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'], unique=False)
    op.create_index('ix_refresh_tokens_revoked', 'refresh_tokens', ['revoked'], unique=False)


def downgrade() -> None:
    # Drop refresh_tokens indexes
    op.drop_index('ix_refresh_tokens_revoked', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    
    # Drop refresh_tokens table
    op.drop_table('refresh_tokens')
    
    # Note: We don't drop the audit_logs.changes column in downgrade
    # because it was part of the original schema in migration 001
    # This migration only ensures it exists for databases that were
    # created before migration 001 was finalized
