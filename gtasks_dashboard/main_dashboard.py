#!/usr/bin/env python3
"""
GTasks Dashboard - Main Entry Point

A modular, consolidated dashboard following Single Source of Truth principles.
Features are controlled by FEATURE_FLAGS in config.py instead of duplicate files.

Run: python main_dashboard.py

Author: GTasks Dashboard Team
Date: January 12, 2026
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, redirect, request, render_template, session, jsonify

# Import feature flags to display available features
from config import FEATURE_FLAGS

# Create Flask app
app = Flask(__name__,
    template_folder='templates',
    static_folder='static'
)

# Import BASE_PATH from routes
from routes.dashboard import BASE_PATH

# Configure Flask for subpath deployment using SCRIPT_NAME
# This allows Flask to properly route requests when deployed behind a proxy at a subpath
@app.before_request
def set_script_name():
    """Set SCRIPT_NAME for subpath deployment"""
    # Get the base path from environment or use default
    script_name = os.environ.get('SCRIPT_NAME', BASE_PATH)
    if script_name:
        request.environ['SCRIPT_NAME'] = script_name


# Register blueprints
from routes.api import api, init_dashboard_state
from routes.dashboard import dashboard

# Set URL prefix for API blueprint
api.url_prefix = f"{BASE_PATH}/api"

app.register_blueprint(api)
app.register_blueprint(dashboard)

# Initialize dashboard state (load accounts and tasks)
init_dashboard_state()


# Root route - redirect to subpath or serve at root for local dev
@app.route('/')
def index():
    """Root route - serve dashboard with empty base_path for local dev"""
    from routes.dashboard import render_dashboard
    # Use empty base_path for local development (no subpath)
    return render_dashboard(view='dashboard', base_path='')


@app.route('/dashboard')
def dashboard_page_local():
    """Dashboard page - explicit route for dashboard view (local development)"""
    from routes.dashboard import render_dashboard
    return render_dashboard(view='dashboard', base_path='')


@app.route('/hierarchy')
def hierarchy_page_local():
    """Hierarchy page - shows hierarchical task visualization (local development)"""
    from routes.dashboard import render_dashboard
    return render_dashboard(view='hierarchy', base_path='')


@app.route('/tasks')
def tasks_page_local():
    """Tasks page - shows task management view (local development)"""
    from routes.dashboard import render_dashboard
    return render_dashboard(view='tasks', base_path='')


@app.route('/tags')
def tags_page_local():
    """Tags page - shows tags management view (local development)"""
    return render_template('tags.html', base_path='')


@app.route('/favicon.ico')
def favicon_local():
    """Serve favicon as SVG data URI (local development)"""
    import base64
    svg_favicon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" rx="20" fill="#3b82f6"/>
        <text x="50" y="65" font-size="50" text-anchor="middle" fill="white">✓</text>
    </svg>'''
    from flask import Response
    return Response(
        f'data:image/svg+xml;base64,{base64.b64encode(svg_favicon.encode()).decode()}',
        mimetype='image/svg+xml'
    )


@app.route('/sw.js')
def service_worker_local():
    """Serve service worker (local development)"""
    from flask import send_from_directory
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')


# Root API routes for subpath deployment - use BASE_PATH
from flask import jsonify, request

@app.route(f'{BASE_PATH}/api/data')
def api_data_local():
    """Get all dashboard data"""
    from routes.api import api_data
    return api_data()

@app.route(f'{BASE_PATH}/api/refresh', methods=['POST'])
def api_refresh_local():
    """Refresh the dashboard cache"""
    from routes.api import api_refresh_cache
    return api_refresh_cache()

@app.route(f'{BASE_PATH}/api/tasks')
def api_tasks_local():
    """Get tasks with optional filters"""
    from routes.api import api_tasks
    return api_tasks()

@app.route(f'{BASE_PATH}/api/accounts')
def api_accounts_local():
    """Get all accounts"""
    from routes.api import api_accounts
    return api_accounts()

@app.route(f'{BASE_PATH}/api/accounts/<account_id>/switch', methods=['POST'])
def switch_account_local(account_id):
    """Switch to a different account"""
    from routes.api import switch_account
    return switch_account(account_id)

@app.route(f'{BASE_PATH}/api/stats')
def api_stats_local():
    """Get dashboard statistics"""
    from routes.api import api_stats
    return api_stats()

@app.route(f'{BASE_PATH}/api/hierarchy')
def api_hierarchy_local():
    """Get hierarchy visualization data"""
    from routes.api import api_hierarchy
    return api_hierarchy()

@app.route(f'{BASE_PATH}/api/hierarchy/filtered')
def api_hierarchy_filtered_local():
    """Get filtered hierarchy visualization data"""
    from routes.api import api_hierarchy_filtered
    return api_hierarchy_filtered()

@app.route(f'{BASE_PATH}/api/tasks/<task_id>')
def get_task_local(task_id):
    """Get a specific task"""
    from routes.api import get_task
    return get_task(task_id)

@app.route(f'{BASE_PATH}/api/health')
def api_health_local():
    """Health check"""
    from routes.api import api_health
    return api_health()

@app.route(f'{BASE_PATH}/api/tasks/<task_id>/complete', methods=['POST'])
def api_complete_task_local(task_id):
    """Mark a task as completed"""
    from routes.api import api_complete_task
    return api_complete_task(task_id)

@app.route(f'{BASE_PATH}/api/sync/advanced', methods=['POST'])
def api_advanced_sync_local():
    """Start an advanced sync operation"""
    from routes.api import api_advanced_sync
    return api_advanced_sync()

@app.route(f'{BASE_PATH}/api/sync/progress')
def api_sync_progress_local():
    """Get the current sync progress"""
    from routes.api import api_sync_progress
    return api_sync_progress()

@app.route(f'{BASE_PATH}/api/sync/complete', methods=['POST'])
def api_sync_complete_local():
    """Wait for sync to complete"""
    from routes.api import api_sync_complete
    return api_sync_complete()

@app.route(f'{BASE_PATH}/api/sync/cancel', methods=['POST'])
def api_sync_cancel_local():
    """Cancel a running sync operation"""
    from routes.api import api_sync_cancel
    return api_sync_cancel()

@app.route(f'{BASE_PATH}/api/sync/status')
def api_sync_status_local():
    """Get the status of sync operations"""
    from routes.api import api_sync_status
    return api_sync_status()

@app.route(f'{BASE_PATH}/api/remote/status')
def api_remote_status_local():
    """Get the status of remote sync"""
    from routes.api import api_remote_status
    return api_remote_status()

@app.route(f'{BASE_PATH}/api/remote/databases', methods=['GET'])
def api_remote_databases_local():
    """List all configured remote databases"""
    from routes.api import api_remote_databases
    return api_remote_databases()

@app.route(f'{BASE_PATH}/api/remote/databases', methods=['POST'])
def api_add_remote_database_local():
    """Add a new remote database"""
    from routes.api import api_add_remote_database
    return api_add_remote_database()

@app.route(f'{BASE_PATH}/api/remote/databases/<db_id>', methods=['DELETE'])
def api_remove_remote_database_local(db_id):
    """Remove a remote database"""
    from routes.api import api_remove_remote_database
    return api_remove_remote_database(db_id)

@app.route(f'{BASE_PATH}/api/remote/sync', methods=['POST'])
def api_remote_sync_local():
    """Perform a full sync with remote databases"""
    from routes.api import api_remote_sync
    return api_remote_sync()

@app.route(f'{BASE_PATH}/api/remote/push', methods=['POST'])
def api_remote_push_local():
    """Push local changes to remote databases"""
    from routes.api import api_remote_push
    return api_remote_push()

@app.route(f'{BASE_PATH}/api/remote/pull', methods=['POST'])
def api_remote_pull_local():
    """Pull remote changes to local database"""
    from routes.api import api_remote_pull
    return api_remote_pull()


@app.route(f'{BASE_PATH}/api/remote/sync-command', methods=['POST'])
def api_remote_sync_command_local():
    """Execute gtasks remote sync command in background"""
    from routes.api import api_remote_sync_command
    return api_remote_sync_command()


@app.route(f'{BASE_PATH}/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return app.send_static_file(filename)


# ============================================
# Root-level API routes for LOCAL DEVELOPMENT (no subpath)
# These enable testing at http://localhost:8081/api/...
# ============================================

@app.route('/api/data')
def api_data_root():
    """Get all dashboard data (local development)"""
    from routes.api import api_data
    return api_data()

@app.route('/api/refresh', methods=['POST'])
def api_refresh_root():
    """Refresh the dashboard cache (local development)"""
    from routes.api import api_refresh_cache
    return api_refresh_cache()

@app.route('/api/tasks')
def api_tasks_root():
    """Get tasks with optional filters (local development)"""
    from routes.api import api_tasks
    return api_tasks()

@app.route('/api/accounts')
def api_accounts_root():
    """Get all accounts (local development)"""
    from routes.api import api_accounts
    return api_accounts()

@app.route('/api/accounts/<account_id>/switch', methods=['POST'])
def switch_account_root(account_id):
    """Switch to a different account (local development)"""
    from routes.api import switch_account
    return switch_account(account_id)

@app.route('/api/stats')
def api_stats_root():
    """Get dashboard statistics (local development)"""
    from routes.api import api_stats
    return api_stats()

@app.route('/api/hierarchy')
def api_hierarchy_root():
    """Get hierarchy visualization data (local development)"""
    from routes.api import api_hierarchy
    return api_hierarchy()

@app.route('/api/hierarchy/filtered')
def api_hierarchy_filtered_root():
    """Get filtered hierarchy visualization data (local development)"""
    from routes.api import api_hierarchy_filtered
    return api_hierarchy_filtered()

@app.route('/api/tasks/<task_id>')
def get_task_root(task_id):
    """Get a specific task (local development)"""
    from routes.api import get_task
    return get_task(task_id)

@app.route('/api/health')
def api_health_root():
    """Health check (local development)"""
    from routes.api import api_health
    return api_health()

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def api_complete_task_root(task_id):
    """Mark a task as completed (local development)"""
    from routes.api import api_complete_task
    return api_complete_task(task_id)

@app.route('/api/sync/advanced', methods=['POST'])
def api_advanced_sync_root():
    """Start an advanced sync operation (local development)"""
    from routes.api import api_advanced_sync
    return api_advanced_sync()

@app.route('/api/sync/progress')
def api_sync_progress_root():
    """Get the current sync progress (local development)"""
    from routes.api import api_sync_progress
    return api_sync_progress()

@app.route('/api/sync/complete', methods=['POST'])
def api_sync_complete_root():
    """Wait for sync to complete (local development)"""
    from routes.api import api_sync_complete
    return api_sync_complete()

@app.route('/api/sync/cancel', methods=['POST'])
def api_sync_cancel_root():
    """Cancel a running sync operation (local development)"""
    from routes.api import api_sync_cancel
    return api_sync_cancel()

@app.route('/api/sync/status')
def api_sync_status_root():
    """Get the status of sync operations (local development)"""
    from routes.api import api_sync_status
    return api_sync_status()

@app.route('/api/remote/status')
def api_remote_status_root():
    """Get the status of remote sync (local development)"""
    from routes.api import api_remote_status
    return api_remote_status()

@app.route('/api/remote/databases', methods=['GET'])
def api_remote_databases_root():
    """List all configured remote databases (local development)"""
    from routes.api import api_remote_databases
    return api_remote_databases()

@app.route('/api/remote/databases', methods=['POST'])
def api_add_remote_database_root():
    """Add a new remote database (local development)"""
    from routes.api import api_add_remote_database
    return api_add_remote_database()

@app.route('/api/remote/databases/<db_id>', methods=['DELETE'])
def api_remove_remote_database_root(db_id):
    """Remove a remote database (local development)"""
    from routes.api import api_remove_remote_database
    return api_remove_remote_database(db_id)

@app.route('/api/remote/sync', methods=['POST'])
def api_remote_sync_root():
    """Perform a full sync with remote databases (local development)"""
    from routes.api import api_remote_sync
    return api_remote_sync()

@app.route('/api/remote/push', methods=['POST'])
def api_remote_push_root():
    """Push local changes to remote databases (local development)"""
    from routes.api import api_remote_push
    return api_remote_push()

@app.route('/api/remote/pull', methods=['POST'])
def api_remote_pull_root():
    """Pull remote changes to local database (local development)"""
    from routes.api import api_remote_pull
    return api_remote_pull()

@app.route('/api/remote/sync-command', methods=['POST'])
def api_remote_sync_command_root():
    """Execute gtasks remote sync command in background (local development)"""
    from routes.api import api_remote_sync_command
    return api_remote_sync_command()

@app.route('/api/remote/tasks', methods=['GET'])
def api_remote_load_tasks_root():
    """Load tasks from remote database (local development)"""
    from routes.api import api_remote_load_tasks
    return api_remote_load_tasks()

@app.route('/api/account-types')
def api_account_types_root():
    """Get all account types (local development)"""
    from routes.api import api_account_types
    return api_account_types()

@app.route('/api/available-tags')
def api_available_tags_root():
    """Get all available tags (local development)"""
    from routes.api import api_available_tags
    return api_available_tags()

@app.route('/api/priority-stats')
def api_priority_stats_root():
    """Get priority statistics (local development)"""
    from routes.api import api_priority_stats
    return api_priority_stats()

@app.route('/api/tags/parse-filter', methods=['POST'])
def api_parse_tag_filter_root():
    """Parse tag filter string (local development)"""
    from routes.api import api_parse_tag_filter
    return api_parse_tag_filter()

@app.route('/api/tasks/due-today')
def api_tasks_due_today_root():
    """Get tasks due today (local development)"""
    from routes.api import api_tasks_due_today
    return api_tasks_due_today()

@app.route('/api/settings', methods=['GET'])
def api_get_settings_root():
    """Get dashboard settings (local development)"""
    from routes.api import api_get_settings
    return api_get_settings()

@app.route('/api/settings', methods=['POST'])
def api_update_settings_root():
    """Update dashboard settings (local development)"""
    from routes.api import api_update_settings
    return api_update_settings()

@app.route('/api/tasks/<task_id>/delete', methods=['POST'])
def api_delete_task_root(task_id):
    """Soft delete a task (local development)"""
    from routes.api import api_delete_task
    return api_delete_task(task_id)

@app.route('/api/tasks/<task_id>/restore', methods=['POST'])
def api_restore_task_root(task_id):
    """Restore a deleted task (local development)"""
    from routes.api import api_restore_task
    return api_restore_task(task_id)

@app.route('/api/deleted-tasks')
def api_deleted_tasks_root():
    """Get deleted tasks (local development)"""
    from routes.api import api_deleted_tasks
    return api_deleted_tasks()

@app.route('/api/reports/types')
def api_report_types_root():
    """Get available report types (local development)"""
    from routes.api import api_report_types
    return api_report_types()

@app.route('/api/reports/generate', methods=['POST'])
def api_generate_report_root():
    """Generate a report (local development)"""
    from routes.api import api_generate_report
    return api_generate_report()

@app.route('/api/filter-tasks', methods=['POST'])
def api_filter_tasks_root():
    """Advanced task filtering (local development)"""
    from routes.api import api_filter_tasks
    return api_filter_tasks()

@app.route('/api/updates/last')
def api_last_update_root():
    """Get last update timestamp (local development)"""
    from routes.api import api_last_update
    return api_last_update()


# Tags Import Routes (local development)
@app.route('/api/tags', methods=['GET'])
def api_tags_root():
    """Get all tags (local development)"""
    from routes.api import api_tags
    return api_tags()


@app.route('/api/tags/dry-run', methods=['POST'])
def api_tags_dry_run_root():
    """Preview tags that will be imported (local development)"""
    from routes.api import api_tags_dry_run
    return api_tags_dry_run()


@app.route('/api/tags/import', methods=['POST'])
def api_tags_import_root():
    """Import tags from Google Tasks (local development)"""
    from routes.api import api_tags_import
    return api_tags_import()


@app.route('/api/tags/statistics', methods=['GET'])
def api_tags_statistics_root():
    """Get tag statistics (local development)"""
    from routes.api import api_tags_statistics
    return api_tags_statistics()


@app.route('/api/tags/sync', methods=['POST'])
def api_tags_sync_root():
    """Sync tags with tasks (local development)"""
    from routes.api import api_tags_sync
    return api_tags_sync()


@app.route('/api/connections', methods=['GET'])
def api_connections_root():
    """Get all user connections (local development)"""
    from routes.api import api_connections
    return api_connections()


# End of local development routes


# ============================================
# Authentication Routes
# ============================================

# Configure secret key for sessions
app.secret_key = os.environ.get('SESSION_SECRET', 'gtasks-dashboard-secret-key-2026')


def get_base_path():
    """Get the base path for routes"""
    return os.environ.get('SCRIPT_NAME', BASE_PATH)


@app.route(f'{BASE_PATH}/login')
def login_page():
    """Render login page"""
    # Check if user is already logged in
    if 'user_id' in session:
        return render_template('login.html', base_path=get_base_path(), success='You are already logged in!')
    return render_template('login.html', base_path=get_base_path())


@app.route(f'{BASE_PATH}/login', methods=['POST'])
def login():
    """Handle login with QERDS API key"""
    from gtasks_cli.services.auth_service import AuthService
    
    email = request.form.get('email', '').strip().lower()
    api_key = request.form.get('api_key', '').strip()
    
    if not email or not api_key:
        return render_template('login.html', base_path=get_base_path(), error='Email and API key are required')
    
    try:
        auth_service = AuthService()
        result = auth_service.login(email=email, api_key=api_key, is_dummy=False)
        
        if result['success']:
            # Store session
            session['user_id'] = result['user']['user_id']
            session['email'] = result['user']['email']
            session['is_dummy'] = False
            return render_template('login.html', base_path=get_base_path(), success=f"Welcome back, {result['user']['email']}!")
        else:
            return render_template('login.html', base_path=get_base_path(), error=result.get('error', 'Login failed'))
    except Exception as e:
        return render_template('login.html', base_path=get_base_path(), error=f'Login failed: {str(e)}')


@app.route(f'{BASE_PATH}/login/dummy', methods=['POST'])
def login_dummy():
    """Handle dummy login for testing"""
    from gtasks_cli.services.auth_service import AuthService
    
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        email = 'demo@example.com'
    
    try:
        auth_service = AuthService()
        result = auth_service.login(email=email, api_key='dummy-key', is_dummy=True)
        
        if result['success']:
            # Store session
            session['user_id'] = result['user']['user_id']
            session['email'] = result['user']['email']
            session['is_dummy'] = True
            return render_template('login.html', base_path=get_base_path(), success=f"Welcome to demo mode, {result['user']['email']}!")
        else:
            return render_template('login.html', base_path=get_base_path(), error=result.get('error', 'Demo login failed'))
    except Exception as e:
        return render_template('login.html', base_path=get_base_path(), error=f'Demo login failed: {str(e)}')


@app.route(f'{BASE_PATH}/logout', methods=['POST'])
def logout():
    """Handle logout"""
    from gtasks_cli.services.auth_service import AuthService
    
    user_id = session.get('user_id')
    
    if user_id:
        try:
            auth_service = AuthService()
            auth_service.logout(user_id)
        except Exception as e:
            pass  # Ignore logout errors
    
    # Clear session
    session.clear()
    
    return render_template('login.html', base_path=get_base_path(), success='You have been logged out')


@app.route(f'{BASE_PATH}/api/auth/status')
def auth_status():
    """Get current authentication status"""
    if 'user_id' in session:
        from gtasks_cli.services.auth_service import AuthService
        
        auth_service = AuthService()
        user = auth_service.get_user(session['user_id'])
        
        if user:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict() if hasattr(user, 'to_dict') else dict(user),
                'is_dummy': session.get('is_dummy', False)
            })
    
    return jsonify({'authenticated': False})


# ============================================
# Shared Tasks Routes (BASE_PATH)
# ============================================

@app.route(f'{BASE_PATH}/api/shared-tasks')
def api_shared_tasks():
    """Get tasks shared with the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    tasks = service.get_tasks_for_user(session['user_id'])
    
    return jsonify({
        'shared_tasks': tasks,
        'count': len(tasks)
    })


@app.route(f'{BASE_PATH}/api/shared-tasks/pending')
def api_pending_shared_tasks():
    """Get pending tasks for the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    tasks = service.get_pending_tasks_for_user(session['user_id'])
    
    return jsonify({
        'pending_tasks': tasks,
        'count': len(tasks)
    })


@app.route(f'{BASE_PATH}/api/shared-tasks/<task_id>/complete', methods=['POST'])
def api_complete_shared_task(task_id):
    """Mark a shared task as complete for the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    result = service.mark_task_complete(task_id, session['user_id'])
    
    return jsonify(result)


@app.route(f'{BASE_PATH}/api/shared-tasks/stats')
def api_shared_tasks_stats():
    """Get shared tasks statistics"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    stats = service.get_overall_stats()
    
    return jsonify(stats)


# ============================================
# Invitation Routes (BASE_PATH)
# ============================================

@app.route(f'{BASE_PATH}/api/invitations/pending')
def api_pending_invitations():
    """Get pending invitations for the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    invitations = service.get_pending_invitations(session['user_id'])
    
    return jsonify({
        'invitations': invitations,
        'count': len(invitations)
    })


@app.route(f'{BASE_PATH}/api/invitations/sent')
def api_sent_invitations():
    """Get sent invitations by the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    invitations = service.get_sent_invitations(session['user_id'])
    
    return jsonify({
        'invitations': invitations,
        'count': len(invitations)
    })


@app.route(f'{BASE_PATH}/api/invitations/<invitation_id>/accept', methods=['POST'])
def api_accept_invitation(invitation_id):
    """Accept an invitation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    result = service.accept_invitation(invitation_id, session['user_id'])
    
    return jsonify(result)


@app.route(f'{BASE_PATH}/api/invitations/<invitation_id>/reject', methods=['POST'])
def api_reject_invitation(invitation_id):
    """Reject an invitation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    result = service.reject_invitation(invitation_id, session['user_id'])
    
    return jsonify(result)


@app.route(f'{BASE_PATH}/api/invitations/create', methods=['POST'])
def api_create_invitation():
    """Create a new invitation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    data = request.get_json()
    
    from_email = data.get('from_email', session.get('email'))
    to_email = data.get('to_email')
    task_id = data.get('task_id')
    message = data.get('message', '')
    
    if not to_email or not task_id:
        return jsonify({'success': False, 'error': 'to_email and task_id are required'}), 400
    
    service = InvitationService()
    result = service.create_invitation(
        from_user_id=session['user_id'],
        from_email=from_email,
        to_email=to_email,
        task_id=task_id,
        message=message
    )
    
    if result['success']:
        # Send invitation email
        service.send_invitation_email(result['invitation_id'])
    
    return jsonify(result)


# ============================================
# Account Tags Routes (BASE_PATH)
# ============================================

@app.route(f'{BASE_PATH}/api/account-tags')
def api_account_tags():
    """Get account tags for the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.account_tag_service import AccountTagService
    
    service = AccountTagService()
    tags = service.get_user_account_tags(session['user_id'])
    
    return jsonify({
        'account_tags': tags,
        'count': len(tags)
    })


@app.route(f'{BASE_PATH}/api/account-tags/parse', methods=['POST'])
def api_parse_account_tags():
    """Parse account tags from text"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.account_tag_service import AccountTagService
    
    data = request.get_json()
    text = data.get('text', '')
    
    service = AccountTagService()
    tags = service.parse_account_tags(text)
    
    return jsonify({
        'account_tags': tags,
        'count': len(tags)
    })


# End of shared tasks and invitations routes (BASE_PATH)


# Local development authentication routes

@app.route('/login')
def login_page_root():
    """Render login page (local development)"""
    if 'user_id' in session:
        return render_template('login.html', base_path='', success='You are already logged in!')
    return render_template('login.html', base_path='')


@app.route('/login', methods=['POST'])
def login_root():
    """Handle login with QERDS API key (local development)"""
    from gtasks_cli.services.auth_service import AuthService
    
    email = request.form.get('email', '').strip().lower()
    api_key = request.form.get('api_key', '').strip()
    
    if not email or not api_key:
        return render_template('login.html', base_path='', error='Email and API key are required')
    
    try:
        auth_service = AuthService()
        result = auth_service.login(email=email, api_key=api_key, is_dummy=False)
        
        if result['success']:
            session['user_id'] = result['user']['user_id']
            session['email'] = result['user']['email']
            session['is_dummy'] = False
            return render_template('login.html', base_path='', success=f"Welcome back, {result['user']['email']}!")
        else:
            return render_template('login.html', base_path='', error=result.get('error', 'Login failed'))
    except Exception as e:
        return render_template('login.html', base_path='', error=f'Login failed: {str(e)}')


@app.route('/login/dummy', methods=['POST'])
def login_dummy_root():
    """Handle dummy login for testing (local development)"""
    from gtasks_cli.services.auth_service import AuthService
    
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        email = 'demo@example.com'
    
    try:
        auth_service = AuthService()
        result = auth_service.login(email=email, api_key='dummy-key', is_dummy=True)
        
        if result['success']:
            session['user_id'] = result['user']['user_id']
            session['email'] = result['user']['email']
            session['is_dummy'] = True
            return render_template('login.html', base_path='', success=f"Welcome to demo mode, {result['user']['email']}!")
        else:
            return render_template('login.html', base_path='', error=result.get('error', 'Demo login failed'))
    except Exception as e:
        return render_template('login.html', base_path='', error=f'Demo login failed: {str(e)}')


@app.route('/logout', methods=['POST'])
def logout_root():
    """Handle logout (local development)"""
    from gtasks_cli.services.auth_service import AuthService
    
    user_id = session.get('user_id')
    
    if user_id:
        try:
            auth_service = AuthService()
            auth_service.logout(user_id)
        except Exception as e:
            pass
    
    session.clear()
    return render_template('login.html', base_path='', success='You have been logged out')


@app.route('/api/auth/status')
def auth_status_root():
    """Get current authentication status (local development)"""
    if 'user_id' in session:
        from gtasks_cli.services.auth_service import AuthService
        
        auth_service = AuthService()
        user = auth_service.get_user(session['user_id'])
        
        if user:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict() if hasattr(user, 'to_dict') else dict(user),
                'is_dummy': session.get('is_dummy', False)
            })
    
    return jsonify({'authenticated': False})


# ============================================
# Shared Tasks Routes (local development)
# ============================================

@app.route('/api/shared-tasks')
def api_shared_tasks_root():
    """Get tasks shared with the current user (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    tasks = service.get_tasks_for_user(session['user_id'])
    
    return jsonify({
        'shared_tasks': tasks,
        'count': len(tasks)
    })


@app.route('/api/shared-tasks/pending')
def api_pending_shared_tasks_root():
    """Get pending tasks for the current user (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    tasks = service.get_pending_tasks_for_user(session['user_id'])
    
    return jsonify({
        'pending_tasks': tasks,
        'count': len(tasks)
    })


@app.route('/api/shared-tasks/<task_id>/complete', methods=['POST'])
def api_complete_shared_task_root(task_id):
    """Mark a shared task as complete for the current user (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    result = service.mark_task_complete(task_id, session['user_id'])
    
    return jsonify(result)


@app.route('/api/shared-tasks/stats')
def api_shared_tasks_stats_root():
    """Get shared tasks statistics (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.task_sharing_service import TaskSharingService
    
    service = TaskSharingService()
    stats = service.get_overall_stats()
    
    return jsonify(stats)


# ============================================
# Invitation Routes (local development)
# ============================================

@app.route('/api/invitations/pending')
def api_pending_invitations_root():
    """Get pending invitations for the current user (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    invitations = service.get_pending_invitations(session['user_id'])
    
    return jsonify({
        'invitations': invitations,
        'count': len(invitations)
    })


@app.route('/api/invitations/sent')
def api_sent_invitations_root():
    """Get sent invitations by the current user (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    invitations = service.get_sent_invitations(session['user_id'])
    
    return jsonify({
        'invitations': invitations,
        'count': len(invitations)
    })


@app.route('/api/invitations/<invitation_id>/accept', methods=['POST'])
def api_accept_invitation_root(invitation_id):
    """Accept an invitation (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    result = service.accept_invitation(invitation_id, session['user_id'])
    
    return jsonify(result)


@app.route('/api/invitations/<invitation_id>/reject', methods=['POST'])
def api_reject_invitation_root(invitation_id):
    """Reject an invitation (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    service = InvitationService()
    result = service.reject_invitation(invitation_id, session['user_id'])
    
    return jsonify(result)


@app.route('/api/invitations/create', methods=['POST'])
def api_create_invitation_root():
    """Create a new invitation (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.invitation_service import InvitationService
    
    data = request.get_json()
    
    from_email = data.get('from_email', session.get('email'))
    to_email = data.get('to_email')
    task_id = data.get('task_id')
    message = data.get('message', '')
    
    if not to_email or not task_id:
        return jsonify({'success': False, 'error': 'to_email and task_id are required'}), 400
    
    service = InvitationService()
    result = service.create_invitation(
        from_user_id=session['user_id'],
        from_email=from_email,
        to_email=to_email,
        task_id=task_id,
        message=message
    )
    
    if result['success']:
        # Send invitation email
        service.send_invitation_email(result['invitation_id'])
    
    return jsonify(result)


# ============================================
# Account Tags Routes (local development)
# ============================================

@app.route('/api/account-tags')
def api_account_tags_root():
    """Get account tags for the current user (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.account_tag_service import AccountTagService
    
    service = AccountTagService()
    tags = service.get_user_account_tags(session['user_id'])
    
    return jsonify({
        'account_tags': tags,
        'count': len(tags)
    })


@app.route('/api/account-tags/parse', methods=['POST'])
def api_parse_account_tags_root():
    """Parse account tags from text (local development)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from gtasks_cli.services.account_tag_service import AccountTagService
    
    data = request.get_json()
    text = data.get('text', '')
    
    service = AccountTagService()
    tags = service.parse_account_tags(text)
    
    return jsonify({
        'account_tags': tags,
        'count': len(tags)
    })


# ============================================
# TASK MODAL ROUTES
# ============================================

@app.route(f'{BASE_PATH}/task/new')
def task_modal_page():
    """Render task creation modal page"""
    return render_template('task-modal.html', base_path=get_base_path())


@app.route(f'{BASE_PATH}/task/<task_id>/edit')
def task_edit_page(task_id):
    """Render task edit modal page"""
    return render_template('task-modal.html', base_path=get_base_path(), task_id=task_id)


# ============================================
# NEW API ENDPOINTS FOR TASKS (local development)
# ============================================

@app.route('/api/invitations/send', methods=['POST'])
def api_send_invitation_root():
    """Send an invitation to connect (local development)"""
    from routes.api import api_send_invitation
    return api_send_invitation()


@app.route('/api/invitations/accept/<invitation_id>', methods=['POST'])
def api_accept_invitation_page_root(invitation_id):
    """Accept an invitation (local development)"""
    from routes.api import api_accept_invitation
    return api_accept_invitation(invitation_id)


@app.route('/api/connected-accounts')
def api_connected_accounts_root():
    """Get connected accounts (local development)"""
    from routes.api import api_connected_accounts
    return api_connected_accounts()


# ============================================
# NEW API ENDPOINTS FOR TASKS (BASE_PATH)
# ============================================

@app.route(f'{BASE_PATH}/api/invitations/send', methods=['POST'])
def api_send_invitation_base():
    """Send an invitation to connect (BASE_PATH)"""
    from routes.api import api_send_invitation
    return api_send_invitation()


@app.route(f'{BASE_PATH}/api/invitations/accept/<invitation_id>', methods=['POST'])
def api_accept_invitation_page_base(invitation_id):
    """Accept an invitation (BASE_PATH)"""
    from routes.api import api_accept_invitation
    return api_accept_invitation(invitation_id)


@app.route(f'{BASE_PATH}/api/connected-accounts')
def api_connected_accounts_base():
    """Get connected accounts (BASE_PATH)"""
    from routes.api import api_connected_accounts
    return api_connected_accounts()


# ============================================
# TAGS MANAGEMENT ROUTES
# ============================================

@app.route(f'{BASE_PATH}/tags')
def tags_page():
    """Render tags management page"""
    return render_template('tags.html', base_path=get_base_path())


@app.route(f'{BASE_PATH}/tags/<tag_name>')
def tag_tasks_page(tag_name):
    """Render page showing tasks with a specific tag"""
    return render_template('tags.html', base_path=get_base_path(), view='tag-tasks', tag_name=tag_name)


@app.route(f'{BASE_PATH}/api/tags', methods=['GET'])
def api_get_tags():
    """Get all tags"""
    from routes.api import api_tags
    return api_tags()


@app.route(f'{BASE_PATH}/api/tags', methods=['POST'])
def api_create_tag():
    """Create a new tag"""
    data = request.get_json()
    
    try:
        tag_name = data.get('name', '').strip()
        tag_type = data.get('type', 'regular')
        color = data.get('color', 'blue')
        description = data.get('description', '')
        
        if not tag_name:
            return jsonify({
                'success': False,
                'message': 'Tag name is required'
            }), 400
        
        # Create tag
        tag = {
            'id': f"tag_{len(_dashboard_state.get('tags', [])) + 1}",
            'tag_name': tag_name,
            'tag_type': tag_type,
            'color': color,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
        
        # Store tag
        if 'tags' not in _dashboard_state:
            _dashboard_state['tags'] = {}
        
        if tag_type == 'account':
            if 'account_tags' not in _dashboard_state['tags']:
                _dashboard_state['tags']['account_tags'] = []
            _dashboard_state['tags']['account_tags'].append(tag)
        else:
            if 'regular_tags' not in _dashboard_state['tags']:
                _dashboard_state['tags']['regular_tags'] = []
            _dashboard_state['tags']['regular_tags'].append(tag)
        
        return jsonify({
            'success': True,
            'tag': tag,
            'message': 'Tag created successfully'
        })
        
    except Exception as e:
        print(f'[API] Error creating tag: {e}')
        return jsonify({
            'success': False,
            'message': f'Error creating tag: {str(e)}'
        }), 500


@app.route(f'{BASE_PATH}/api/tags/<tag_id>', methods=['PUT'])
def api_update_tag(tag_id):
    """Update an existing tag"""
    data = request.get_json()
    
    try:
        tag_name = data.get('name', '').strip()
        color = data.get('color')
        description = data.get('description')
        
        # Find and update tag
        tags = _dashboard_state.get('tags', {})
        account_tags = tags.get('account_tags', [])
        regular_tags = tags.get('regular_tags', [])
        
        for tag_list in [account_tags, regular_tags]:
            for tag in tag_list:
                if tag.get('id') == tag_id or tag.get('tag_name') == tag_id:
                    if tag_name:
                        tag['tag_name'] = tag_name
                    if color:
                        tag['color'] = color
                    if description is not None:
                        tag['description'] = description
                    tag['updated_at'] = datetime.now().isoformat()
                    
                    return jsonify({
                        'success': True,
                        'tag': tag,
                        'message': 'Tag updated successfully'
                    })
        
        return jsonify({
            'success': False,
            'message': 'Tag not found'
        }), 404
        
    except Exception as e:
        print(f'[API] Error updating tag: {e}')
        return jsonify({
            'success': False,
            'message': f'Error updating tag: {str(e)}'
        }), 500


@app.route(f'{BASE_PATH}/api/tags/<tag_id>', methods=['DELETE'])
def api_delete_tag(tag_id):
    """Delete a tag"""
    try:
        tags = _dashboard_state.get('tags', {})
        account_tags = tags.get('account_tags', [])
        regular_tags = tags.get('regular_tags', [])
        
        # Find and remove tag
        for i, tag in enumerate(account_tags):
            if tag.get('id') == tag_id or tag.get('tag_name') == tag_id:
                account_tags.pop(i)
                return jsonify({
                    'success': True,
                    'message': 'Tag deleted successfully'
                })
        
        for i, tag in enumerate(regular_tags):
            if tag.get('id') == tag_id or tag.get('tag_name') == tag_id:
                regular_tags.pop(i)
                return jsonify({
                    'success': True,
                    'message': 'Tag deleted successfully'
                })
        
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


# ============================================
# SETTINGS ROUTES
# ============================================

@app.route(f'{BASE_PATH}/settings')
def settings_page():
    """Render settings page"""
    return render_template('settings.html', base_path=get_base_path())


@app.route(f'{BASE_PATH}/settings/tags-import')
def settings_tags_import():
    """Render settings page with Tags Import section"""
    return render_template('settings.html', base_path=get_base_path(), section='tags-import')


@app.route(f'{BASE_PATH}/settings/tags-management')
def settings_tags_management():
    """Render settings page with Tags Management section"""
    return render_template('settings.html', base_path=get_base_path(), section='tags-management')


@app.route(f'{BASE_PATH}/settings/connected-accounts')
def settings_connected_accounts():
    """Render settings page with Connected Accounts section"""
    return render_template('settings.html', base_path=get_base_path(), section='connected-accounts')


@app.route(f'{BASE_PATH}/settings/remote-sync')
def settings_remote_sync():
    """Render settings page with Remote Sync section"""
    return render_template('settings.html', base_path=get_base_path(), section='remote-sync')


@app.route(f'{BASE_PATH}/api/settings', methods=['GET'])
def api_get_settings():
    """Get user settings"""
    try:
        # Get settings from state or defaults
        settings = _dashboard_state.get('settings', {
            'auto_refresh': True,
            'refresh_interval': 60,
            'default_view': 'dashboard',
            'hide_deleted': True
        })
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        print(f'[API] Error getting settings: {e}')
        return jsonify({
            'success': False,
            'message': f'Error getting settings: {str(e)}'
        }), 500


@app.route(f'{BASE_PATH}/api/settings', methods=['POST'])
def api_save_settings():
    """Save user settings"""
    data = request.get_json()
    
    try:
        # Update settings
        _dashboard_state['settings'] = {
            'auto_refresh': data.get('auto_refresh', True),
            'refresh_interval': data.get('refresh_interval', 60),
            'default_view': data.get('default_view', 'dashboard'),
            'hide_deleted': data.get('hide_deleted', True)
        }
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully'
        })
        
    except Exception as e:
        print(f'[API] Error saving settings: {e}')
        return jsonify({
            'success': False,
            'message': f'Error saving settings: {str(e)}'
        }), 500


# ============================================
# SETTINGS ROUTES (local development)
# ============================================

@app.route('/settings')
def settings_page_local():
    """Render settings page (local development)"""
    return render_template('settings.html', base_path='')


@app.route('/settings/tags-import')
def settings_tags_import_local():
    """Render settings page with Tags Import section (local development)"""
    return render_template('settings.html', base_path='', section='tags-import')


@app.route('/settings/tags-management')
def settings_tags_management_local():
    """Render settings page with Tags Management section (local development)"""
    return render_template('settings.html', base_path='', section='tags-management')


@app.route('/settings/connected-accounts')
def settings_connected_accounts_local():
    """Render settings page with Connected Accounts section (local development)"""
    return render_template('settings.html', base_path='', section='connected-accounts')


@app.route('/settings/remote-sync')
def settings_remote_sync_local():
    """Render settings page with Remote Sync section (local development)"""
    return render_template('settings.html', base_path='', section='remote-sync')


@app.route('/api/settings', methods=['GET'])
def api_get_settings_local():
    """Get user settings (local development)"""
    return api_get_settings()


@app.route('/api/settings', methods=['POST'])
def api_save_settings_local():
    """Save user settings (local development)"""
    return api_save_settings()


# ============================================
# TAGS MANAGEMENT ROUTES (local development)
# ============================================

@app.route('/api/tags', methods=['POST'])
def api_create_tag_local():
    """Create a new tag (local development)"""
    return api_create_tag()


@app.route('/api/tags/<tag_id>', methods=['PUT'])
def api_update_tag_local(tag_id):
    """Update an existing tag (local development)"""
    return api_update_tag(tag_id)


@app.route('/api/tags/<tag_id>', methods=['DELETE'])
def api_delete_tag_local(tag_id):
    """Delete a tag (local development)"""
    return api_delete_tag(tag_id)


# ============================================
# TASK MODAL ROUTES
# ============================================

@app.route('/task/new')
def task_modal_page_local():
    """Render task creation modal page (local development)"""
    return render_template('task-modal.html', base_path='')


@app.route('/task/<task_id>/edit')
def task_edit_page_local(task_id):
    """Render task edit modal page (local development)"""
    return render_template('task-modal.html', base_path='', task_id=task_id)


# ============================================
# NEW API ENDPOINTS FOR TASKS (local development)
# ============================================

# End of local development routes


def get_enabled_features() -> list:
    """Get list of enabled features based on feature flags"""
    features = []
    
    # Core features
    features.append("Dashboard overview with stats")
    features.append("Hierarchical task visualization (D3.js)")
    features.append("Multi-account support")
    
    # Enhanced features (based on feature flags)
    if FEATURE_FLAGS.get('ENABLE_PRIORITY_SYSTEM', False):
        features.append("Priority system (asterisk-based calculation)")
    
    if FEATURE_FLAGS.get('ENABLE_ADVANCED_FILTERS', False):
        features.append("Advanced filters (OR/AND/NOT tag filtering)")
    
    if FEATURE_FLAGS.get('ENABLE_REPORTS', False):
        features.append("Reports system")
    
    if FEATURE_FLAGS.get('ENABLE_DELETED_TASKS', False):
        features.append("Deleted tasks management")
    
    if FEATURE_FLAGS.get('ENABLE_TASKS_DUE_TODAY', False):
        features.append("Tasks due today dashboard")
    
    if FEATURE_FLAGS.get('ENABLE_ACCOUNT_TYPE_FILTERS', False):
        features.append("Multi-select account type filters")
    
    if FEATURE_FLAGS.get('ENABLE_REALTIME_UPDATES', False):
        features.append("Realtime data updates")
    
    return features


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))  # Default to 8081
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("=" * 50)
    print("  GTasks Dashboard")
    print("  Consolidated Architecture")
    print("  Single Source of Truth")
    print("=" * 50)
    print()
    print(f"🚀 Starting server on http://{host}:{port}")
    print()
    
    print("Enabled Features:")
    for feature in get_enabled_features():
        print(f"  ✅ {feature}")
    
    print()
    print("Controls:")
    print("  - Ctrl+B: Toggle sidebar")
    print("  - ESC: Exit fullscreen")
    print()
    print("-" * 50)
    print("Feature flags can be configured in config.py")
    print("-" * 50)
    
    app.run(host=host, port=port, debug=True)
