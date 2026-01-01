"""drop unique constraint on students.email

Revision ID: 4d8c7f2a9b1e
Revises: abc123def456
Create Date: 2025-11-07 21:10:00.000000

"""
from backend.strathy_app.models.models import Base
target_metadata = Base.metadata

from alembic import op

# revision identifiers, used by Alembic.
revision = "4d8c7f2a9b1e"
down_revision = "abc123def456"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE students DROP CONSTRAINT IF EXISTS students_email_key")


def downgrade():
    op.execute(
        "ALTER TABLE students ADD CONSTRAINT students_email_key UNIQUE (email)"
    )