"""
API Routes
"""
from flask import Blueprint, jsonify, request, session
from services.data_manager import DataManager
import threading
import traceback
import uuid
import re
from datetime import datetime
from pathlib import Path

api = Blueprint('api', __name__)
data_manager = DataManager()

# In-memory state
_dashboard_state = {
    'tasks': {},
    'accounts': [],
    'current_account': None,
    'stats': {}
}

# Background sync lock to prevent concurrent Google sync
_sync_lock = threading.Lock()


def extract_tags_from_task(task) -> set:
    """
    Extract tags from a task (supports both Task object and dict).
    This includes:
    1. Tags from the structured 'tags' field
    2. Tags from the hybrid_tags.bracket array
    3. Tags from the description in [tagname] format
    4. Account tags from description in [@account] format
    
    Args:
        task: Task object or dictionary
        
    Returns:
        Set of tag strings
    """
    tags_set = set()
    
    # 1. Extract tags from structured 'tags' field
    tags = getattr(task, 'tags', [])
    if isinstance(tags, str):
        tags = tags.split(',')
    elif tags is None and isinstance(task, dict):
        tags = task.get('tags', [])
        if isinstance(tags, str):
            tags = tags.split(',')
            
    if tags:
        for tag in tags:
            tag = str(tag).strip()
            if tag:
                tags_set.add(tag)
    
    # 2. Extract from hybrid_tags
    ht = getattr(task, 'hybrid_tags', None)
    if not ht and isinstance(task, dict):
         ht = task.get('hybrid_tags')
    
    if ht:
        # ht might be Object or Dict
        bracket = getattr(ht, 'bracket', None)
        if bracket is None and isinstance(ht, dict):
            bracket = ht.get('bracket')
            
        hash_tags = getattr(ht, 'hash', None)
        if hash_tags is None and isinstance(ht, dict):
            hash_tags = ht.get('hash')
            
        user = getattr(ht, 'user', None)
        if user is None and isinstance(ht, dict):
            user = ht.get('user')
            
        # Add tags
        if bracket:
            tags_set.update([str(t).strip() for t in bracket if str(t).strip()])
        if hash_tags:
            tags_set.update([str(t).strip() for t in hash_tags if str(t).strip()])
        if user:
            tags_set.update([f"@{str(t).strip()}" for t in user if str(t).strip()])
            
    else:
        # Fallback description
        desc = getattr(task, 'description', '') or ''
        if not desc and isinstance(task, dict):
            desc = task.get('description', '') or ''
        
        if desc:
            description_tags = re.findall(r'\[([^\]]+)\]', desc)
            tags_set.update([t.strip() for t in description_tags if t.strip()])
            
            # 3. Extract account tags from description (only if not already extracted from hybrid_tags)
            if not ht:
                account_tags = re.findall(r'@(\w+)', desc)
                tags_set.update([f"@{t.strip()}" for t in account_tags if t.strip()])
            
    return tags_set


def _sync_task_to_google_background(task_id: str, account_id: str):
    """Background task to sync task completion to Google Tasks (non-blocking)"""
    with _sync_lock:
        try:
            print(f'[Background Sync] Starting sync for task {task_id} (account: {account_id})')
            
            # Import here to avoid circular imports and only load when needed
            import sys
            from pathlib import Path
            from datetime import datetime
            
            # Add gtasks_cli to path
            gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
            if str(gtasks_cli_path) not in sys.path:
                sys.path.insert(0, str(gtasks_cli_path))
            
            from gtasks_cli.core.task_manager import TaskManager
            from gtasks_cli.storage.sqlite_storage import SQLiteStorage
            from gtasks_cli.integrations.google_tasks_client import GoogleTasksClient
            from gtasks_cli.models.task import TaskStatus
            
            # Initialize components
            storage = SQLiteStorage(account_name=account_id)
            google_client = GoogleTasksClient(account_name=account_id)
            
            # Connect to Google Tasks (non-blocking, uses cached credentials)
            if not google_client.connect():
                print(f'[Background Sync] Failed to connect to Google Tasks - credentials may need refresh')
                return
            
            # Get the task from local storage
            task_dicts = storage.load_tasks()
            task = None
            for t in task_dicts:
                if t.get('id') == task_id:
                    task = t
                    break
            
            if not task:
                print(f'[Background Sync] Task {task_id} not found in local storage')
                return
            
            # Create Task object
            from gtasks_cli.models.task import Task
            task_obj = Task(**task)
            
            # Update status to completed
            task_obj.status = TaskStatus.COMPLETED
            task_obj.completed_at = datetime.utcnow()
            task_obj.modified_at = datetime.utcnow()
            
            # Try to update via Google Tasks API
            try:
                if hasattr(task_obj, 'tasklist_id') and task_obj.tasklist_id:
                    updated = google_client.update_task(task_obj, task_obj.tasklist_id)
                    if updated:
                        print(f'[Background Sync] ✅ Successfully synced task {task_id} to Google Tasks')
                    else:
                        print(f'[Background Sync] ⚠️ Google Tasks API returned empty response for {task_id}')
                else:
                    print(f'[Background Sync] ⚠️ Task {task_id} has no tasklist_id, cannot sync to Google')
            except Exception as e:
                error_msg = str(e)
                if 'invalid_grant' in error_msg.lower() or 'credentials' in error_msg.lower():
                    print(f'[Background Sync] 🔑 Google credentials need refresh - sync pending')
                else:
                    print(f'[Background Sync] ❌ Error syncing to Google: {e}')
                    
        except Exception as e:
            print(f'[Background Sync] ❌ Unexpected error: {e}')
            traceback.print_exc()


def _sync_task_to_turso_background(task_id: str, account_id: str):
    """Background task to sync task completion to Turso Remote DB (non-blocking)"""
    try:
        print(f'[Turso Background Sync] Starting sync for task {task_id} (account: {account_id})')
        
        # Import required modules
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        from gtasks_cli.storage.sqlite_storage import SQLiteStorage
        from gtasks_cli.storage.sync_config_storage import SyncConfigStorage
        from gtasks_cli.storage.libsql_storage import LibSQLStorage
        
        # Initialize storage and load the task
        storage = SQLiteStorage(account_name=account_id)
        task_dicts = storage.load_tasks()
        task = None
        for t in task_dicts:
            if t.get('id') == task_id:
                task = t
                break
        
        if not task:
            print(f'[Turso Background Sync] Task {task_id} not found in local storage')
            return
        
        # Get active remote databases
        config_storage = SyncConfigStorage(account_name=account_id)
        active_dbs = config_storage.get_active_remote_dbs()
        
        if not active_dbs:
            print(f'[Turso Background Sync] No active remote databases configured')
            return
        
        # Push the task to each active remote DB
        for db_config in active_dbs:
            try:
                remote_storage = LibSQLStorage(url=db_config.url, account_name=account_id)
                # Get existing remote tasks
                remote_tasks = remote_storage.load_tasks()
                
                # Update or add the task
                updated_remote_tasks = []
                task_updated = False
                for rt in remote_tasks:
                    if rt.get('id') == task_id:
                        # Update existing task with completed status
                        rt['status'] = task['status']
                        rt['completed_at'] = task['completed_at']
                        rt['modified_at'] = task.get('modified_at', task['completed_at'])
                        task_updated = True
                    updated_remote_tasks.append(rt)
                
                if not task_updated:
                    # Task doesn't exist in remote, add it
                    updated_remote_tasks.append(task)
                
                # Save updated tasks
                remote_storage.save_tasks(updated_remote_tasks)
                remote_storage.close()
                
                # Update last synced timestamp
                config_storage.update_last_synced(db_config.url)
                
                print(f'[Turso Background Sync] ✅ Synced task {task_id} to {db_config.name}')
                
            except Exception as e:
                print(f'[Turso Background Sync] ❌ Error syncing to {db_config.name}: {e}')
                
    except Exception as e:
        print(f'[Turso Background Sync] ❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()


def _sync_task_update_to_google_background(task_id: str, account_id: str, updates: dict):
    """Background task to sync task updates to Google Tasks (non-blocking)"""
    with _sync_lock:
        try:
            print(f'[Background Sync Update] Starting sync for task {task_id} (account: {account_id})')
            print(f'[Background Sync Update] Updates: {list(updates.keys())}')
            
            # Import here to avoid circular imports
            import sys
            from pathlib import Path
            from datetime import datetime
            
            # Add gtasks_cli to path
            gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
            if str(gtasks_cli_path) not in sys.path:
                sys.path.insert(0, str(gtasks_cli_path))
            
            from gtasks_cli.core.task_manager import TaskManager
            from gtasks_cli.storage.sqlite_storage import SQLiteStorage
            from gtasks_cli.integrations.google_tasks_client import GoogleTasksClient
            from gtasks_cli.models.task import Task, TaskStatus
            
            # Initialize components
            storage = SQLiteStorage(account_name=account_id)
            google_client = GoogleTasksClient(account_name=account_id)
            
            # Connect to Google Tasks
            if not google_client.connect():
                print(f'[Background Sync Update] Failed to connect to Google Tasks')
                return
            
            # Get the task from local storage
            task_dicts = storage.load_tasks()
            task = None
            for t in task_dicts:
                if t.get('id') == task_id:
                    task = t
                    break
            
            if not task:
                print(f'[Background Sync Update] Task {task_id} not found in local storage')
                return
            
            # Create Task object
            task_obj = Task(**task)
            
            # Apply updates to task object
            if 'status' in updates:
                try:
                    task_obj.status = TaskStatus(updates['status'])
                except ValueError:
                    pass
            if 'title' in updates:
                task_obj.title = updates['title']
            if 'description' in updates:
                task_obj.description = updates['description']
            if 'due' in updates:
                task_obj.due = updates['due']
            if 'priority' in updates:
                task_obj.priority = updates['priority']
                task_obj.calculated_priority = updates['priority']
            
            task_obj.modified_at = datetime.utcnow()
            
            # Try to update via Google Tasks API
            try:
                if hasattr(task_obj, 'tasklist_id') and task_obj.tasklist_id:
                    updated = google_client.update_task(task_obj, task_obj.tasklist_id)
                    if updated:
                        print(f'[Background Sync Update] ✅ Successfully synced task {task_id} to Google Tasks')
                    else:
                        print(f'[Background Sync Update] ⚠️ Google Tasks API returned empty response for {task_id}')
                else:
                    print(f'[Background Sync Update] ⚠️ Task {task_id} has no tasklist_id, cannot sync to Google')
            except Exception as e:
                error_msg = str(e)
                if 'invalid_grant' in error_msg.lower() or 'credentials' in error_msg.lower():
                    print(f'[Background Sync Update] 🔑 Google credentials need refresh')
                else:
                    print(f'[Background Sync Update] ❌ Error syncing to Google: {e}')
                    
        except Exception as e:
            print(f'[Background Sync Update] ❌ Unexpected error: {e}')
            traceback.print_exc()


def _sync_task_update_to_turso_background(task_id: str, account_id: str, updates: dict):
    """Background task to sync task updates to Turso Remote DB (non-blocking)"""
    try:
        print(f'[Turso Background Sync Update] Starting sync for task {task_id} (account: {account_id})')
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        from gtasks_cli.storage.sqlite_storage import SQLiteStorage
        from gtasks_cli.storage.sync_config_storage import SyncConfigStorage
        from gtasks_cli.storage.libsql_storage import LibSQLStorage
        
        # Initialize storage and load the task
        storage = SQLiteStorage(account_name=account_id)
        task_dicts = storage.load_tasks()
        task = None
        for t in task_dicts:
            if t.get('id') == task_id:
                task = t
                break
        
        if not task:
            print(f'[Turso Background Sync Update] Task {task_id} not found')
            return
        
        # Apply updates to task
        for key, value in updates.items():
            if key in ['title', 'description', 'due', 'status', 'priority', 'calculated_priority']:
                task[key] = value
        task['modified_at'] = datetime.now().isoformat()
        
        # Get active remote databases
        config_storage = SyncConfigStorage(account_name=account_id)
        active_dbs = config_storage.get_active_remote_dbs()
        
        if not active_dbs:
            print(f'[Turso Background Sync Update] No active remote databases')
            return
        
        # Push the task to each active remote DB
        for db_config in active_dbs:
            try:
                remote_storage = LibSQLStorage(url=db_config.url, account_name=account_id)
                remote_tasks = remote_storage.load_tasks()
                
                updated_remote_tasks = []
                task_updated = False
                for rt in remote_tasks:
                    if rt.get('id') == task_id:
                        # Update with new values
                        for key, value in updates.items():
                            if key in ['title', 'description', 'due', 'status', 'priority', 'calculated_priority']:
                                rt[key] = value
                        rt['modified_at'] = task['modified_at']
                        task_updated = True
                    updated_remote_tasks.append(rt)
                
                if not task_updated:
                    updated_remote_tasks.append(task)
                
                remote_storage.save_tasks(updated_remote_tasks)
                remote_storage.close()
                
                config_storage.update_last_synced(db_config.url)
                print(f'[Turso Background Sync Update] ✅ Synced task {task_id} to {db_config.name}')
                
            except Exception as e:
                print(f'[Turso Background Sync Update] ❌ Error syncing to {db_config.name}: {e}')
                
    except Exception as e:
        print(f'[Turso Background Sync Update] ❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()


def refresh_dashboard_cache():
    """Refresh the in-memory dashboard cache from database"""
    print('[Cache] Refreshing dashboard cache...')
    
    # Detect accounts first
    accounts = data_manager.detect_accounts()
    _dashboard_state['accounts'] = accounts
    
    # Set first account as active
    if accounts:
        _dashboard_state['current_account'] = accounts[0].id
    
    # Load tasks FRESH from database for each account
    _dashboard_state['tasks'] = {}
    for account in accounts:
        tasks = data_manager.load_tasks_for_account(account.id)
        _dashboard_state['tasks'][account.id] = [t.to_dict() for t in tasks]
        print(f'[Cache] Loaded {len(tasks)} tasks for account: {account.id}')
    
    total_tasks = sum(len(tasks) for tasks in _dashboard_state['tasks'].values())
    print(f'[Cache] ✅ Cache refreshed with {len(accounts)} accounts and {total_tasks} total tasks')
    
    # Sync tags with newly loaded tasks
    data_manager.sync_tags_with_tasks()
    
    return True


def init_dashboard_state():
    """Initialize dashboard state"""
    refresh_dashboard_cache()


@api.route('/refresh', methods=['POST'])
def api_refresh_cache():
    """Refresh the dashboard cache (called when refresh button is clicked)"""
    try:
        refresh_dashboard_cache()
        return jsonify({
            'success': True,
            'message': 'Dashboard cache refreshed successfully',
            'accounts_count': len(_dashboard_state['accounts']),
            'total_tasks': sum(len(tasks) for tasks in _dashboard_state['tasks'].values())
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error refreshing cache: {str(e)}'
        }), 500


def get_current_tasks():
    """Get tasks for current account"""
    current = _dashboard_state.get('current_account')
    if current:
        # First try exact match
        tasks = _dashboard_state['tasks'].get(current, [])
        if tasks:
            return tasks
        
        # Try case-insensitive match if no exact match found
        current_lower = current.lower()
        for account_id in _dashboard_state['tasks'].keys():
            if account_id.lower() == current_lower:
                return _dashboard_state['tasks'].get(account_id, [])
        
        # If still no tasks found, log warning and return empty list
        print(f'[WARNING] get_current_tasks: No tasks found for account "{current}"')
        print(f'[WARNING] Available accounts: {list(_dashboard_state["tasks"].keys())}')
        return []
    return []


@api.route('/data')
def api_data():
    """Get all dashboard data"""
    current_account_id = _dashboard_state.get('current_account')
    tasks = _dashboard_state['tasks'].get(current_account_id, []) if current_account_id else []
    
    # Calculate stats for current account only
    from models.task import DashboardStats
    from models.task import Task
    task_objects = [Task.from_dict(t) for t in tasks]
    stats = DashboardStats.from_tasks(task_objects)
    
    return jsonify({
        'tasks': tasks,
        'accounts': [a.to_dict() for a in _dashboard_state['accounts']],
        'current_account': current_account_id,
        'stats': {
            'total': stats.total_tasks,
            'completed': stats.completed_tasks,
            'pending': stats.pending_tasks,
            'in_progress': stats.in_progress_tasks,
            'critical': stats.critical_tasks,
            'high': stats.high_priority_tasks,
            'overdue': stats.overdue_tasks,
            'completion_rate': stats.completion_rate
        }
    })


@api.route('/tasks')
def api_tasks():
    """Get tasks with optional filters"""
    tasks = get_current_tasks()
    
    # Apply filters
    status = request.args.get('status')
    priority = request.args.get('priority')
    search = request.args.get('search')
    account_id = request.args.get('account_id')
    tag = request.args.get('tag')
    
    if account_id and account_id in _dashboard_state['tasks']:
        tasks = _dashboard_state['tasks'][account_id]
    elif not account_id:
        tasks = get_current_tasks()
    
    if status:
        tasks = [t for t in tasks if t.get('status') == status]
    
    if priority:
        tasks = [t for t in tasks if t.get('calculated_priority') == priority]
    
    if tag:
        # Filter tasks that have the specified tag
        tag_lower = tag.lower()
        tasks = [t for t in tasks if tag_lower in [t_tag.lower() for t_tag in extract_tags_from_task(t)]]
    
    if search:
        search_lower = search.lower()
        tasks = [t for t in tasks if 
                 search_lower in t.get('title', '').lower() or
                 (t.get('description') and search_lower in t.get('description', '').lower())]
    
    return jsonify({
        'tasks': tasks,
        'total': len(tasks)
    })


@api.route('/accounts')
def api_accounts():
    """Get all accounts"""
    return jsonify({
        'accounts': [a.to_dict() for a in _dashboard_state['accounts']],
        'current_account': _dashboard_state.get('current_account')
    })


@api.route('/accounts/<account_id>/switch', methods=['POST'])
def switch_account(account_id):
    """Switch to a different account"""
    if account_id in [a.id for a in _dashboard_state['accounts']]:
        _dashboard_state['current_account'] = account_id
        
        # Load tasks for this account if not already loaded
        if account_id not in _dashboard_state['tasks']:
            tasks = data_manager.load_tasks_for_account(account_id)
            _dashboard_state['tasks'][account_id] = [t.to_dict() for t in tasks]
        
        return jsonify({
            'success': True,
            'account_id': account_id
        })
    
    return jsonify({'success': False, 'error': 'Account not found'}), 404


@api.route('/stats')
def api_stats():
    """Get dashboard statistics"""
    from models.task import DashboardStats, Task
    
    tasks = get_current_tasks()
    task_objects = [Task.from_dict(t) for t in tasks]
    stats = DashboardStats.from_tasks(task_objects)
    
    return jsonify({
        'total': stats.total_tasks,
        'completed': stats.completed_tasks,
        'pending': stats.pending_tasks,
        'in_progress': stats.in_progress_tasks,
        'critical': stats.critical_tasks,
        'high': stats.high_priority_tasks,
        'overdue': stats.overdue_tasks,
        'completion_rate': stats.completion_rate
    })


@api.route('/hierarchy')
def api_hierarchy():
    """Get hierarchy visualization data"""
    from models.task import Task
    
    tasks = get_current_tasks()
    task_objects = [Task.from_dict(t) for t in tasks]
    hierarchy_data = data_manager.get_hierarchy_data(task_objects)
    
    return jsonify(hierarchy_data)


@api.route('/hierarchy/filtered')
def api_hierarchy_filtered():
    """Get filtered hierarchy visualization data"""
    from models.task import Task
    
    # Get filter parameters
    tag_search = request.args.get('tag_search', '')
    status = request.args.get('status', '')
    date_field = request.args.get('date_field', 'due')
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    
    # Parse tag search (comma-separated)
    tag_filters = data_manager.parse_chart_tag_filter(tag_search)
    
    tasks = get_current_tasks()
    task_objects = [Task.from_dict(t) for t in tasks]
    
    # Get filtered hierarchy data
    if tag_filters or status or date_start or date_end:
        hierarchy_data = data_manager.get_filtered_hierarchy_data(
            task_objects,
            tag_filters=tag_filters,
            status_filter=status or None,
            date_field=date_field,
            date_start=date_start or None,
            date_end=date_end or None
        )
    else:
        hierarchy_data = data_manager.get_hierarchy_data(task_objects)
    
    return jsonify(hierarchy_data)


@api.route('/tasks/<task_id>')
def get_task(task_id):
    """Get a specific task"""
    for account_tasks in _dashboard_state['tasks'].values():
        for task in account_tasks:
            if task.get('id') == task_id:
                return jsonify(task)
    
    return jsonify({'error': 'Task not found'}), 404


@api.route('/debug/account-state', methods=['GET'])
def api_debug_account_state():
    """Debug endpoint to check current account state"""
    current = _dashboard_state.get('current_account')
    accounts = [a.id for a in _dashboard_state['accounts']]
    task_accounts = list(_dashboard_state['tasks'].keys())
    
    # Get current tasks with the new logic
    tasks = get_current_tasks()
    
    # Get sample tags from current tasks
    sample_tags = set()
    for task in tasks[:10]:
        task_tags = extract_tags_from_task(task)
        sample_tags.update(task_tags)
    
    return jsonify({
        'current_account': current,
        'all_accounts': accounts,
        'task_accounts': task_accounts,
        'current_tasks_count': len(tasks),
        'sample_tags': list(sample_tags)[:20],
        'default_account_set_to': 'Work'  # This is what the DataManager sets
    })


# ============================================
# ENHANCED API ENDPOINTS (Consolidated)
# ============================================

@api.route('/account-types')
def api_account_types():
    """Get all account types"""
    return jsonify({
        'success': True,
        'data': data_manager.dashboard_state.get('account_types', [])
    })


@api.route('/available-tags')
def api_available_tags():
    """Get all available tags"""
    return jsonify({
        'success': True,
        'data': data_manager.dashboard_state.get('available_tags', {})
    })


@api.route('/tags', methods=['GET'])
def api_tags():
    """
    Get all tags.
    
    This endpoint extracts tags from:
    1. The structured 'tags' field of tasks
    2. Tags in task descriptions in [tagname] format
    3. Account tags in task descriptions in [@account] format
    
    Response:
        {
            "success": True,
            "tags": [
                {"id": "tag_name", "name": "tag_name", "is_account": True/False, "usage_count": 5},
                ...
            ]
        }
    """
    try:
        available_tags = data_manager.dashboard_state.get('available_tags', {})
        
        # Get all tasks from all accounts to count tag usage
        all_tasks = []
        for account_tasks in _dashboard_state['tasks'].values():
            all_tasks.extend(account_tasks)
        
        # Count tags usage using the helper function
        tags_usage = {}
        for task in all_tasks:
            task_tags = extract_tags_from_task(task)
            for tag in task_tags:
                tags_usage[tag] = tags_usage.get(tag, 0) + 1
        
        # Build tags list
        tags_list = []
        for tag_name, tag_data in available_tags.items():
            tags_list.append({
                'id': tag_name,
                'name': tag_name,
                'is_account': tag_name.startswith('@'),
                'usage_count': tags_usage.get(tag_name, 0)
            })
        
        # Sort by name
        tags_list.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'tags': tags_list
        })
        
    except Exception as e:
        print(f'[API] Error getting tags: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error getting tags: {str(e)}'
        }), 500


@api.route('/tags/<tag_name>', methods=['DELETE'])
def api_delete_tag(tag_name):
    """
    Delete a tag.
    
    Path parameters:
        tag_name: Name of the tag to delete
        
    Response:
        {
            "success": True,
            "message": "Tag deleted successfully"
        }
    """
    try:
        available_tags = data_manager.dashboard_state.get('available_tags', {})
        
        if tag_name in available_tags:
            del available_tags[tag_name]
            data_manager.dashboard_state['available_tags'] = available_tags
            
            return jsonify({
                'success': True,
                'message': f'Tag "{tag_name}" deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Tag not found'
            }), 404
        
    except Exception as e:
        print(f'[API] Error deleting tag: {e}')
        return jsonify({
            'success': False,
            'message': f'Error deleting tag: {str(e)}'
        }), 500


@api.route('/connections', methods=['GET'])
def api_connections():
    """
    Get all user connections.
    
    Response:
        {
            "success": True,
            "connections": [
                {
                    "id": "conn_id",
                    "email": "user@example.com",
                    "user_id": "user12345",
                    "status": "connected",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                ...
            ]
        }
    """
    try:
        connections = _dashboard_state.get('connections', [])
        
        # Build connections list
        connections_list = []
        for conn in connections:
            connections_list.append({
                'id': conn['id'],
                'email': conn['to_email'],
                'user_id': conn['to_user'],
                'status': 'connected',
                'created_at': conn['created_at']
            })
        
        return jsonify({
            'success': True,
            'connections': connections_list
        })
        
    except Exception as e:
        print(f'[API] Error getting connections: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting connections: {str(e)}'
        }), 500


@api.route('/connections/<connection_id>', methods=['DELETE'])
def api_delete_connection(connection_id):
    """
    Disconnect a user.
    
    Path parameters:
        connection_id: ID of the connection to delete
        
    Response:
        {
            "success": True,
            "message": "User disconnected successfully"
        }
    """
    try:
        connections = _dashboard_state.get('connections', [])
        
        # Find and remove the connection
        original_length = len(connections)
        _dashboard_state['connections'] = [c for c in connections if c['id'] != connection_id]
        
        if len(_dashboard_state['connections']) < original_length:
            return jsonify({
                'success': True,
                'message': 'User disconnected successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Connection not found'
            }), 404
        
    except Exception as e:
        print(f'[API] Error disconnecting user: {e}')
        return jsonify({
            'success': False,
            'message': f'Error disconnecting user: {str(e)}'
        }), 500


# ============================================
# TAGS IMPORT ENDPOINTS
# ============================================

@api.route('/tags/dry-run', methods=['POST'])
def api_tags_dry_run():
    """
    Preview tags that will be imported from Google Tasks.
    
    This endpoint extracts tags from:
    1. The structured 'tags' field of tasks
    2. Tags in task descriptions in [tagname] format
    3. Account tags in task descriptions in [@account] format
    
    Note: Tags are extracted from the CURRENT ACCOUNT only.
    
    Response:
        {
            "success": True,
            "data": {
                "preview": [...],
                "count": 5,
                "message": "Dry run completed. These tags will be imported."
            }
        }
    """
    try:
        # Debug: Log current account state
        current_account = _dashboard_state.get('current_account')
        all_accounts = [a.id for a in _dashboard_state['accounts']]
        print(f'[DEBUG] Dry run - Current account: {current_account}')
        print(f'[DEBUG] Dry run - All accounts: {all_accounts}')
        
        # Get tasks from current account only
        all_tasks = get_current_tasks()
        print(f'[DEBUG] Dry run - Got {len(all_tasks)} tasks from current account')
        
        if len(all_tasks) == 0:
            # If no tasks in current account, try getting from ALL accounts for debugging
            print('[DEBUG] Dry run - No tasks in current account, checking all accounts...')
            for account_id, tasks in _dashboard_state['tasks'].items():
                print(f'[DEBUG] - Account {account_id}: {len(tasks)} tasks')
                # Show sample tags from each account
                if len(tasks) > 0:
                    sample_tags = set()
                    for task in tasks[:5]:  # Check first 5 tasks
                        task_tags = extract_tags_from_task(task)
                        sample_tags.update(task_tags)
                    print(f'[DEBUG] - Sample tags in {account_id}: {list(sample_tags)[:10]}')
        
        # Extract unique tags from all tasks using the helper function
        tags_set = set()
        for task in all_tasks:
            task_tags = extract_tags_from_task(task)
            tags_set.update(task_tags)
        
        print(f'[DEBUG] Dry run - Found {len(tags_set)} unique tags: {list(tags_set)[:20]}')
        
        # Sort tags
        tags_list = sorted(list(tags_set))
        
        # Create preview data
        preview = []
        for tag in tags_list:
            preview.append({
                'name': tag,
                'type': 'account' if tag.startswith('@') else 'regular',
                'action': 'import'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'preview': preview,
                'count': len(preview),
                'message': f'Dry run completed. {len(preview)} tags will be imported.'
            }
        })
        
    except Exception as e:
        print(f'[API] Error in dry run: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error running dry run: {str(e)}'
        }), 500


@api.route('/tags/import', methods=['POST'])
def api_tags_import():
    """
    Import tags from Google Tasks to the local database.
    
    This endpoint extracts tags from:
    1. The structured 'tags' field of tasks
    2. Tags in task descriptions in [tagname] format
    3. Account tags in task descriptions in [@account] format
    
    Note: Tags are extracted from the CURRENT ACCOUNT only.
    
    Request body (optional):
        {
            "dry_run": false  # If true, only preview without importing
        }
        
    Response:
        {
            "success": True,
            "data": {
                "imported": 5,
                "tags": [...]
            },
            "message": "Tags imported successfully"
        }
    """
    try:
        # Parse request body safely - allow requests without JSON body
        data = {}
        content_type = request.content_type or ''
        
        if 'application/json' in content_type:
            try:
                data = request.get_json() or {}
            except Exception:
                pass
        
        dry_run = data.get('dry_run', False)
        
        # Get tasks from current account only
        all_tasks = get_current_tasks()
        
        # Extract unique tags from all tasks using the helper function
        tags_set = set()
        for task in all_tasks:
            task_tags = extract_tags_from_task(task)
            tags_set.update(task_tags)
        
        # Sort tags
        tags_list = sorted(list(tags_set))
        
        if dry_run:
            # Just return preview
            preview = [{'name': tag, 'type': 'account' if tag.startswith('@') else 'regular'} for tag in tags_list]
            return jsonify({
                'success': True,
                'data': {
                    'preview': preview,
                    'count': len(preview),
                    'message': f'Dry run: {len(preview)} tags would be imported.'
                }
            })
        
        # Import tags (store in dashboard state for now)
        available_tags = data_manager.dashboard_state.get('available_tags', {})
        for tag in tags_list:
            if tag not in available_tags:
                available_tags[tag] = {
                    'name': tag,
                    'type': 'account' if tag.startswith('@') else 'regular',
                    'created_at': datetime.now().isoformat(),
                    'task_count': 0
                }
        
        # Update task counts by re-extracting tags from all tasks
        for task in all_tasks:
            task_tags = extract_tags_from_task(task)
            for tag in task_tags:
                if tag in available_tags:
                    available_tags[tag]['task_count'] = available_tags[tag].get('task_count', 0) + 1
        
        data_manager.dashboard_state['available_tags'] = available_tags
        
        # Create imported tags list
        imported_tags = [{'name': tag, 'type': 'account' if tag.startswith('@') else 'regular'} for tag in tags_list]
        
        return jsonify({
            'success': True,
            'data': {
                'imported': len(tags_list),
                'tags': imported_tags
            },
            'message': f'Successfully imported {len(tags_list)} tags'
        })
        
    except Exception as e:
        print(f'[API] Error importing tags: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error importing tags: {str(e)}'
        }), 500


@api.route('/tags/statistics', methods=['GET'])
def api_tags_statistics():
    """
    Get statistics about tags.
    
    This endpoint extracts tags from:
    1. The structured 'tags' field of tasks
    2. Tags in task descriptions in [tagname] format
    3. Account tags in task descriptions in [@account] format
    
    Response:
        {
            "success": True,
            "data": {
                "total_tags": 10,
                "account_tags": 2,
                "regular_tags": 8,
                "top_tags": [...],
                "unused_tags": [...]
            }
        }
    """
    try:
        available_tags = data_manager.dashboard_state.get('available_tags', {})
        
        # Get all tags from tasks using the helper function
        all_tasks = []
        for account_tasks in _dashboard_state['tasks'].values():
            all_tasks.extend(account_tasks)
        
        # Count tags usage using the helper function
        tags_usage = {}
        for task in all_tasks:
            task_tags = extract_tags_from_task(task)
            for tag in task_tags:
                tags_usage[tag] = tags_usage.get(tag, 0) + 1
        
        # Calculate statistics
        account_tags = [tag for tag in available_tags.keys() if tag.startswith('@')]
        regular_tags = [tag for tag in available_tags.keys() if not tag.startswith('@')]
        
        # Top tags by usage
        top_tags = sorted([(tag, count) for tag, count in tags_usage.items()], key=lambda x: x[1], reverse=True)[:10]
        
        # Unused tags
        used_tags = set(tags_usage.keys())
        all_defined_tags = set(available_tags.keys())
        unused_tags = list(all_defined_tags - used_tags)
        
        return jsonify({
            'success': True,
            'data': {
                'total_tags': len(available_tags),
                'account_tags': len(account_tags),
                'regular_tags': len(regular_tags),
                'total_usage_count': sum(tags_usage.values()),
                'top_tags': [{'name': tag, 'count': count} for tag, count in top_tags],
                'unused_tags_count': len(unused_tags)
            }
        })
        
    except Exception as e:
        print(f'[API] Error getting tag statistics: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error getting statistics: {str(e)}'
        }), 500


@api.route('/tags/sync', methods=['POST'])
def api_tags_sync():
    """
    Sync tags with tasks to update usage counts.
    
    This endpoint extracts tags from:
    1. The structured 'tags' field of tasks
    2. Tags in task descriptions in [tagname] format
    3. Account tags in task descriptions in [@account] format
    
    Response:
        {
            "success": True,
            "data": {
                "synced": 10,
                "message": "Tags synced successfully"
            }
        }
    """
    try:
        # Sync tags using DataManager
        data_manager.sync_tags_with_tasks()
        
        # Get count
        available_tags = data_manager.dashboard_state.get('available_tags', {})
        synced_count = len(available_tags)
        total_updates = sum(t.get('task_count', 0) for t in available_tags.values())
        
        return jsonify({
            'success': True,
            'data': {
                'synced': synced_count,
                'total_updates': total_updates
            },
            'message': f'Synced {synced_count} unique tags'
        })
        
    except Exception as e:
        print(f'[API] Error syncing tags: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error syncing tags: {str(e)}'
        }), 500


@api.route('/priority-stats')
def api_priority_stats():
    """Get priority statistics"""
    return jsonify({
        'success': True,
        'data': data_manager.dashboard_state.get('priority_stats', {})
    })


@api.route('/tags/parse-filter', methods=['POST'])
def api_parse_tag_filter():
    """Parse tag filter string"""
    data = request.get_json()
    tag_string = data.get('tag_string', '')
    
    parsed = data_manager.parse_tag_filter(tag_string)
    return jsonify({
        'success': True,
        'data': parsed
    })


@api.route('/tasks/due-today')
def api_tasks_due_today():
    """Get tasks due today"""
    due_today_tasks = data_manager.get_tasks_due_today()
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in due_today_tasks]
    })


@api.route('/settings', methods=['GET'])
def api_get_settings():
    """Get dashboard settings"""
    return jsonify({
        'success': True,
        'data': data_manager.dashboard_state.get('settings', {})
    })


@api.route('/settings', methods=['POST'])
def api_update_settings():
    """Update dashboard settings"""
    data = request.get_json()
    try:
        updated_settings = data_manager.update_settings(data)
        return jsonify({
            'success': True,
            'data': updated_settings,
            'message': 'Settings updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating settings: {str(e)}'
        }), 500


@api.route('/tasks/<task_id>/delete', methods=['POST'])
def api_delete_task(task_id):
    """Soft delete a task"""
    data = request.get_json() or {}
    account_id = data.get('account_id', _dashboard_state.get('current_account'))
    permanent = data.get('permanent', False)
    
    try:
        if permanent:
            success = data_manager.permanently_delete_task(task_id, account_id)
            action = 'permanently deleted'
        else:
            success = data_manager.soft_delete_task(task_id, account_id)
            action = 'deleted'
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Task {action} successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Task not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting task: {str(e)}'
        }), 500


@api.route('/tasks/<task_id>/restore', methods=['POST'])
def api_restore_task(task_id):
    """Restore a deleted task"""
    data = request.get_json() or {}
    account_id = data.get('account_id', _dashboard_state.get('current_account'))
    
    try:
        success = data_manager.restore_task(task_id, account_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'Task restored successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Task not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error restoring task: {str(e)}'
        }), 500


@api.route('/deleted-tasks')
def api_deleted_tasks():
    """Get deleted tasks"""
    account_id = request.args.get('account', _dashboard_state.get('current_account'))
    
    all_tasks = _dashboard_state['tasks'].get(account_id, [])
    deleted_tasks = [t for t in all_tasks if t.get('is_deleted', False)]
    
    return jsonify({'success': True, 'data': deleted_tasks})


@api.route('/reports/types')
def api_report_types():
    """Get available report types"""
    return jsonify({
        'success': True,
        'data': data_manager.get_report_types()
    })


@api.route('/reports/generate', methods=['POST'])
def api_generate_report():
    """Generate a report"""
    data = request.get_json()
    report_type = data.get('report_type')
    filters = data.get('filters', {})
    parameters = data.get('parameters', {})
    
    if not report_type:
        return jsonify({
            'success': False,
            'message': 'Report type is required'
        }), 400
    
    try:
        # Get filtered tasks
        filtered_tasks = data_manager.get_filtered_tasks(filters)
        
        # Generate report
        report_data = data_manager.generate_report(report_type, filtered_tasks, **parameters)
        
        return jsonify({
            'success': True,
            'data': report_data,
            'message': f'Report {report_type} generated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating report: {str(e)}'
        }), 500


@api.route('/filter-tasks', methods=['POST'])
def api_filter_tasks():
    """Advanced task filtering"""
    data = request.get_json()
    filters = data.get('filters', {})
    
    try:
        filtered_tasks = data_manager.get_filtered_tasks(filters)
        return jsonify({
            'success': True,
            'data': [t.to_dict() for t in filtered_tasks],
            'count': len(filtered_tasks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error filtering tasks: {str(e)}'
        }), 500


@api.route('/updates/last')
def api_last_update():
    """Get last update timestamp"""
    return jsonify({
        'success': True,
        'data': {
            'last_update': data_manager.dashboard_state['realtime'].get('last_update'),
            'connected': data_manager.dashboard_state['realtime'].get('connected', False)
        }
    })


@api.route('/tasks/<task_id>/complete', methods=['POST'])
def api_complete_task(task_id):
    """Mark a task as completed with background sync to Google Tasks"""
    from datetime import datetime
    data = request.get_json() or {}
    account_id = data.get('account_id', _dashboard_state.get('current_account'))
    sync_to_google = data.get('sync_to_google', True)
    
    print(f'[API] Completing task: {task_id}')
    print(f'[API] Account: {account_id}')
    print(f'[API] Sync to Google: {sync_to_google}')
    
    # Search in the specified account first, then all accounts
    accounts_to_search = []
    if account_id and account_id in _dashboard_state['tasks']:
        accounts_to_search = [account_id]
    else:
        accounts_to_search = list(_dashboard_state['tasks'].keys())
    
    task_found = False
    completed_task = None
    
    for acc_id in accounts_to_search:
        tasks = _dashboard_state['tasks'].get(acc_id, [])
        
        for task in tasks:
            if task.get('id') == task_id:
                print(f'[API] Found task: {task_id}')
                task_found = True
                
                # Update task in memory
                task['status'] = 'completed'
                task['completed_at'] = datetime.now().isoformat()
                completed_task = task
                
                # Sync to local SQLite database
                try:
                    db_path = data_manager.gtasks_path / acc_id / 'tasks.db' if data_manager.gtasks_path else None
                    if not db_path or not db_path.exists():
                        db_path = data_manager.gtasks_path / 'tasks.db' if data_manager.gtasks_path else None
                    
                    if db_path and db_path.exists():
                        import sqlite3
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE tasks 
                            SET status = ?, completed_at = ?, modified_at = ?
                            WHERE id = ?
                        """, (
                            'completed',
                            task['completed_at'],
                            datetime.now().isoformat(),
                            task_id
                        ))
                        conn.commit()
                        conn.close()
                        print(f'[API] Task {task_id} updated in local database')
                except Exception as e:
                    print(f'[API] Error updating local database: {e}')
                
                # Trigger background sync to Google Tasks (non-blocking)
                if sync_to_google:
                    print(f'[API] Starting background sync to Google Tasks...')
                    sync_thread = threading.Thread(
                        target=_sync_task_to_google_background,
                        args=(task_id, acc_id),
                        daemon=True
                    )
                    sync_thread.start()
                    print(f'[API] Background sync thread started for task {task_id}')
                
                # Trigger background sync to Turso Remote DB (non-blocking)
                print(f'[API] Starting background sync to Turso Remote DB...')
                turso_sync_thread = threading.Thread(
                    target=_sync_task_to_turso_background,
                    args=(task_id, acc_id),
                    daemon=True
                )
                turso_sync_thread.start()
                print(f'[API] Background Turso sync thread started for task {task_id}')
                
                break
        
        if task_found:
            break
    
    if task_found:
        return jsonify({
            'success': True,
            'message': 'Task completed successfully',
            'syncing': sync_to_google
        })
    else:
        print(f'[API] Task {task_id} not found')
        return jsonify({
            'success': False,
            'message': 'Task not found'
        }), 404


@api.route('/tasks/<task_id>/incomplete', methods=['POST'])
def api_mark_incomplete(task_id):
    """Mark a completed task as incomplete (pending) with background sync"""
    from datetime import datetime
    data = request.get_json() or {}
    account_id = data.get('account_id', _dashboard_state.get('current_account'))
    sync_to_google = data.get('sync_to_google', True)
    
    print(f'[API] Marking task as incomplete: {task_id}')
    print(f'[API] Account: {account_id}')
    
    # Search in the specified account first, then all accounts
    accounts_to_search = []
    if account_id and account_id in _dashboard_state['tasks']:
        accounts_to_search = [account_id]
    else:
        accounts_to_search = list(_dashboard_state['tasks'].keys())
    
    task_found = False
    
    for acc_id in accounts_to_search:
        tasks = _dashboard_state['tasks'].get(acc_id, [])
        
        for task in tasks:
            if task.get('id') == task_id:
                print(f'[API] Found task: {task_id}')
                
                # Only mark as incomplete if it's currently completed
                if task.get('status') != 'completed':
                    return jsonify({
                        'success': False,
                        'message': 'Task is not completed'
                    }), 400
                
                task_found = True
                
                # Update task in memory
                task['status'] = 'pending'
                task['completed_at'] = None
                task['modified_at'] = datetime.now().isoformat()
                
                # Sync to local SQLite database
                try:
                    db_path = data_manager.gtasks_path / acc_id / 'tasks.db' if data_manager.gtasks_path else None
                    if not db_path or not db_path.exists():
                        db_path = data_manager.gtasks_path / 'tasks.db' if data_manager.gtasks_path else None
                    
                    if db_path and db_path.exists():
                        import sqlite3
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE tasks 
                            SET status = ?, completed_at = ?, modified_at = ?
                            WHERE id = ?
                        """, (
                            'pending',
                            None,
                            datetime.now().isoformat(),
                            task_id
                        ))
                        conn.commit()
                        conn.close()
                        print(f'[API] Task {task_id} marked as incomplete in local database')
                except Exception as e:
                    print(f'[API] Error updating local database: {e}')
                
                # Trigger background sync to Google Tasks (non-blocking)
                if sync_to_google:
                    print(f'[API] Starting background sync to Google Tasks...')
                    updates = {'status': 'pending'}
                    sync_thread = threading.Thread(
                        target=_sync_task_update_to_google_background,
                        args=(task_id, acc_id, updates),
                        daemon=True
                    )
                    sync_thread.start()
                    print(f'[API] Background sync thread started for task {task_id}')
                
                # Trigger background sync to Turso Remote DB (non-blocking)
                print(f'[API] Starting background sync to Turso Remote DB...')
                updates = {'status': 'pending'}
                turso_sync_thread = threading.Thread(
                    target=_sync_task_update_to_turso_background,
                    args=(task_id, acc_id, updates),
                    daemon=True
                )
                turso_sync_thread.start()
                print(f'[API] Background Turso sync thread started for task {task_id}')
                
                break
        
        if task_found:
            break
    
    if task_found:
        return jsonify({
            'success': True,
            'message': 'Task marked as incomplete',
            'syncing': sync_to_google
        })
    else:
        print(f'[API] Task {task_id} not found')
        return jsonify({
            'success': False,
            'message': 'Task not found'
        }), 404


@api.route('/tasks/<task_id>/update', methods=['POST'])
def api_update_task(task_id):
    """Update task details with background sync"""
    from datetime import datetime
    data = request.get_json() or {}
    account_id = data.get('account_id', _dashboard_state.get('current_account'))
    sync_to_google = data.get('sync_to_google', True)
    
    # Valid fields that can be updated
    valid_fields = ['title', 'description', 'due', 'priority', 'status', 'notes', 'due_date']
    
    # Extract updates from request
    updates = {}
    for field in valid_fields:
        if field in data and data[field] is not None:
            updates[field] = data[field]
    
    # Map field names to internal names
    field_mapping = {
        'notes': 'description',
        'due_date': 'due'
    }
    normalized_updates = {}
    for key, value in updates.items():
        normalized_key = field_mapping.get(key, key)
        normalized_updates[normalized_key] = value
    
    # Validate status if provided
    if 'status' in normalized_updates:
        valid_statuses = ['pending', 'in_progress', 'completed']
        if normalized_updates['status'] not in valid_statuses:
            return jsonify({
                'success': False,
                'message': f'Invalid status. Must be one of: {valid_statuses}'
            }), 400
    
    if not normalized_updates:
        return jsonify({
            'success': False,
            'message': 'No valid fields to update'
        }), 400
    
    print(f'[API] Updating task: {task_id}')
    print(f'[API] Updates: {list(normalized_updates.keys())}')
    print(f'[API] Account: {account_id}')
    
    # Search in the specified account first, then all accounts
    accounts_to_search = []
    if account_id and account_id in _dashboard_state['tasks']:
        accounts_to_search = [account_id]
    else:
        accounts_to_search = list(_dashboard_state['tasks'].keys())
    
    task_found = False
    
    for acc_id in accounts_to_search:
        tasks = _dashboard_state['tasks'].get(acc_id, [])
        
        for task in tasks:
            if task.get('id') == task_id:
                print(f'[API] Found task: {task_id}')
                task_found = True
                
                # Apply updates to task
                for key, value in normalized_updates.items():
                    task[key] = value
                
                task['modified_at'] = datetime.now().isoformat()
                
                # Sync to local SQLite database
                try:
                    db_path = data_manager.gtasks_path / acc_id / 'tasks.db' if data_manager.gtasks_path else None
                    if not db_path or not db_path.exists():
                        db_path = data_manager.gtasks_path / 'tasks.db' if data_manager.gtasks_path else None
                    
                    if db_path and db_path.exists():
                        import sqlite3
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        
                        # Build dynamic UPDATE query
                        set_clauses = ['modified_at = ?']
                        params = [datetime.now().isoformat()]
                        
                        for key in normalized_updates.keys():
                            if key in ['title', 'description', 'due', 'status', 'priority']:
                                set_clauses.append(f'{key} = ?')
                                params.append(normalized_updates[key])
                        
                        params.append(task_id)
                        
                        query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?"
                        cursor.execute(query, params)
                        
                        conn.commit()
                        conn.close()
                        print(f'[API] Task {task_id} updated in local database')
                except Exception as e:
                    print(f'[API] Error updating local database: {e}')
                
                # Trigger background sync to Google Tasks (non-blocking)
                if sync_to_google:
                    print(f'[API] Starting background sync to Google Tasks...')
                    sync_thread = threading.Thread(
                        target=_sync_task_update_to_google_background,
                        args=(task_id, acc_id, normalized_updates),
                        daemon=True
                    )
                    sync_thread.start()
                    print(f'[API] Background sync thread started for task {task_id}')
                
                # Trigger background sync to Turso Remote DB (non-blocking)
                print(f'[API] Starting background sync to Turso Remote DB...')
                turso_sync_thread = threading.Thread(
                    target=_sync_task_update_to_turso_background,
                    args=(task_id, acc_id, normalized_updates),
                    daemon=True
                )
                turso_sync_thread.start()
                print(f'[API] Background Turso sync thread started for task {task_id}')
                
                break
        
        if task_found:
            break
    
    if task_found:
        return jsonify({
            'success': True,
            'message': 'Task updated successfully',
            'updated_fields': list(normalized_updates.keys()),
            'syncing': sync_to_google
        })
    else:
        print(f'[API] Task {task_id} not found')
        return jsonify({
            'success': False,
            'message': 'Task not found'
        }), 404


# ============================================
# ADVANCED SYNC ENDPOINTS
# ============================================

@api.route('/sync/advanced', methods=['POST'])
def api_advanced_sync():
    """
    Start an advanced sync operation.
    
    Request body:
        {
            "sync_type": "push|pull|both" (default: "both"),
            "account": "optional_account_name"
        }
        
    Response:
        {
            "success": True,
            "sync_id": "unique_sync_id",
            "message": "Sync started"
        }
    """
    from services.sync_service import SyncService
    
    try:
        data = request.get_json() or {}
        sync_type = data.get('sync_type', 'both')
        account = data.get('account')
        
        # Validate sync_type
        if sync_type not in ('push', 'pull', 'both'):
            return jsonify({
                'success': False,
                'message': 'Invalid sync_type. Must be "push", "pull", or "both"'
            }), 400
        
        # Start the sync
        sync_id = SyncService.start_advanced_sync(sync_type=sync_type, account=account)
        
        return jsonify({
            'success': True,
            'sync_id': sync_id,
            'message': f'Started {sync_type} sync'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting sync: {str(e)}'
        }), 500


@api.route('/sync/progress')
def api_sync_progress():
    """
    Get the current sync progress.
    
    Query parameters:
        sync_id: Optional sync ID to query (uses current sync if not provided)
        
    Response:
        {
            "success": True,
            "data": {
                "percentage": 0-100,
                "message": "description",
                "status": "running|completed|error|idle",
                "sync_type": "push|pull|both",
                "account": "account_name",
                "start_time": "ISO timestamp",
                "error": "error message if any"
            }
        }
    """
    from services.sync_service import SyncService
    
    try:
        sync_id = request.args.get('sync_id')
        progress = SyncService.get_sync_progress(sync_id=sync_id)
        
        return jsonify({
            'success': True,
            'data': progress
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting sync progress: {str(e)}'
        }), 500


@api.route('/sync/complete', methods=['POST'])
def api_sync_complete():
    """
    Wait for sync to complete and return final status.
    
    Request body:
        {
            "sync_id": "optional_sync_id",
            "timeout": 300 (optional, default 300 seconds)
        }
        
    Response:
        {
            "success": True,
            "data": {
                "percentage": 0-100,
                "message": "description",
                "status": "completed|error|timeout",
                "error": "error message if any"
            }
        }
    """
    from services.sync_service import SyncService
    
    try:
        data = request.get_json() or {}
        sync_id = data.get('sync_id')
        timeout = float(data.get('timeout', 300))
        
        result = SyncService.wait_for_sync_completion(sync_id=sync_id, timeout=timeout)
        
        # Refresh dashboard cache after sync completes
        if result.get('status') == 'completed':
            refresh_dashboard_cache()
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error waiting for sync completion: {str(e)}'
        }), 500


@api.route('/sync/cancel', methods=['POST'])
def api_sync_cancel():
    """
    Cancel a running sync operation.
    
    Request body:
        {
            "sync_id": "optional_sync_id"
        }
        
    Response:
        {
            "success": True,
            "message": "Sync cancelled"
        }
    """
    from services.sync_service import SyncService
    
    try:
        data = request.get_json() or {}
        sync_id = data.get('sync_id')
        
        cancelled = SyncService.cancel_sync(sync_id=sync_id)
        
        if cancelled:
            return jsonify({
                'success': True,
                'message': 'Sync cancelled'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No running sync to cancel'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error cancelling sync: {str(e)}'
        }), 500


@api.route('/sync/status')
def api_sync_status():
    """
    Get the status of all sync operations or check if a specific sync is running.
    
    Query parameters:
        sync_id: Optional sync ID to check
        
    Response:
        {
            "success": True,
            "data": {
                "running": True/False,
                "sync_id": "current_sync_id",
                "all_sync_ids": ["id1", "id2", ...]
            }
        }
    """
    from services.sync_service import SyncService
    
    try:
        sync_id = request.args.get('sync_id')
        is_running = SyncService.is_sync_running(sync_id=sync_id)
        
        return jsonify({
            'success': True,
            'data': {
                'running': is_running,
                'sync_id': sync_id or SyncService._current_sync_id,
                'all_sync_ids': SyncService.get_all_sync_ids()
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting sync status: {str(e)}'
        }), 500


# ============================================
# REMOTE SYNC ENDPOINTS
# ============================================

@api.route('/remote/status')
def api_remote_status():
    """
    Get the status of remote sync feature.
    
    Response:
        {
            "success": True,
            "data": {
                "enabled": True/False,
                "remote_dbs": [...],
                "local_db_exists": True/False,
                "connection_status": "connected|local_only|offline",
                "last_sync": "ISO timestamp or null"
            }
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        status = RemoteSyncService.get_remote_status()
        return jsonify({
            'success': True,
            'data': status
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting remote status: {str(e)}'
        }), 500


@api.route('/remote/databases', methods=['GET'])
def api_remote_databases():
    """
    List all configured remote databases.
    
    Response:
        {
            "success": True,
            "data": [
                {
                    "id": "db_id",
                    "name": "Database Name",
                    "url": "libsql://...",
                    "active": True/False,
                    "last_sync": "ISO timestamp or null"
                },
                ...
            ]
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        databases = RemoteSyncService.list_remote_databases()
        return jsonify({
            'success': True,
            'data': databases
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error listing remote databases: {str(e)}'
        }), 500


@api.route('/remote/databases', methods=['POST'])
def api_add_remote_database():
    """
    Add a new remote database configuration.
    
    Request body:
        {
            "url": "libsql://gtaskssqllite-sirusdas.aws-ap-south-1.turso.io",
            "name": "Optional Database Name",
            "token": "optional_auth_token (or use GTASKS_TURSO_TOKEN env var)"
        }
        
    Response:
        {
            "success": True,
            "data": {
                "id": "new_db_id",
                "name": "Database Name"
            },
            "message": "Database added successfully"
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        data = request.get_json()
        url = data.get('url')
        name = data.get('name')
        token = data.get('token')
        
        if not url:
            return jsonify({
                'success': False,
                'message': 'URL is required'
            }), 400
        
        result = RemoteSyncService.add_remote_db(url, name, token)
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Remote database added successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error adding remote database: {str(e)}'
        }), 500


@api.route('/remote/databases/<db_id>', methods=['DELETE'])
def api_remove_remote_database(db_id):
    """
    Remove a remote database configuration.
    
    Path parameters:
        db_id: Database ID to remove
        
    Response:
        {
            "success": True,
            "message": "Database removed successfully"
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        RemoteSyncService.remove_remote_db(db_id)
        
        return jsonify({
            'success': True,
            'message': 'Remote database removed successfully'
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error removing remote database: {str(e)}'
        }), 500


@api.route('/remote/databases/<db_id>/activate', methods=['POST'])
def api_activate_remote_database(db_id):
    """
    Activate a remote database for sync.
    
    Path parameters:
        db_id: Database ID to activate
        
    Response:
        {
            "success": True,
            "message": "Database activated successfully"
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        RemoteSyncService.activate_remote_db(db_id)
        
        return jsonify({
            'success': True,
            'message': 'Remote database activated successfully'
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error activating remote database: {str(e)}'
        }), 500


@api.route('/remote/databases/<db_id>/deactivate', methods=['POST'])
def api_deactivate_remote_database(db_id):
    """
    Deactivate a remote database for sync.
    
    Path parameters:
        db_id: Database ID to deactivate
        
    Response:
        {
            "success": True,
            "message": "Database deactivated successfully"
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        RemoteSyncService.deactivate_remote_db(db_id)
        
        return jsonify({
            'success': True,
            'message': 'Remote database deactivated successfully'
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deactivating remote database: {str(e)}'
        }), 500


@api.route('/remote/sync', methods=['POST'])
def api_remote_sync():
    """
    Perform a full sync with all active remote databases.
    
    Request body (optional):
        {
            "push": True,  # Push local changes to remote
            "pull": True   # Pull remote changes to local
        }
        
    Response:
        {
            "success": True,
            "data": {
                "sync_id": "unique_sync_id",
                "status": "completed",
                "results": [
                    {
                        "db_id": "...",
                        "db_name": "...",
                        "pushed": 5,
                        "pulled": 3,
                        "conflicts_resolved": 2,
                        "success": True,
                        "error": null
                    },
                    ...
                ]
            },
            "message": "Sync completed successfully"
        }
    """
    from services.remote_sync_service import RemoteSyncService
    from services.sync_service import SyncService
    
    try:
        data = request.get_json() or {}
        push = data.get('push', True)
        pull = data.get('pull', True)
        
        if not push and not pull:
            return jsonify({
                'success': False,
                'message': 'At least one of push or pull must be True'
            }), 400
        
        # Start sync via SyncService for progress tracking
        sync_id = SyncService.start_advanced_sync(sync_type='both', account='remote')
        
        # Perform the actual sync
        result = RemoteSyncService.sync_all(push=pull, pull=pull)
        
        # Refresh dashboard cache after sync completes
        refresh_dashboard_cache()
        
        # Update sync status
        SyncService._sync_results[sync_id] = {
            'status': 'completed',
            'message': f'Synced with {len(result)} remote database(s)',
            'results': result
        }
        
        return jsonify({
            'success': True,
            'data': {
                'sync_id': sync_id,
                'status': 'completed',
                'results': result
            },
            'message': 'Remote sync completed successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error syncing with remote databases: {str(e)}'
        }), 500


@api.route('/remote/push', methods=['POST'])
def api_remote_push():
    """
    Push local changes to remote databases.
    
    Request body (optional):
        {
            "db_id": "specific_db_id"  # Push to specific DB, or all if not provided
        }
        
    Response:
        {
            "success": True,
            "data": {
                "results": [
                    {
                        "db_id": "...",
                        "db_name": "...",
                        "pushed": 5,
                        "success": True,
                        "error": null
                    },
                    ...
                ]
            },
            "message": "Push completed successfully"
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        data = request.get_json() or {}
        db_id = data.get('db_id')
        
        if db_id:
            result = RemoteSyncService.push_to_remote(db_id)
            results = [result]
        else:
            results = RemoteSyncService.push_all()
        
        # Refresh dashboard cache after push completes
        refresh_dashboard_cache()
        
        return jsonify({
            'success': True,
            'data': {'results': results},
            'message': 'Push to remote databases completed'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error pushing to remote databases: {str(e)}'
        }), 500


@api.route('/remote/pull', methods=['POST'])
def api_remote_pull():
    """
    Pull remote changes to local database.
    
    Request body (optional):
        {
            "db_id": "specific_db_id"  # Pull from specific DB, or all if not provided
        }
        
    Response:
        {
            "success": True,
            "data": {
                "results": [
                    {
                        "db_id": "...",
                        "db_name": "...",
                        "pulled": 3,
                        "success": True,
                        "error": null
                    },
                    ...
                ]
            },
            "message": "Pull completed successfully"
        }
    """
    from services.remote_sync_service import RemoteSyncService
    
    try:
        data = request.get_json() or {}
        db_id = data.get('db_id')
        
        if db_id:
            result = RemoteSyncService.pull_from_remote(db_id)
            results = [result]
        else:
            results = RemoteSyncService.pull_all()
        
        # Refresh dashboard cache after pull completes
        refresh_dashboard_cache()
        
        return jsonify({
            'success': True,
            'data': {'results': results},
            'message': 'Pull from remote databases completed'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error pulling from remote databases: {str(e)}'
        }), 500


@api.route('/remote/sync-command', methods=['POST'])
def api_remote_sync_command():
    """
    Execute 'gtasks remote sync' command in a background thread.
    
    This endpoint runs the CLI command and returns immediately.
    The command output will appear in the terminal where the dashboard is running.
    
    Response:
        {
            "success": True,
            "message": "Remote sync command started in background"
        }
    """
    import subprocess
    import threading
    
    try:
        def run_gtasks_remote_sync():
            """Background function to run gtasks remote sync command."""
            try:
                print('[Remote Sync] Starting gtasks remote sync...')
                result = subprocess.run(
                    ['gtasks', 'remote', 'sync'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                print(f'[Remote Sync] Command completed with return code: {result.returncode}')
                if result.stdout:
                    print(f'[Remote Sync] Output: {result.stdout}')
                if result.stderr:
                    print(f'[Remote Sync] Errors: {result.stderr}')
            except subprocess.TimeoutExpired:
                print('[Remote Sync] Command timed out after 5 minutes')
            except Exception as e:
                print(f'[Remote Sync] Error executing command: {e}')
        
        # Start the command in a background thread
        thread = threading.Thread(target=run_gtasks_remote_sync, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Remote sync command started in background'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting remote sync: {str(e)}'
        }), 500


@api.route('/remote/tasks', methods=['GET'])
def api_remote_load_tasks():
    """
    Load tasks from remote database when local DB is missing.
    
    Query parameters:
        db_id: Optional specific database ID
        
    Response:
        {
            "success": True,
            "data": {
                "tasks": [...],
                "source": "remote_db_name",
                "loaded_from": "remote"
            }
        }
    """
    from services.remote_sync_service import RemoteSyncService
    from models.task import Task
    
    try:
        db_id = request.args.get('db_id')
        
        if db_id:
            tasks = RemoteSyncService.load_tasks_from_remote(db_id)
        else:
            tasks = RemoteSyncService.load_tasks_from_any_remote()
        
        return jsonify({
            'success': True,
            'data': {
                'tasks': [t.to_dict() if hasattr(t, 'to_dict') else t for t in tasks],
                'source': 'remote',
                'loaded_from': 'remote'
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading tasks from remote: {str(e)}'
        }), 500


# ============================================
# TASK CREATION ENDPOINTS
# ============================================

@api.route('/tasks/create', methods=['POST'])
def api_create_task():
    """
    Create a new task.
    
    Request body:
        {
            "title": "Task title",
            "notes": "Optional task description",
            "due_date": "YYYY-MM-DD or null",
            "priority": "none|low|medium|high|critical",
            "status": "pending|in_progress|completed",
            "tags": ["@account1", "#tag2"],
            "account_id": "account_id",
            "task_list_id": "task_list_id"
        }
        
    Response:
        {
            "success": True,
            "task_id": "new_task_id",
            "message": "Task created successfully"
        }
    """
    from datetime import datetime
    import uuid
    from models.task import Task, TaskStatus
    
    try:
        data = request.get_json()
        
        # Validate required fields
        title = data.get('title', '').strip()
        if not title:
            return jsonify({
                'success': False,
                'message': 'Task title is required'
            }), 400
        
        # Get account and task list
        account_id = data.get('account_id') or _dashboard_state.get('current_account')
        task_list_id = data.get('task_list_id')
        
        if not account_id:
            return jsonify({
                'success': False,
                'message': 'Account ID is required'
            }), 400
        
        if not task_list_id:
            return jsonify({
                'success': False,
                'message': 'Task list ID is required'
            }), 400
        
        # Create new task
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Parse status
        status_str = data.get('status', 'pending')
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.PENDING
        
        # Parse priority
        priority = data.get('priority', 'none')
        
        # Create task data
        task_data = {
            'id': task_id,
            'title': title,
            'description': data.get('notes', ''),
            'due': data.get('due_date'),
            'status': status.value,
            'priority': priority,
            'calculated_priority': priority,
            'tasklist_id': task_list_id,
            'account_id': account_id,
            'created_at': now,
            'modified_at': now,
            'completed_at': None,
            'is_deleted': False,
            'tags': data.get('tags', [])
        }
        
        # Add to in-memory state
        if account_id not in _dashboard_state['tasks']:
            _dashboard_state['tasks'][account_id] = []
        
        _dashboard_state['tasks'][account_id].append(task_data)
        
        # Save to local SQLite database
        try:
            import sqlite3
            from pathlib import Path
            
            # Find the database path
            db_path = None
            gtasks_path = data_manager.gtasks_path
            if gtasks_path:
                db_path = gtasks_path / account_id / 'tasks.db'
                if not db_path.exists():
                    db_path = gtasks_path / 'tasks.db'
            
            if db_path and db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Insert new task
                cursor.execute("""
                    INSERT INTO tasks (
                        id, title, description, due, status, priority,
                        calculated_priority, tasklist_id, account_id,
                        created_at, modified_at, completed_at, is_deleted, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_data['id'],
                    task_data['title'],
                    task_data['description'],
                    task_data['due'],
                    task_data['status'],
                    task_data['priority'],
                    task_data['calculated_priority'],
                    task_data['tasklist_id'],
                    task_data['account_id'],
                    task_data['created_at'],
                    task_data['modified_at'],
                    task_data['completed_at'],
                    0,  # is_deleted
                    ','.join(task_data['tags']) if task_data['tags'] else ''
                ))
                
                conn.commit()
                conn.close()
                print(f'[API] Task {task_id} saved to local database')
        except Exception as e:
            print(f'[API] Error saving task to local database: {e}')
        
        # Process @account tags if present
        tags = data.get('tags', [])
        account_tags = [tag for tag in tags if tag.startswith('@')]
        
        if account_tags:
            try:
                from gtasks_cli.services.account_tag_service import AccountTagService
                from gtasks_cli.services.task_sharing_service import TaskSharingService
                
                account_tag_service = AccountTagService()
                task_sharing_service = TaskSharingService()
                
                for tag in account_tags:
                    tag_name = tag[1:]  # Remove @ prefix
                    
                    # Get or create account tag mapping
                    account_tag_service.get_or_create_account_tag(
                        user_id=session.get('user_id') if 'user_id' in dir() else None,
                        tag_name=tag_name,
                        email=f"{tag_name}@example.com"  # Placeholder
                    )
                    
                    # Share task with the account
                    task_sharing_service.share_task_with_user(
                        task_id=task_id,
                        user_id=tag_name,
                        shared_by=session.get('user_id') if 'user_id' in dir() else None
                    )
                    
            except Exception as e:
                print(f'[API] Error processing account tags: {e}')
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Task created successfully'
        })
        
    except Exception as e:
        print(f'[API] Error creating task: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating task: {str(e)}'
        }), 500


# ============================================
# INVITATION ENDPOINTS
# ============================================

@api.route('/invitations', methods=['GET'])
def api_invitations():
    """
    Get all invitations for the current user (both sent and received).

    Query parameters:
        status: Filter by status (pending, accepted, declined)

    Response:
        {
            "success": True,
            "data": {
                "received": [...],
                "sent": [...]
            }
        }
    """
    try:
        invitations = _dashboard_state.get('invitations', [])
        status_filter = request.args.get('status')

        current_email = session.get('email') or 'current@example.com'
        current_user = session.get('user_id') or 'current_user'

        received = []
        sent = []

        for inv in invitations:
            # Apply status filter if provided
            if status_filter and inv['status'] != status_filter:
                continue

            inv_data = {
                'id': inv['id'],
                'from_user': f"@{inv['from_user']}" if not inv['from_user'].startswith('@') else inv['from_user'],
                'from_email': inv['from_email'],
                'to_email': inv['email'],
                'message': inv.get('message', ''),
                'task_id': inv.get('task_id'),
                'status': inv['status'],
                'created_at': inv['created_at']
            }

            # Check if current user received this invitation
            if inv['email'] == current_email:
                received.append(inv_data)

            # Check if current user sent this invitation
            if inv['from_email'] == current_email or inv['from_user'] == current_user:
                sent.append(inv_data)

        return jsonify({
            'success': True,
            'data': {
                'received': received,
                'sent': sent
            }
        })

    except Exception as e:
        print(f'[API] Error getting invitations: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting invitations: {str(e)}'
        }), 500


@api.route('/invitations/send', methods=['POST'])
def api_send_invitation():
    """
    Send an invitation to connect with a user.

    Request body:
        {
            "email": "user@example.com",
            "message": "Optional message",
            "task_id": "optional_task_id to share",
            "tag": "@tag_name"
        }

    Response:
        {
            "success": True,
            "invitation_id": "inv_id",
            "message": "Invitation sent successfully"
        }
    """
    import uuid

    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        tag = data.get('tag', '').strip()

        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400

        # Generate unique invitation ID
        invitation_id = str(uuid.uuid4())

        # Create invitation record
        invitation = {
            'id': invitation_id,
            'email': email,
            'tag': tag,
            'from_user': session.get('user_id') or 'current_user',
            'from_email': session.get('email') or 'current@example.com',
            'message': data.get('message', ''),
            'task_id': data.get('task_id'),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'expires_at': None
        }

        # Store invitation (in-memory for now)
        if 'invitations' not in _dashboard_state:
            _dashboard_state['invitations'] = []

        _dashboard_state['invitations'].append(invitation)

        # TODO: Send actual email via QERDS API or SMTP
        print(f'[API] Invitation sent to {email} (ID: {invitation_id}, Tag: {tag})')

        return jsonify({
            'success': True,
            'invitation_id': invitation_id,
            'message': f'Invitation sent to {email}'
        })

    except Exception as e:
        print(f'[API] Error sending invitation: {e}')
        return jsonify({
            'success': False,
            'message': f'Error sending invitation: {str(e)}'
        }), 500


@api.route('/invitations/accept/<invitation_id>', methods=['POST'])
def api_accept_invitation(invitation_id):
    """
    Accept an invitation.
    
    Path parameters:
        invitation_id: ID of the invitation to accept
        
    Response:
        {
            "success": True,
            "message": "Invitation accepted"
        }
    """
    try:
        invitations = _dashboard_state.get('invitations', [])
        invitation = next((i for i in invitations if i['id'] == invitation_id), None)
        
        if not invitation:
            return jsonify({
                'success': False,
                'message': 'Invitation not found'
            }), 404
        
        if invitation['status'] != 'pending':
            return jsonify({
                'success': False,
                'message': f'Invitation already {invitation["status"]}'
            }), 400
        
        # Update invitation status
        invitation['status'] = 'accepted'
        invitation['accepted_at'] = datetime.now().isoformat()
        
        # Create connection between users
        if 'connections' not in _dashboard_state:
            _dashboard_state['connections'] = []
        
        connection = {
            'id': str(uuid.uuid4()),
            'from_user': invitation['from_user'],
            'to_user': session.get('user_id') or invitation['email'].split('@')[0],
            'to_email': invitation['email'],
            'created_at': datetime.now().isoformat()
        }
        _dashboard_state['connections'].append(connection)
        
        print(f'[API] Invitation {invitation_id} accepted')
        
        return jsonify({
            'success': True,
            'message': 'Invitation accepted successfully'
        })
        
    except Exception as e:
        print(f'[API] Error accepting invitation: {e}')
        return jsonify({
            'success': False,
            'message': f'Error accepting invitation: {str(e)}'
        }), 500


@api.route('/connected-accounts', methods=['GET'])
def api_connected_accounts():
    """
    Get all connected accounts (for @account tag autocomplete).

    Response:
        {
            "success": True,
            "data": [
                {"tag": "@john", "email": "john@example.com"},
                {"tag": "@jane", "email": "jane@example.com"}
            ]
        }
    """
    try:
        connections = _dashboard_state.get('connections', [])

        accounts = []
        for conn in connections:
            # Generate tag from email or user ID
            tag = conn['to_email'].split('@')[0] if '@' in conn['to_email'] else conn['to_user']
            accounts.append({
                'tag': f'@{tag}',
                'email': conn['to_email']
            })

        return jsonify({
            'success': True,
            'data': accounts
        })

    except Exception as e:
        print(f'[API] Error getting connected accounts: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting connected accounts: {str(e)}'
        }), 500


@api.route('/invitations/pending', methods=['GET'])
def api_pending_invitations():
    """
    Get pending invitations for the current user.

    Response:
        {
            "success": True,
            "data": [
                {
                    "id": "inv_id",
                    "from_user": "@john",
                    "from_email": "john@example.com",
                    "message": "Join me on tasks",
                    "task_id": "task_123",
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
    """
    try:
        invitations = _dashboard_state.get('invitations', [])

        # Filter pending invitations for current user
        current_user = session.get('user_id') or 'current_user'
        current_email = session.get('email') or 'current@example.com'

        pending = []
        for inv in invitations:
            if inv['status'] == 'pending' and inv['email'] == current_email:
                pending.append({
                    'id': inv['id'],
                    'from_user': f"@{inv['from_user']}" if not inv['from_user'].startswith('@') else inv['from_user'],
                    'from_email': inv['from_email'],
                    'message': inv['message'],
                    'task_id': inv.get('task_id'),
                    'created_at': inv['created_at']
                })

        return jsonify({
            'success': True,
            'data': pending
        })

    except Exception as e:
        print(f'[API] Error getting pending invitations: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting pending invitations: {str(e)}'
        }), 500


@api.route('/invitations/<invitation_id>/decline', methods=['POST'])
def api_decline_invitation(invitation_id):
    """
    Decline an invitation.

    Path parameters:
        invitation_id: ID of the invitation to decline

    Response:
        {
            "success": True,
            "message": "Invitation declined"
        }
    """
    try:
        invitations = _dashboard_state.get('invitations', [])
        invitation = next((i for i in invitations if i['id'] == invitation_id), None)

        if not invitation:
            return jsonify({
                'success': False,
                'message': 'Invitation not found'
            }), 404

        if invitation['status'] != 'pending':
            return jsonify({
                'success': False,
                'message': f'Invitation already {invitation["status"]}'
            }), 400

        # Update invitation status
        invitation['status'] = 'declined'
        invitation['declined_at'] = datetime.now().isoformat()

        print(f'[API] Invitation {invitation_id} declined')

        return jsonify({
            'success': True,
            'message': 'Invitation declined successfully'
        })

    except Exception as e:
        print(f'[API] Error declining invitation: {e}')
        return jsonify({
            'success': False,
            'message': f'Error declining invitation: {str(e)}'
        }), 500


@api.route('/tasks/<task_id>/complete-user', methods=['POST'])
def api_complete_task_for_user(task_id):
    """
    Mark a task as complete for a specific user.

    Path parameters:
        task_id: ID of the task

    Request body:
        {
            "user_id": "@john"  # The user completing the task
        }

    Response:
        {
            "success": True,
            "message": "Task marked as complete for user"
        }
    """
    from datetime import datetime

    try:
        data = request.get_json()
        user_id = data.get('user_id', '').strip()

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User ID is required'
            }), 400

        # Normalize user_id (remove @ prefix if present)
        if user_id.startswith('@'):
            user_id = user_id[1:]

        # Find the task
        task_found = False
        for account_tasks in _dashboard_state['tasks'].values():
            for task in account_tasks:
                if task.get('id') == task_id:
                    task_found = True

                    # Initialize completion tracking if not present
                    if 'completion' not in task:
                        task['completion'] = {}

                    # Mark task as complete for this user
                    task['completion'][user_id] = {
                        'completed': True,
                        'at': datetime.now().isoformat()
                    }

                    # Update modified_at
                    task['modified_at'] = datetime.now().isoformat()

                    # TODO: Save to local database
                    print(f'[API] Task {task_id} marked complete for user @{user_id}')

                    break
            if task_found:
                break

        if not task_found:
            return jsonify({
                'success': False,
                'message': 'Task not found'
            }), 404

        return jsonify({
            'success': True,
            'message': f'Task marked as complete for @{user_id}'
        })

    except Exception as e:
        print(f'[API] Error completing task for user: {e}')
        return jsonify({
            'success': False,
            'message': f'Error completing task: {str(e)}'
        }), 500


@api.route('/shared/tasks', methods=['GET'])
def api_shared_tasks():
    """
    Get shared tasks for the current user.
    
    Query parameters:
        type: "shared_with_me" or "shared_by_me"
        status: Filter by completion status (pending, completed)
    
    Response:
        {
            "success": True,
            "data": [...]
        }
    """
    try:
        from gtasks_cli.services.shared_task_access_service import SharedTaskAccessService
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        task_type = request.args.get('type', 'shared_with_me')
        status_filter = request.args.get('status')
        
        # Get current user info
        current_user_id = session.get('user_id') or 'current_user'
        current_email = session.get('email')
        
        access_service = SharedTaskAccessService()
        
        if task_type == 'shared_by_me':
            tasks = access_service.get_tasks_shared_by_user(current_user_id)
        else:
            tasks_data = access_service.get_shared_tasks_for_user(current_user_id, current_email)
            tasks = [{
                'task_id': t.task_id,
                'task_title': t.task_title,
                'original_account_id': t.original_account_id,
                'owner_user_id': t.owner_user_id,
                'shared_at': t.shared_at,
                'completion_status': t.completion_status,
                'completed_at': t.completed_at,
                'task_data': t.task_data
            } for t in tasks_data]
        
        # Apply status filter
        if status_filter:
            if task_type == 'shared_with_me':
                tasks = [t for t in tasks if t.get('completion_status') == status_filter]
            else:
                # For shared_by_me, filter by overall task status
                tasks = [t for t in tasks if t.get('status') == status_filter]
        
        return jsonify({
            'success': True,
            'data': tasks
        })
        
    except Exception as e:
        print(f'[API] Error getting shared tasks: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error getting shared tasks: {str(e)}'
        }), 500


@api.route('/shared/tasks/<task_id>/complete', methods=['POST'])
def api_complete_shared_task(task_id):
    """
    Mark a shared task as complete for the current user.
    
    Path parameters:
        task_id: ID of the task
    
    Request body:
        {
            "original_account_id": "account_id"
        }
    
    Response:
        {
            "success": True,
            "message": "Task marked as complete"
        }
    """
    try:
        from gtasks_cli.services.shared_task_access_service import SharedTaskAccessService
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        data = request.get_json() or {}
        original_account_id = data.get('original_account_id')
        
        if not original_account_id:
            return jsonify({
                'success': False,
                'message': 'original_account_id is required'
            }), 400
        
        current_user_id = session.get('user_id') or 'current_user'
        
        access_service = SharedTaskAccessService()
        result = access_service.mark_task_complete(current_user_id, task_id, original_account_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Task marked as complete'
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        print(f'[API] Error completing shared task: {e}')
        return jsonify({
            'success': False,
            'message': f'Error completing task: {str(e)}'
        }), 500


@api.route('/shared/stats', methods=['GET'])
def api_shared_stats():
    """
    Get statistics about shared tasks.
    
    Response:
        {
            "success": True,
            "data": {
                "shared_with_me_count": 5,
                "shared_by_me_count": 3,
                "pending_completion": 2,
                "completed": 3,
                "total_accounts_shared_with": 4
            }
        }
    """
    try:
        from gtasks_cli.services.shared_task_access_service import SharedTaskAccessService
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        current_user_id = session.get('user_id') or 'current_user'
        
        access_service = SharedTaskAccessService()
        stats = access_service.get_statistics(current_user_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        print(f'[API] Error getting shared stats: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting statistics: {str(e)}'
        }), 500


# ============================================
# INVITATION WORKFLOW ENDPOINTS
# ============================================

@api.route('/invitations/create', methods=['POST'])
def api_create_invitation():
    """
    Create and send an invitation using the InvitationWorkflowManager.
    
    Request body:
        {
            "to_email": "user@example.com",
            "task_id": "optional_task_id",
            "task_title": "optional_task_title",
            "message": "optional_message"
        }
    
    Response:
        {
            "success": True,
            "invitation_id": "inv_...",
            "message": "Invitation created successfully"
        }
    """
    try:
        from gtasks_cli.services.invitation_workflow_manager import (
            InvitationWorkflowManager,
            InvitationRequest
        )
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        data = request.get_json()
        to_email = data.get('to_email', '').strip()
        
        if not to_email:
            return jsonify({
                'success': False,
                'message': 'to_email is required'
            }), 400
        
        current_user_id = session.get('user_id') or 'current_user'
        current_email = session.get('email') or 'current@example.com'
        
        # Create invitation request
        request_data = InvitationRequest(
            from_user_id=current_user_id,
            from_user_email=current_email,
            to_email=to_email,
            task_id=data.get('task_id'),
            task_title=data.get('task_title'),
            message=data.get('message')
        )
        
        workflow_manager = InvitationWorkflowManager()
        result = workflow_manager.create_invitation(request_data)
        
        if result.success:
            return jsonify({
                'success': True,
                'invitation_id': result.invitation_id,
                'message': result.message
            })
        else:
            return jsonify({
                'success': False,
                'message': result.message
            }), 400
            
    except Exception as e:
        print(f'[API] Error creating invitation: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating invitation: {str(e)}'
        }), 500


@api.route('/invitations/accept/<invitation_id>', methods=['POST'])
def api_accept_invitation_workflow(invitation_id):
    """
    Accept an invitation using the InvitationWorkflowManager.
    
    Path parameters:
        invitation_id: ID of the invitation to accept
    
    Response:
        {
            "success": True,
            "connection_id": "conn_...",
            "message": "Connection created successfully"
        }
    """
    try:
        from gtasks_cli.services.invitation_workflow_manager import InvitationWorkflowManager
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        current_user_id = session.get('user_id') or 'current_user'
        current_email = session.get('email') or 'current@example.com'
        
        workflow_manager = InvitationWorkflowManager()
        result = workflow_manager.process_acceptance(invitation_id, current_user_id, current_email)
        
        if result.success:
            return jsonify({
                'success': True,
                'connection_id': result.connection_id,
                'message': result.message
            })
        else:
            return jsonify({
                'success': False,
                'message': result.message
            }), 400
            
    except Exception as e:
        print(f'[API] Error accepting invitation: {e}')
        return jsonify({
            'success': False,
            'message': f'Error accepting invitation: {str(e)}'
        }), 500


@api.route('/invitations/sent', methods=['GET'])
def api_sent_invitations():
    """
    Get all invitations sent by the current user.
    
    Response:
        {
            "success": True,
            "data": [...]
        }
    """
    try:
        from gtasks_cli.services.invitation_workflow_manager import InvitationWorkflowManager
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        current_user_id = session.get('user_id') or 'current_user'
        
        workflow_manager = InvitationWorkflowManager()
        invitations = workflow_manager.get_sent_invitations(current_user_id)
        
        return jsonify({
            'success': True,
            'data': invitations
        })
        
    except Exception as e:
        print(f'[API] Error getting sent invitations: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting invitations: {str(e)}'
        }), 500


@api.route('/invitations/pending', methods=['GET'])
def api_pending_invitations_workflow():
    """
    Get pending invitations for the current user's email.
    
    Response:
        {
            "success": True,
            "data": [...]
        }
    """
    try:
        from gtasks_cli.services.invitation_workflow_manager import InvitationWorkflowManager
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        current_email = session.get('email') or 'current@example.com'
        
        workflow_manager = InvitationWorkflowManager()
        invitations = workflow_manager.get_pending_invitations_for_user(current_email)
        
        return jsonify({
            'success': True,
            'data': invitations
        })
        
    except Exception as e:
        print(f'[API] Error getting pending invitations: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting invitations: {str(e)}'
        }), 500


# ============================================
# ACCOUNT TAG ENDPOINTS
# ============================================

@api.route('/account-tags/detect', methods=['POST'])
def api_detect_account_tags():
    """
    Detect account tags in task text.
    
    Request body:
        {
            "text": "Task description with [@account] tags"
        }
    
    Response:
        {
            "success": True,
            "data": {
                "account_tags": ["account1", "account2"]
            }
        }
    """
    try:
        from gtasks_cli.services.account_tag_service import AccountTagService
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'success': False,
                'message': 'text is required'
            }), 400
        
        account_tag_service = AccountTagService()
        account_tags = account_tag_service.extract_account_tags(text)
        
        return jsonify({
            'success': True,
            'data': {
                'account_tags': account_tags
            }
        })
        
    except Exception as e:
        print(f'[API] Error detecting account tags: {e}')
        return jsonify({
            'success': False,
            'message': f'Error detecting tags: {str(e)}'
        }), 500


@api.route('/account-tags/validate', methods=['POST'])
def api_validate_account_tags():
    """
    Validate if a user can be contacted at an email.
    
    Request body:
        {
            "account_tag": "account_name",
            "email": "user@example.com"
        }
    
    Response:
        {
            "success": True,
            "data": {
                "valid": True,
                "message": "Email matches account"
            }
        }
    """
    try:
        from gtasks_cli.services.account_tag_service import AccountTagService
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        data = request.get_json()
        account_tag = data.get('account_tag', '').strip()
        email = data.get('email', '').strip()
        
        if not account_tag or not email:
            return jsonify({
                'success': False,
                'message': 'account_tag and email are required'
            }), 400
        
        # Remove @ prefix if present
        if account_tag.startswith('@'):
            account_tag = account_tag[1:]
        
        account_tag_service = AccountTagService()
        is_valid = account_tag_service.validate_account_contact(account_tag, email)
        
        if is_valid:
            return jsonify({
                'success': True,
                'data': {
                    'valid': True,
                    'message': 'Email matches account'
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'valid': False,
                    'message': 'Email does not match account. An invitation will be sent.'
                }
            })
        
    except Exception as e:
        print(f'[API] Error validating account tag: {e}')
        return jsonify({
            'success': False,
            'message': f'Error validating: {str(e)}'
        }), 500


# ============================================
# USER ID ENDPOINTS
# ============================================

@api.route('/user/id', methods=['GET'])
def api_user_id():
    """
    Get user ID information for the current user.
    
    Response:
        {
            "success": True,
            "data": {
                "user_id": "abc12345",
                "email": "abc@gmail.com",
                "account_name": "abc"
            }
        }
    """
    try:
        from gtasks_cli.utils.user_id_generator import UserIDGenerator
        
        import sys
        from pathlib import Path
        
        # Add gtasks_cli to path
        gtasks_cli_path = Path(__file__).parent.parent.parent / 'gtasks_cli' / 'src'
        if str(gtasks_cli_path) not in sys.path:
            sys.path.insert(0, str(gtasks_cli_path))
        
        current_user_id = session.get('user_id')
        current_email = session.get('email')
        
        if not current_user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        # Extract account name from user ID
        account_name = UserIDGenerator.extract_account_name(current_user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': current_user_id,
                'email': current_email,
                'account_name': account_name
            }
        })
        
    except Exception as e:
        print(f'[API] Error getting user ID: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting user info: {str(e)}'
        }), 500
