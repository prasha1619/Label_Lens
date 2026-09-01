"""add users, sessions, audit ownership and inspection ownership

Revision ID: 20260831_auth
Revises:
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa
revision = '20260831_auth'
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    op.create_table('users', sa.Column('id', sa.String(36), primary_key=True), sa.Column('full_name', sa.String(120), nullable=False), sa.Column('email', sa.String(254), nullable=False), sa.Column('password_hash', sa.String(512), nullable=False), sa.Column('organization', sa.String(160)), sa.Column('profile_photo_path', sa.String(500)), sa.Column('role', sa.String(20), nullable=False, server_default='inspector'), sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column('created_at', sa.DateTime(), nullable=False), sa.Column('updated_at', sa.DateTime(), nullable=False), sa.Column('last_login_at', sa.DateTime()))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_table('auth_sessions', sa.Column('id', sa.String(36), primary_key=True), sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False), sa.Column('token_hash', sa.String(64), nullable=False), sa.Column('expires_at', sa.DateTime(), nullable=False), sa.Column('created_at', sa.DateTime(), nullable=False), sa.Column('revoked_at', sa.DateTime()))
    op.create_index('ix_auth_sessions_token_hash', 'auth_sessions', ['token_hash'], unique=True)
    op.add_column('inspections', sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL')))
    op.create_index('ix_inspections_user_id', 'inspections', ['user_id'])
    op.add_column('audit_logs', sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL')))
def downgrade():
    op.drop_column('audit_logs', 'user_id'); op.drop_index('ix_inspections_user_id', table_name='inspections'); op.drop_column('inspections', 'user_id'); op.drop_table('auth_sessions'); op.drop_index('ix_users_email', table_name='users'); op.drop_table('users')
