"""Create leave_transactions table if it doesn't exist.

Revision ID: create_leave_transactions_table
Revises: 
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'create_leave_transactions_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_transactions' not in inspector.get_table_names():
        op.create_table(
            'leave_transactions',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('employee_id', sa.Integer(), nullable=False, index=True),
            sa.Column('leave_type_id', sa.Integer(), nullable=False),
            sa.Column('leave_request_id', sa.Integer(), nullable=True),
            sa.Column('days', sa.Float(), nullable=False),
            sa.Column('type', sa.String(50), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
            sa.ForeignKeyConstraint(['leave_type_id'], ['leave_types.id'], ),
            sa.ForeignKeyConstraint(['leave_request_id'], ['leave_requests.id'], ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_transactions' in inspector.get_table_names():
        op.drop_table('leave_transactions')
