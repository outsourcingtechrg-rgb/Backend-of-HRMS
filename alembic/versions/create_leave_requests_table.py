"""Create leave_requests table if it doesn't exist.

Revision ID: create_leave_requests_table
Revises: 
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'create_leave_requests_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_requests' not in inspector.get_table_names():
        op.create_table(
            'leave_requests',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('employee_id', sa.Integer(), nullable=False, index=True),
            sa.Column('leave_type_id', sa.Integer(), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('days', sa.Float(), nullable=False),
            sa.Column('reason', sa.String(500), nullable=True),
            sa.Column('status', sa.String(50), nullable=False, server_default='pending', index=True),
            sa.Column('action_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
            sa.ForeignKeyConstraint(['leave_type_id'], ['leave_types.id'], ),
            sa.ForeignKeyConstraint(['action_by'], ['employees.id'], ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_requests' in inspector.get_table_names():
        op.drop_table('leave_requests')
