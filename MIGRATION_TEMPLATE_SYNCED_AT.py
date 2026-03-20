"""Add synced_at timestamp to attendance table

Revision ID: add_synced_at_to_attendance
Revises: 
Create Date: 2026-03-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_synced_at_to_attendance'
down_revision = None  # Change this to the previous revision ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add synced_at column to attendance table"""
    op.add_column('attendance', sa.Column('synced_at', sa.DateTime(), nullable=True))
    
    # Create index for performance
    op.create_index(
        op.f('ix_attendance_synced_at'),
        'attendance',
        ['synced_at'],
        unique=False
    )


def downgrade() -> None:
    """Remove synced_at column from attendance table"""
    op.drop_index(op.f('ix_attendance_synced_at'), table_name='attendance')
    op.drop_column('attendance', 'synced_at')
