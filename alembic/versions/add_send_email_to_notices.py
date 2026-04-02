"""Add send_email field to notices table for email notifications.

Revision ID: add_send_email_notices
Revises: 
Create Date: 2026-04-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_send_email_notices'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'notices' not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("notices")
    }

    if 'send_email' not in existing_columns:
        op.add_column('notices', sa.Column('send_email', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'notices' not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("notices")
    }

    if 'send_email' in existing_columns:
        op.drop_column('notices', 'send_email')
