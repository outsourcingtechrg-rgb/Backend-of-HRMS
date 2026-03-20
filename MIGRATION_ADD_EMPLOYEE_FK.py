# """Add employee_id foreign key to attendance table

# Revision ID: add_employee_fk_to_attendance
# Revises: 
# Create Date: 2026-03-07 00:00:00.000000

# """
# from alembic import op
# import sqlalchemy as sa


# # revision identifiers, used by Alembic.
# revision = 'add_employee_fk_to_attendance'
# down_revision = None  # Change this to the previous revision ID if you have one
# branch_labels = None
# depends_on = None


# def upgrade() -> None:
#     """Add foreign key constraint to employee_id in attendance table"""
#     # First, add index if it doesn't exist
#     op.create_index(
#         op.f('ix_attendance_employee_id'),
#         'attendance',
#         ['employee_id'],
#         unique=False
#     )
    
#     # Add the foreign key constraint
#     op.create_foreign_key(
#         'fk_attendance_employee_id',
#         'attendance',
#         'employees',
#         ['employee_id'],
#         ['id'],
#         ondelete='CASCADE'
#     )


# def downgrade() -> None:
#     """Remove foreign key constraint from attendance table"""
#     op.drop_constraint('fk_attendance_employee_id', 'attendance', type_='foreignkey')
#     op.drop_index(op.f('ix_attendance_employee_id'), table_name='attendance')
