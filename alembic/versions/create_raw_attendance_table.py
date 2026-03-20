"""Create raw_attendance table for unlinked ZKT data

Revision ID: create_raw_attendance_table
Revises: 
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'create_raw_attendance_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create raw_attendance table
    op.create_table(
        'raw_attendance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('machine_user_id', sa.Integer(), nullable=False),
        sa.Column('employee_name', sa.String(255), nullable=True),
        sa.Column('attendance_date', sa.Date(), nullable=False),
        sa.Column('attendance_time', sa.Time(), nullable=False),
        sa.Column('punch', sa.Boolean(), nullable=False),
        sa.Column('attendance_mode', sa.String(50), nullable=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('ip_address', sa.String(255), nullable=True),
        sa.Column('device_serial', sa.String(255), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('linked_at', sa.DateTime(), nullable=True),
        sa.Column('linked_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('machine_user_id', 'attendance_date', 'attendance_time', name='uq_machine_attendance_time')
    )
    
    # Create indexes
    op.create_index('ix_raw_attendance_machine_user_id', 'raw_attendance', ['machine_user_id'])
    op.create_index('ix_raw_attendance_attendance_date', 'raw_attendance', ['attendance_date'])
    op.create_index('ix_raw_attendance_employee_id', 'raw_attendance', ['employee_id'])


def downgrade() -> None:
    op.drop_index('ix_raw_attendance_employee_id', table_name='raw_attendance')
    op.drop_index('ix_raw_attendance_attendance_date', table_name='raw_attendance')
    op.drop_index('ix_raw_attendance_machine_user_id', table_name='raw_attendance')
    op.drop_table('raw_attendance')
