"""Add leave attachments support to database

Revision ID: add_leave_attachments
Revises: 
Create Date: 2024-04-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func


# revision identifiers, used by Alembic.
revision = 'add_leave_attachments'
down_revision = None  # Change this to the previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    """Add leave attachment columns and tables"""
    
    # Add columns to leave_types table
    op.add_column(
        'leave_types',
        sa.Column('requires_document', sa.Boolean(), nullable=False, server_default='0')
    )
    op.add_column(
        'leave_types',
        sa.Column('document_description', sa.Text(), nullable=True)
    )
    op.add_column(
        'leave_types',
        sa.Column('allowed_file_types', sa.String(255), nullable=False, server_default='pdf,jpg,png,doc,docx')
    )
    
    # Create leave_attachments table
    op.create_table(
        'leave_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        
        # File information
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_extension', sa.String(20), nullable=True),
        
        # Metadata
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
        
        # Constraints
        sa.ForeignKeyConstraint(['transaction_id'], ['leave_transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_leave_attachments_transaction_id', 'transaction_id'),
        sa.Index('ix_leave_attachments_uploaded_by', 'uploaded_by'),
    )


def downgrade():
    """Revert changes"""
    
    # Drop leave_attachments table
    op.drop_table('leave_attachments')
    
    # Drop columns from leave_types table
    op.drop_column('leave_types', 'allowed_file_types')
    op.drop_column('leave_types', 'document_description')
    op.drop_column('leave_types', 'requires_document')
