"""Add missing columns to leave_types table.

Revision ID: add_leave_types_columns
Revises: 
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_leave_types_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_types' not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("leave_types")
    }

    # Add code column if missing
    if 'code' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('code', sa.String(255), nullable=True, unique=True)
        )

    # Add max_carry_forward if missing
    if 'max_carry_forward' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('max_carry_forward', sa.Float(), nullable=True)
        )

    # Add allow_negative_balance if missing
    if 'allow_negative_balance' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('allow_negative_balance', sa.Boolean(), nullable=False, server_default='0')
        )

    # Add gender_specific if missing
    if 'gender_specific' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('gender_specific', sa.String(255), nullable=True)
        )

    # Add reset_month if missing
    if 'reset_month' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('reset_month', sa.Integer(), nullable=True)
        )

    # Add min_days if missing
    if 'min_days' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('min_days', sa.Float(), nullable=True)
        )

    # Add max_days_per_request if missing
    if 'max_days_per_request' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('max_days_per_request', sa.Float(), nullable=True)
        )

    # Add extradata if missing
    if 'extradata' not in existing_columns:
        op.add_column(
            'leave_types',
            sa.Column('extradata', sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'leave_types' not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("leave_types")
    }

    # Drop columns if they exist
    columns_to_drop = [
        'code', 'max_carry_forward', 'allow_negative_balance',
        'gender_specific', 'reset_month', 'min_days',
        'max_days_per_request', 'extradata'
    ]

    for col in columns_to_drop:
        if col in existing_columns:
            op.drop_column('leave_types', col)
