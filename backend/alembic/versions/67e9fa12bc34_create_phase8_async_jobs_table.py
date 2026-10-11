"""create_phase8_async_jobs_table

Revision ID: 67e9fa12bc34
Revises: 56d8da5f509c
Create Date: 2026-10-11 03:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67e9fa12bc34'
down_revision: Union[str, Sequence[str], None] = '56d8da5f509c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include async_jobs table for Phase 8 background processing."""
    op.create_table(
        'async_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('job_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('asset_id', sa.BigInteger(), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('async_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_async_jobs_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_async_jobs_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_async_jobs_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_async_jobs_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('async_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_async_jobs_created_at'))
        batch_op.drop_index(batch_op.f('ix_async_jobs_asset_id'))
        batch_op.drop_index(batch_op.f('ix_async_jobs_status'))
        batch_op.drop_index(batch_op.f('ix_async_jobs_user_id'))
    op.drop_table('async_jobs')
