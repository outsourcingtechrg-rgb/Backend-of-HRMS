"""
alembic_migration_policy_approval.py

Alembic migration — add CEO approval columns to policies table.

Run with:
    alembic revision --autogenerate -m "add_policy_approval_workflow"
    alembic upgrade head

Or apply manually with the SQL below.

───────────────────────────────────────────────────────────────
Manual SQL (PostgreSQL):
───────────────────────────────────────────────────────────────
ALTER TABLE policies
  ADD COLUMN IF NOT EXISTS approved_by              INTEGER REFERENCES employees(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS approved_at              TIMESTAMP,
  ADD COLUMN IF NOT EXISTS approval_note            TEXT,
  ADD COLUMN IF NOT EXISTS submitted_for_review_at  TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_policies_approved_by ON policies(approved_by);
───────────────────────────────────────────────────────────────
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        "policies",
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("policies", sa.Column("approved_at",           sa.DateTime(), nullable=True))
    op.add_column("policies", sa.Column("approval_note",         sa.Text(),     nullable=True))
    op.add_column("policies", sa.Column("submitted_for_review_at", sa.DateTime(), nullable=True))
    op.create_index("ix_policies_approved_by", "policies", ["approved_by"])


def downgrade():
    op.drop_index("ix_policies_approved_by", table_name="policies")
    op.drop_column("policies", "submitted_for_review_at")
    op.drop_column("policies", "approval_note")
    op.drop_column("policies", "approved_at")
    op.drop_column("policies", "approved_by")
