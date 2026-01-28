#!/usr/bin/env python3
"""
User Authentication Commands
Commands for managing user accounts with QERDS authentication.
"""

import click
import os
from typing import Optional

from gtasks_cli.utils.logger import setup_logger
from gtasks_cli.services.auth_service import get_auth_service, AuthenticationError

# Set up logger
logger = setup_logger(__name__)


def get_user_display(user) -> str:
    """Format user for display."""
    if not user:
        return "Not logged in"
    return f"{user.display_name} ({user.email})"


@click.group()
def user():
    """User authentication and account management commands."""
    pass


@user.command()
@click.argument('token', type=str, required=False)
@click.option('--dummy', '-d', is_flag=True, help='Use dummy authentication for testing')
@click.option('--session', '-s', is_flag=True, help='Create a session after login')
def login(token: Optional[str], dummy: bool, session: bool):
    """
    Login with QERDS authentication token.
    
    If no token is provided, you will be prompted to enter it.
    
    Example:
        gtasks user login YOUR_QERDS_TOKEN
        gtasks user login --dummy  # For testing without real QERDS account
    """
    from gtasks_cli.services.qerds_api import get_qerds_client
    
    # Use dummy token if --dummy flag is set
    if dummy:
        token = "demo_token_123"
    
    # Get token from prompt if not provided
    if not token:
        token = click.prompt('Enter your QERDS authentication token', hide_input=True)
    
    # Create auth service
    auth_service = get_auth_service()
    
    # Use dummy client if requested
    if dummy:
        from gtasks_cli.services.qerds_api import QerdsApiClient
        from gtasks_cli.services.auth_service import AuthService
        qerds_client = QerdsApiClient(use_dummy_fallback=True)
        auth_service = AuthService(qerds_client=qerds_client)
    
    try:
        # Perform login
        success, user, message = auth_service.login(token)
        
        if success and user:
            click.echo(f"✅ {message}")
            click.echo(f"   User ID: {user.user_id}")
            click.echo(f"   Email: {user.email}")
            click.echo(f"   Display Name: {user.display_name}")
            
            # Create session if requested
            if session:
                session_obj = auth_service.create_session(user.user_id)
                click.echo(f"\n📝 Session created:")
                click.echo(f"   Session ID: {session_obj.session_id}")
                click.echo(f"   Expires: {session_obj.expires_at}")
            
            # Store session info for parent context
            ctx = click.get_current_context()
            ctx.obj = {'user': user, 'session': auth_service.create_session(user.user_id) if session else None}
        else:
            click.echo(f"❌ {message}")
            exit(1)
            
    except AuthenticationError as e:
        click.echo(f"❌ Authentication failed: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Login error: {e}")
        click.echo(f"❌ An unexpected error occurred during login")
        exit(1)


@user.command()
@click.option('--all', '-a', is_flag=True, help='Logout from all sessions')
def logout(all: bool):
    """
    Logout from your account.
    
    This invalidates your current session. If you want to logout
    from all devices, use the --all flag.
    
    Example:
        gtasks user logout
        gtasks user logout --all
    """
    auth_service = get_auth_service()
    
    # Get current session from context if available
    ctx = click.get_current_context()
    session_id = None
    
    if ctx.obj and 'session' in ctx.obj:
        session_id = ctx.obj['session'].session_id if ctx.obj['session'] else None
    
    if session_id:
        success, message = auth_service.logout(session_id)
        if success:
            click.echo(f"✅ {message}")
        else:
            click.echo(f"⚠️ {message}")
    
    # Logout from all sessions if requested
    if all:
        # Get all users and logout their sessions
        users = auth_service.get_all_users()
        for user in users:
            success, msg = auth_service.logout_all_sessions(user.user_id)
            if success and "No active sessions" not in msg:
                click.echo(f"🔓 Logged out from {user.display_name}'s sessions")
    
    click.echo("✅ You have been logged out.")


@user.command()
def status():
    """
    Check authentication status.
    
    Shows whether you are currently logged in and your session details.
    
    Example:
        gtasks user status
    """
    auth_service = get_auth_service()
    
    # Try to get current session from context
    ctx = click.get_current_context()
    
    if ctx.obj and 'session' in ctx.obj and ctx.obj['session']:
        session = ctx.obj['session']
        valid, user, message = auth_service.validate_session(session.session_id)
        
        if valid and user:
            click.echo("✅ You are logged in")
            click.echo(f"\n👤 User: {get_user_display(user)}")
            click.echo(f"🆔 User ID: {user.user_id}")
            click.echo(f"📧 Email: {user.email}")
            click.echo(f"📅 Created: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
            if user.last_login:
                click.echo(f"🕐 Last login: {user.last_login.strftime('%Y-%m-%d %H:%M')}")
            click.echo(f"\n🔑 Session valid until: {session.expires_at}")
            return
    
    # Check if any sessions exist
    users = auth_service.get_all_users()
    if users:
        click.echo(f"⚠️ You have {len(users)} account(s) but no active session.")
        click.echo("Run 'gtasks user login' to create a new session.")
        for user in users:
            click.echo(f"   - {get_user_display(user)}")
    else:
        click.echo("❌ You are not logged in.")
        click.echo("Run 'gtasks user login YOUR_TOKEN' to authenticate.")


@user.command()
def whoami():
    """
    Display current user information.
    
    Shows who you are currently logged in as.
    
    Example:
        gtasks user whoami
    """
    auth_service = get_auth_service()
    
    # Try to get user from context
    ctx = click.get_current_context()
    
    user = None
    if ctx.obj and 'user' in ctx.obj:
        user = ctx.obj['user']
    
    if not user:
        # Try to find any logged in user by checking sessions
        users = auth_service.get_all_users()
        if users:
            # Get the most recently active user
            user = max(users, key=lambda u: u.last_login or u.created_at)
    
    if user:
        click.echo(f"👤 {user.display_name}")
        click.echo(f"   Email: {user.email}")
        click.echo(f"   User ID: {user.user_id}")
    else:
        click.echo("You are not logged in.")
        click.echo("Run 'gtasks user login YOUR_TOKEN' to authenticate.")


@user.command()
@click.argument('user_id', type=str, required=False)
def deactivate(user_id: Optional[str]):
    """
    Deactivate your account.
    
    This will deactivate your account and logout from all sessions.
    Your data will be preserved but you won't be able to login.
    
    Example:
        gtasks user deactivate
        gtasks user deactivate abc12345  # Admin can deactivate other users
    """
    auth_service = get_auth_service()
    
    # Get current user if no user_id provided
    if not user_id:
        ctx = click.get_current_context()
        if ctx.obj and 'user' in ctx.obj:
            user_id = ctx.obj['user'].user_id
        else:
            click.echo("❌ Please provide a user ID or login first")
            exit(1)
    
    # Confirm deactivation
    if not click.confirm("Are you sure you want to deactivate this account?"):
        click.echo("Cancelled.")
        return
    
    success, message = auth_service.deactivate_user(user_id)
    
    if success:
        click.echo(f"✅ {message}")
        click.echo("Your account has been deactivated. You can reactivate by logging in again.")
    else:
        click.echo(f"❌ {message}")
        exit(1)


@user.command()
def list():
    """
    List all registered users (admin command).
    
    Shows all users who have registered with the system.
    
    Example:
        gtasks user list
    """
    auth_service = get_auth_service()
    
    users = auth_service.get_all_users()
    
    if not users:
        click.echo("No users registered yet.")
        return
    
    click.echo(f"Registered users ({len(users)}):")
    click.echo("-" * 60)
    
    for user in users:
        status = "🟢 Active" if user.is_active else "🔴 Inactive"
        last_login = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else "Never"
        click.echo(f"{user.user_id} | {user.email} | {status} | Last login: {last_login}")


if __name__ == "__main__":
    user()
