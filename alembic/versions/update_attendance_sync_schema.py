"""Update AttendanceSync model schema

Revision ID: update_attendance_sync_schema
Revises: 
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'update_attendance_sync_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old table if exists (in case of fresh install)
    op.execute("DROP TABLE IF EXISTS attendance_sync")
    
    # Create new attendance_sync table with updated schema
    op.create_table(
        'attendance_sync',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_ip', sa.String(255), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sync_interval_minutes', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_ip', name='uq_device_ip')
    )


def downgrade() -> None:
    op.drop_table('attendance_sync')
