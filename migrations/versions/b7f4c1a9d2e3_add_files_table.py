"""add files table

Revision ID: b7f4c1a9d2e3
Revises: 7358a6a3e2a4
Create Date: 2026-07-04 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f4c1a9d2e3'
down_revision: Union[str, Sequence[str], None] = '7358a6a3e2a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('object_key', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=150), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_files_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_files_owner_id'), ['owner_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_files_display_name'), ['display_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_files_object_key'), ['object_key'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_files_object_key'))
        batch_op.drop_index(batch_op.f('ix_files_display_name'))
        batch_op.drop_index(batch_op.f('ix_files_owner_id'))
        batch_op.drop_index(batch_op.f('ix_files_id'))
    op.drop_table('files')
