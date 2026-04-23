"""Create leave_allocations table if it doesn't exist.

Revision ID: create_leave_allocations_table
Revises: 
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'create_leave_allocations_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_allocations' not in inspector.get_table_names():
        op.create_table(
            'leave_allocations',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('employee_id', sa.Integer(), nullable=False, index=True),
            sa.Column('leave_type_id', sa.Integer(), nullable=False, index=True),
            sa.Column('year', sa.Integer(), nullable=False, index=True),
            sa.Column('allocated_days', sa.Float(), nullable=False, server_default='0'),
            sa.Column('used_days', sa.Float(), nullable=False, server_default='0'),
            sa.Column('carried_forward', sa.Float(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
            sa.ForeignKeyConstraint(['leave_type_id'], ['leave_types.id'], ),
            sa.UniqueConstraint('employee_id', 'leave_type_id', 'year', name='uq_leave_allocation'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_allocations' in inspector.get_table_names():
        op.drop_table('leave_allocations')
