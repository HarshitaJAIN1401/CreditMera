"""add_international_case_management_and_passport

Revision ID: 78fa0b34de56
Revises: 67e9fa12bc34
Create Date: 2026-10-11 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78fa0b34de56'
down_revision: Union[str, Sequence[str], None] = '67e9fa12bc34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add passport metadata to registered_assets and create global_cases table."""
    # 1. Add international passport columns to registered_assets
    with op.batch_alter_table('registered_assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.String(length=64), server_default='Other', nullable=True))
        batch_op.add_column(sa.Column('country', sa.String(length=64), server_default='International', nullable=True))
        batch_op.add_column(sa.Column('license_type', sa.String(length=64), server_default='All Rights Reserved', nullable=True))
        batch_op.add_column(sa.Column('attribution_text', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('perceptual_hash', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_registered_assets_perceptual_hash'), ['perceptual_hash'], unique=False)

    # 2. Create global_cases table for cross-border image misuse tracking
    op.create_table(
        'global_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_number', sa.String(length=64), nullable=False),
        sa.Column('reporter_id', sa.String(length=36), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('suspected_image_path', sa.String(length=512), nullable=True),
        sa.Column('suspected_url', sa.String(length=512), nullable=True),
        sa.Column('suspected_country', sa.String(length=64), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('watermark_status', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='New', nullable=False),
        sa.Column('evidence_notes', sa.Text(), nullable=True),
        sa.Column('timeline_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['registered_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('global_cases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_global_cases_case_number'), ['case_number'], unique=True)
        batch_op.create_index(batch_op.f('ix_global_cases_reporter_id'), ['reporter_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_global_cases_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_global_cases_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_global_cases_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('global_cases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_global_cases_created_at'))
        batch_op.drop_index(batch_op.f('ix_global_cases_status'))
        batch_op.drop_index(batch_op.f('ix_global_cases_asset_id'))
        batch_op.drop_index(batch_op.f('ix_global_cases_reporter_id'))
        batch_op.drop_index(batch_op.f('ix_global_cases_case_number'))
    op.drop_table('global_cases')

    with op.batch_alter_table('registered_assets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_registered_assets_perceptual_hash'))
        batch_op.drop_column('perceptual_hash')
        batch_op.drop_column('attribution_text')
        batch_op.drop_column('license_type')
        batch_op.drop_column('country')
        batch_op.drop_column('category')
