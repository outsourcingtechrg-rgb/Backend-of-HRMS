"""Update employees table FK constraints to allow deletion

Revision ID: update_employee_fk_constraints
Revises: 
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'update_employee_fk_constraints'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing foreign key constraints
    op.drop_constraint('employees_ibfk_1', 'employees', type_='foreignkey')  # role_id
    op.drop_constraint('employees_ibfk_2', 'employees', type_='foreignkey')  # department_id
    op.drop_constraint('employees_ibfk_3', 'employees', type_='foreignkey')  # shift_id
    
    # Change columns to nullable
    op.alter_column('employees', 'role_id', existing_type=sa.Integer(), nullable=True)
    op.alter_column('employees', 'department_id', existing_type=sa.Integer(), nullable=True)
    op.alter_column('employees', 'shift_id', existing_type=sa.Integer(), nullable=True)
    
    # Re-create foreign key constraints with SET NULL
    op.create_foreign_key(
        'employees_ibfk_1',
        'employees', 'roles',
        ['role_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'employees_ibfk_2',
        'employees', 'departments',
        ['department_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'employees_ibfk_3',
        'employees', 'shifts',
        ['shift_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop the new constraints
    op.drop_constraint('employees_ibfk_1', 'employees', type_='foreignkey')
    op.drop_constraint('employees_ibfk_2', 'employees', type_='foreignkey')
    op.drop_constraint('employees_ibfk_3', 'employees', type_='foreignkey')
    
    # Change columns back to NOT NULL
    op.alter_column('employees', 'role_id', existing_type=sa.Integer(), nullable=False)
    op.alter_column('employees', 'department_id', existing_type=sa.Integer(), nullable=False)
    op.alter_column('employees', 'shift_id', existing_type=sa.Integer(), nullable=False)
    
    # Re-create foreign key constraints with RESTRICT
    op.create_foreign_key(
        'employees_ibfk_1',
        'employees', 'roles',
        ['role_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'employees_ibfk_2',
        'employees', 'departments',
        ['department_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'employees_ibfk_3',
        'employees', 'shifts',
        ['shift_id'], ['id'],
        ondelete='RESTRICT'
    )
