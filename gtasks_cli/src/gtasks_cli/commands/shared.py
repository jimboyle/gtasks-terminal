"""
Shared Tasks Commands

Commands for viewing and managing shared tasks:
- gtasks shared list - List tasks shared with you
- gtasks shared by-me - List tasks you've shared with others
- gtasks shared complete <task_id> - Mark a shared task as complete
- gtasks shared stats - Show statistics about shared tasks
"""

import click
from typing import Optional
from datetime import datetime

from ..services.shared_task_access_service import (
    SharedTaskAccessService,
    SharedTaskInfo
)


@click.group()
def shared():
    """Manage shared tasks"""
    pass


@shared.command('list')
@click.option('--user-id', '-u', default=None, help='User ID to list shared tasks for')
@click.option('--status', '-s', type=click.Choice(['all', 'pending', 'completed']), 
              default='all', help='Filter by completion status')
def list_shared_tasks(user_id: Optional[str], status: str):
    """List tasks that have been shared with you"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    user_info = _get_current_user_info()
    user_email = user_info.get('email') if user_info else None
    
    access_service = SharedTaskAccessService()
    tasks = access_service.get_shared_tasks_for_user(user_id, user_email)
    
    click.echo(f"\n📤 Tasks Shared With You:")
    click.echo("=" * 80)
    
    if not tasks:
        click.echo("No tasks have been shared with you.")
        click.echo("\nTo receive shared tasks:")
        click.echo("1. Others need to add [@your_account] tags to their tasks")
        click.echo("2. They will send you an invitation")
        click.echo("3. You need to accept the invitation")
    else:
        # Filter by status
        if status != 'all':
            tasks = [t for t in tasks if t.completion_status == status]
        
        if not tasks:
            click.echo(f"No tasks with status '{status}'.")
        else:
            for task in tasks:
                status_icon = "✅" if task.completion_status == 'completed' else "⏳"
                click.echo(f"\n{status_icon} {task.task_title}")
                click.echo(f"   From account: {task.original_account_id}")
                click.echo(f"   Shared: {task.shared_at[:10]}")
                click.echo(f"   Task ID: {task.task_id}")
                
                if task.task_data and task.task_data.get('due'):
                    click.echo(f"   Due: {task.task_data['due']}")
        
        click.echo(f"\n📊 Total: {len(tasks)} tasks")


@shared.command('by-me')
@click.option('--user-id', '-u', default=None, help='User ID to list shared tasks for')
def list_shared_by_me(user_id: Optional[str]):
    """List tasks that you have shared with others"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    access_service = SharedTaskAccessService()
    tasks = access_service.get_tasks_shared_by_user(user_id)
    
    click.echo(f"\n📤 Tasks You've Shared:")
    click.echo("=" * 80)
    
    if not tasks:
        click.echo("You haven't shared any tasks yet.")
        click.echo("\nTo share a task:")
        click.echo("1. Create a task with [@other_account] tag")
        click.echo("2. The other user will receive an invitation")
        click.echo("3. Once they accept, they can see and complete the task")
    else:
        for task in tasks:
            shared_accounts = task.get('shared_accounts', [])
            click.echo(f"\n📌 {task.get('title', 'Untitled')}")
            click.echo(f"   Shared with: {', '.join(shared_accounts)}")
            click.echo(f"   Task ID: {task.get('task_id')}")
            
            if task.get('due'):
                click.echo(f"   Due: {task['due']}")
        
        click.echo(f"\n📊 Total: {len(tasks)} tasks shared")


@shared.command('complete')
@click.argument('task_id')
@click.option('--account', '-a', default=None, help='Original account where task was created')
@click.option('--user-id', '-u', default=None, help='User ID completing the task')
def complete_shared_task(task_id: str, account: Optional[str], user_id: Optional[str]):
    """Mark a shared task as complete"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    if not account:
        # Try to detect account from task ID or ask user
        account = click.prompt("Enter the original account ID (where task was created)")
    
    access_service = SharedTaskAccessService()
    result = access_service.mark_task_complete(user_id, task_id, account)
    
    if result['success']:
        click.echo(f"\n✅ Task marked as complete!")
        click.echo("The task owner will be notified of your completion.")
    else:
        click.echo(f"\n❌ Failed to complete task: {result['message']}")


@shared.command('status')
@click.argument('task_id')
@click.option('--account', '-a', default=None, help='Original account where task was created')
def task_completion_status(task_id: str, account: Optional[str]):
    """Check completion status of a shared task"""
    if not account:
        account = click.prompt("Enter the original account ID (where task was created)")
    
    access_service = SharedTaskAccessService()
    statuses = access_service.get_completion_status(task_id, account)
    
    click.echo(f"\n📊 Completion Status for Task {task_id}:")
    click.echo("=" * 60)
    
    if not statuses:
        click.echo("No completion records found.")
    else:
        for status in statuses:
            icon = "✅" if status.status == 'completed' else "⏳"
            completed_at = status.completed_at[:10] if status.completed_at else "N/A"
            click.echo(f"{icon} {status.user_email}: {status.status} (completed: {completed_at})")


@shared.command('stats')
@click.option('--user-id', '-u', default=None, help='User ID to show stats for')
def shared_tasks_stats(user_id: Optional[str]):
    """Show statistics about shared tasks"""
    if not user_id:
        user_id = _get_current_user_id()
        if not user_id:
            click.echo("Error: No user logged in. Please login first.")
            return
    
    access_service = SharedTaskAccessService()
    stats = access_service.get_statistics(user_id)
    
    click.echo(f"\n📊 Shared Tasks Statistics:")
    click.echo("=" * 60)
    click.echo(f"Tasks shared with you: {stats['shared_with_me_count']}")
    click.echo(f"Tasks you've shared: {stats['shared_by_me_count']}")
    click.echo(f"Pending completion: {stats['pending_completion']}")
    click.echo(f"Completed: {stats['completed']}")
    click.echo(f"Unique accounts shared with: {stats['total_accounts_shared_with']}")


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
