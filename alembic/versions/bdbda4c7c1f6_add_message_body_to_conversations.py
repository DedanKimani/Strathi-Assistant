"""add message_body to conversations

Revision ID: abc123def456
Revises: <previous_revision_id>
Create Date: 2025-11-07 20:00:00.000000

"""
# add your model's MetaData object here
# for 'autogenerate' support
from backend.strathy_app.models.models import Base  # import your Base
target_metadata = Base.metadata

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abc123def456'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add message_body column to conversations table
    op.add_column(
        'conversations',
        sa.Column('message_body', sa.Text(), nullable=True)  # Text for Postgres
    )


def downgrade():
    # Remove the column if we roll back
    op.drop_column('conversations', 'message_body')
