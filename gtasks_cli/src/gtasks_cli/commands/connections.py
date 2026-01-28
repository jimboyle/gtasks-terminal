"""
Connection Management Commands

Commands for managing user connections and invitations:
- gtasks connections list - List all connections
- gtasks connections pending - List pending invitations
- gtasks connections accept <invitation_id> - Accept an invitation
- gtasks connections reject <invitation_id> - Reject an invitation
- gtasks connections remove <connection_id> - Remove a connection
- gtasks connections sent - List sent invitations
"""

import click
from typing import Optional
from pathlib import Path

from ..services.invitation_workflow_manager import (
    InvitationWorkflowManager,
    InvitationRequest
)
from ..services.shared_task_access_service import SharedTaskAccessService


@click.group()
def connections():
    """Manage user connections and invitations"""
    pass


@connections.command('list')
@click.option('--user-id', '-u', default=None, help='User ID to list connections for (defaults to current user)')
def list_connections(user_id: Optional[str]):
    """List all connections for a user"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    workflow_manager = InvitationWorkflowManager()
    sent_invitations = workflow_manager.get_sent_invitations(user_id)
    
    click.echo(f"\n📋 Connections for user: {user_id}")
    click.echo("=" * 60)
    
    if not sent_invitations:
        click.echo("No connections or invitations found.")
        click.echo("\nTo connect with other users:")
        click.echo("1. Create tasks with [@account] tags")
        click.echo("2. When they login, they can accept your invitation")
    else:
        # Group by status
        pending = [i for i in sent_invitations if i['status'] == 'pending']
        accepted = [i for i in sent_invitations if i['status'] == 'accepted']
        other = [i for i in sent_invitations if i['status'] not in ['pending', 'accepted']]
        
        if pending:
            click.echo(f"\n⏳ Pending Invitations ({len(pending)}):")
            for inv in pending:
                click.echo(f"  • {inv['to_email']} - Sent {inv['created_at'][:10]}")
        
        if accepted:
            click.echo(f"\n✅ Connected Users ({len(accepted)}):")
            for inv in accepted:
                click.echo(f"  • {inv['to_email']} - Connected {inv['responded_at'][:10] if inv.get('responded_at') else 'N/A'}")
        
        if other:
            click.echo(f"\n📋 Other ({len(other)}):")
            for inv in other:
                click.echo(f"  • {inv['to_email']} - {inv['status']}")


@connections.command('pending')
@click.option('--email', '-e', default=None, help='Email to check pending invitations for')
def pending_invitations(email: Optional[str]):
    """List pending invitations for a user"""
    if not email:
        user_info = _get_current_user_info()
        if not user_info:
            click.echo("Error: No user logged in. Please login first.")
            return
        email = user_info.get('email')
    
    workflow_manager = InvitationWorkflowManager()
    invitations = workflow_manager.get_pending_invitations_for_user(email)
    
    click.echo(f"\n📬 Pending Invitations for {email}:")
    click.echo("=" * 60)
    
    if not invitations:
        click.echo("No pending invitations.")
        click.echo("\nIf someone shared a task with you, check your email for an invitation.")
    else:
        for inv in invitations:
            click.echo(f"\n  From: {inv['from_user_email']}")
            click.echo(f"  Sent: {inv['created_at'][:10]}")
            if inv.get('task_title'):
                click.echo(f"  Task: {inv['task_title']}")
            if inv.get('message'):
                click.echo(f"  Message: {inv['message']}")
            click.echo(f"  ID: {inv['id']}")
            click.echo(f"  Expires: {inv['expires_at'][:10]}")


@connections.command('accept')
@click.argument('invitation_id')
@click.option('--user-id', '-u', default=None, help='User ID accepting the invitation')
@click.option('--email', '-e', default=None, help='Email of the user accepting')
def accept_invitation(invitation_id: str, user_id: Optional[str], email: Optional[str]):
    """Accept an invitation"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    if not email:
        user_info = _get_current_user_info()
        if user_info:
            email = user_info.get('email')
    
    if not email:
        email = click.prompt("Enter your email address")
    
    workflow_manager = InvitationWorkflowManager()
    result = workflow_manager.process_acceptance(invitation_id, user_id, email)
    
    if result.success:
        click.echo(f"\n✅ Connection created successfully!")
        click.echo(f"Connection ID: {result.connection_id}")
        click.echo(f"\nYou can now:")
        click.echo("  • View shared tasks")
        click.echo("  • Complete tasks shared with you")
        click.echo("  • See who shared tasks with you")
    else:
        click.echo(f"\n❌ Failed to accept invitation: {result.message}")


@connections.command('reject')
@click.argument('invitation_id')
@click.option('--user-id', '-u', default=None, help='User ID rejecting the invitation')
def reject_invitation(invitation_id: str, user_id: Optional[str]):
    """Reject an invitation"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    workflow_manager = InvitationWorkflowManager()
    result = workflow_manager.process_rejection(invitation_id, user_id)
    
    if result['success']:
        click.echo("\n✅ Invitation rejected.")
    else:
        click.echo(f"\n❌ Failed to reject invitation: {result['message']}")


@connections.command('remove')
@click.argument('connection_id')
@click.option('--user-id', '-u', default=None, help='User ID removing the connection')
def remove_connection(connection_id: str, user_id: Optional[str]):
    """Remove a connection"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    click.echo(f"\n🗑️ Removing connection {connection_id}")
    click.echo("Note: This will not delete shared tasks, but you won't see new updates.")
    
    if click.confirm("Are you sure?"):
        # TODO: Implement connection removal
        click.echo("Connection removal not yet implemented.")


@connections.command('sent')
@click.option('--user-id', '-u', default=None, help='User ID to list sent invitations for')
def sent_invitations(user_id: Optional[str]):
    """List all invitations sent by a user"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    workflow_manager = InvitationWorkflowManager()
    invitations = workflow_manager.get_sent_invitations(user_id)
    
    click.echo(f"\n📤 Invitations sent by {user_id}:")
    click.echo("=" * 60)
    
    if not invitations:
        click.echo("No invitations sent yet.")
        click.echo("\nTo invite someone:")
        click.echo("1. Create a task with [@email] tag")
        click.echo("2. The user will receive an email invitation")
    else:
        # Group by status
        pending = [i for i in invitations if i['status'] == 'pending']
        accepted = [i for i in invitations if i['status'] == 'accepted']
        rejected = [i for i in invitations if i['status'] == 'rejected']
        other = [i for i in invitations if i['status'] not in ['pending', 'accepted', 'rejected']]
        
        if pending:
            click.echo(f"\n⏳ Awaiting Response ({len(pending)}):")
            for inv in pending:
                click.echo(f"  • To: {inv['to_email']} - Sent {inv['created_at'][:10]}")
        
        if accepted:
            click.echo(f"\n✅ Accepted ({len(accepted)}):")
            for inv in accepted:
                click.echo(f"  • To: {inv['to_email']} - Connected {inv['responded_at'][:10] if inv.get('responded_at') else 'N/A'}")
        
        if rejected:
            click.echo(f"\n❌ Rejected ({len(rejected)}):")
            for inv in rejected:
                click.echo(f"  • To: {inv['to_email']} - Rejected {inv['responded_at'][:10] if inv.get('responded_at') else 'N/A'}")
        
        if other:
            click.echo(f"\n📋 Other ({len(other)}):")
            for inv in other:
                click.echo(f"  • To: {inv['to_email']} - {inv['status']}")


def _get_current_user_id() -> Optional[str]:
    """Get current logged in user ID"""
    try:
        from ..storage.config_manager import ConfigManager
        config = ConfigManager()
        user_config = config.get_user_config()
        return user_config.get('user_id') if user_config else None
    except Exception:
        return None


def _get_current_user_info() -> Optional[dict]:
    """Get current logged in user info"""
    try:
        from ..storage.config_manager import ConfigManager
        config = ConfigManager()
        user_config = config.get_user_config()
        return user_config if user_config else None
    except Exception:
        return None
