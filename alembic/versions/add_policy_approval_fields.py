"""Add approval workflow fields to policies table.

Revision ID: add_approval_fields_policy
Revises: 
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_approval_fields_policy'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'policies' not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("policies")
    }
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("policies")
    }
    existing_fks = {
        fk.get("name") for fk in inspector.get_foreign_keys("policies") if fk.get("name")
    }

    if 'approved_by' not in existing_columns:
        op.add_column('policies', sa.Column('approved_by', sa.Integer(), nullable=True))
        existing_columns.add('approved_by')

    if 'approved_at' not in existing_columns:
        op.add_column('policies', sa.Column('approved_at', sa.DateTime(), nullable=True))

    if 'approval_note' not in existing_columns:
        op.add_column('policies', sa.Column('approval_note', sa.Text(), nullable=True))

    if 'submitted_for_review_at' not in existing_columns:
        op.add_column('policies', sa.Column('submitted_for_review_at', sa.DateTime(), nullable=True))

    if 'approved_by' in existing_columns and 'fk_policies_approved_by_employees' not in existing_fks:
        op.create_foreign_key(
            'fk_policies_approved_by_employees',
            'policies',
            'employees',
            ['approved_by'],
            ['id'],
            ondelete='SET NULL',
        )

    if 'ix_policies_approved_by' not in existing_indexes:
        op.create_index('ix_policies_approved_by', 'policies', ['approved_by'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'policies' not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("policies")
    }
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("policies")
    }
    existing_fks = {
        fk.get("name") for fk in inspector.get_foreign_keys("policies") if fk.get("name")
    }

    if 'ix_policies_approved_by' in existing_indexes:
        op.drop_index('ix_policies_approved_by', table_name='policies')

    if 'fk_policies_approved_by_employees' in existing_fks:
        op.drop_constraint('fk_policies_approved_by_employees', 'policies', type_='foreignkey')

    if 'submitted_for_review_at' in existing_columns:
        op.drop_column('policies', 'submitted_for_review_at')

    if 'approval_note' in existing_columns:
        op.drop_column('policies', 'approval_note')

    if 'approved_at' in existing_columns:
        op.drop_column('policies', 'approved_at')

    if 'approved_by' in existing_columns:
        op.drop_column('policies', 'approved_by')
