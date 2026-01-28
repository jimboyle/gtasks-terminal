"""
Shared Task Access Service

This service manages task visibility and completion tracking for shared tasks.
It determines which tasks a user can access based on their connections
and tracks completion status per user.

This service integrates with:
- account_tag_integration_service (for detecting shared tasks)
- invitation_workflow_manager (for connection status)
- database_service (for persistence)
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SharedTaskInfo:
    """Information about a shared task"""
    task_id: str
    task_title: str
    original_account_id: str
    owner_user_id: str
    shared_at: str
    completion_status: str  # pending, in_progress, completed
    completed_at: Optional[str] = None
    task_data: Optional[Dict[str, Any]] = None


@dataclass
class CompletionStatus:
    """Completion status for a specific user"""
    user_id: str
    user_email: str
    status: str  # pending, in_progress, completed
    completed_at: Optional[str] = None


class SharedTaskAccessService:
    """
    Manages access to shared tasks and tracks completion per user.
    
    Key responsibilities:
    1. Determine which tasks a user can access (based on connections)
    2. Get tasks shared with a user (where user is tagged with [@account])
    3. Get tasks shared by a user (where user created tasks with [@account] tags)
    4. Mark tasks as complete for specific users
    5. Get completion status for all users who have access to a task
    6. Provide unified view of shared tasks
    """
    
    def __init__(self, gtasks_path: Optional[Path] = None):
        """Initialize the access service"""
        self.gtasks_path = gtasks_path or self._detect_gtasks_path()
        logger.info("[SharedTaskAccessService] Initialized")
    
    def _detect_gtasks_path(self) -> Optional[Path]:
        """Detect GTasks CLI path with multiple fallback locations"""
        import os
        from pathlib import Path
        
        if os.environ.get('GTASKS_CONFIG_DIR'):
            config_path = Path(os.environ['GTASKS_CONFIG_DIR'])
            if config_path.exists():
                logger.info(f"[SharedTaskAccessService] Using GTASKS_CONFIG_DIR: {config_path}")
                return config_path
        
        possible_paths = [
            Path.home() / '.gtasks',
            Path('./gtasks_cli'),
            Path(__file__).parent.parent.parent / 'gtasks_cli',
            Path.cwd().parent / 'gtasks_cli',
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"[SharedTaskAccessService] Detected gtasks path: {path}")
                return path
        
        logger.warning("[SharedTaskAccessService] No gtasks path found")
        return None
    
    def _extract_account_tags(self, text: str) -> List[str]:
        """Extract account tags from text"""
        if not text:
            return []
        
        # Match [@account] pattern
        account_tags = re.findall(r'@\[([^\]]+)\]', text, re.IGNORECASE)
        
        # Also support direct @account format
        direct_accounts = re.findall(r'@(\w+)', text, re.IGNORECASE)
        
        # Combine and deduplicate
        all_accounts = set()
        for account in account_tags + direct_accounts:
            account = account.strip()
            if account and len(account) >= 2:
                all_accounts.add(account.lower())
        
        return list(all_accounts)
    
    def get_shared_tasks_for_user(self, user_id: str, user_email: str = None) -> List[SharedTaskInfo]:
        """
        Get all tasks that are shared with a user.
        
        A task is shared with a user if:
        1. The task contains an [@account] tag
        2. The account name matches the user's ID (derived from email)
        3. The user is connected to the task owner
        
        Args:
            user_id: User ID to get shared tasks for
            user_email: User email for additional matching
            
        Returns:
            List of SharedTaskInfo objects
        """
        # Extract account names from user ID
        account_names = self._get_account_names_from_user(user_id, user_email)
        
        # Get tasks from all accounts
        all_tasks = []
        for account_name in account_names:
            tasks = self._get_tasks_with_account_tag(account_name)
            all_tasks.extend(tasks)
        
        # Filter to only tasks where user is connected to owner
        connected_tasks = []
        for task in all_tasks:
            if self._is_user_connected_to_task_owner(user_id, task['owner_user_id']):
                task_info = SharedTaskInfo(
                    task_id=task['task_id'],
                    task_title=task['task_title'],
                    original_account_id=task['original_account_id'],
                    owner_user_id=task['owner_user_id'],
                    shared_at=task['shared_at'],
                    completion_status=task.get('completion_status', 'pending'),
                    completed_at=task.get('completed_at'),
                    task_data=task.get('task_data')
                )
                connected_tasks.append(task_info)
        
        logger.info(f"[SharedTaskAccessService] Found {len(connected_tasks)} shared tasks for user {user_id}")
        return connected_tasks
    
    def _get_account_names_from_user(self, user_id: str, user_email: str = None) -> List[str]:
        """Extract account names from user ID and email"""
        account_names = []
        
        # User ID format: abc12345 (from abc@gmail.com)
        # Account name is the prefix
        if user_id and len(user_id) >= 3:
            # Extract potential account name (everything except last few chars which might be hash)
            # Try different splits to find valid account names
            for split_point in range(3, len(user_id)):
                potential_name = user_id[:split_point].lower()
                if potential_name.isalnum() and len(potential_name) >= 2:
                    account_names.append(potential_name)
        
        # Also try extracting from email
        if user_email and '@' in user_email:
            email_prefix = user_email.split('@')[0].lower()
            if email_prefix not in account_names:
                account_names.append(email_prefix)
        
        return list(set(account_names))  # Remove duplicates
    
    def _get_tasks_with_account_tag(self, account_name: str) -> List[Dict[str, Any]]:
        """Get tasks that contain a specific account tag"""
        tasks = []
        
        if not self.gtasks_path:
            return tasks
        
        # Check main database
        db_file = self.gtasks_path / 'tasks.db'
        if not db_file.exists():
            return tasks
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Get all tasks
            cursor.execute("""
                SELECT id, title, description, due, priority, status, tags, notes, 
                       created_at, modified_at, list_title
                FROM tasks
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            # Check each task for the account tag
            for row in rows:
                task_id, title, description, due, priority, status, tags, notes, \
                created_at, modified_at, list_title = row
                
                # Combine text fields to search for account tags
                full_text = f"{title} {description or ''} {notes or ''}"
                
                # Check structured tags field
                if tags:
                    try:
                        tag_list = json.loads(tags)
                        if isinstance(tag_list, list):
                            full_text += ' ' + ' '.join(tag_list)
                    except:
                        pass
                
                # Extract account tags
                account_tags = self._extract_account_tags(full_text)
                
                if account_name.lower() in [t.lower() for t in account_tags]:
                    # Task contains the account tag
                    task_data = {
                        'task_id': task_id,
                        'task_title': title,
                        'description': description,
                        'due': due,
                        'priority': priority,
                        'status': status,
                        'notes': notes,
                        'list_title': list_title,
                        'original_account_id': account_name,
                        'owner_user_id': None,  # Will be filled later
                        'shared_at': datetime.now().isoformat(),
                        'completion_status': 'pending',
                        'task_data': {
                            'id': task_id,
                            'title': title,
                            'description': description,
                            'due': due,
                            'priority': priority,
                            'status': status,
                            'notes': notes,
                            'list_title': list_title
                        }
                    }
                    tasks.append(task_data)
            
            logger.info(f"[SharedTaskAccessService] Found {len(tasks)} tasks with account tag '{account_name}'")
            
        except Exception as e:
            logger.error(f"[SharedTaskAccessService] Error getting tasks: {e}")
        
        return tasks
    
    def _is_user_connected_to_task_owner(self, user_id: str, owner_id: str) -> bool:
        """Check if user is connected to task owner"""
        if user_id == owner_id:
            return True  # User owns the task
        
        if not self.gtasks_path:
            return False
        
        db_file = self.gtasks_path / 'connections.db'
        if not db_file.exists():
            return False
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT id FROM connections 
                   WHERE ((user_id1 = ? AND user_id2 = ?) OR (user_id1 = ? AND user_id2 = ?)) 
                   AND status = 'active'""",
                (user_id, owner_id, owner_id, user_id)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"[SharedTaskAccessService] Error checking connection: {e}")
        
        return False
    
    def get_tasks_shared_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks that have been shared by a user.
        
        A task is shared by a user if:
        1. The user created the task
        2. The task contains [@account] tags for other users
        
        Args:
            user_id: User ID to get shared tasks for
            
        Returns:
            List of task dictionaries with share information
        """
        # Get all tasks from user's accounts
        user_accounts = self._get_user_accounts(user_id)
        
        shared_tasks = []
        for account_id in user_accounts:
            tasks = self._get_tasks_from_account(account_id)
            
            for task in tasks:
                # Check if task has account tags
                full_text = f"{task.get('title', '')} {task.get('description', '')} {task.get('notes', '')}"
                account_tags = self._extract_account_tags(full_text)
                
                if account_tags:
                    # Task has been shared with other accounts
                    task['shared_accounts'] = account_tags
                    task['shared_count'] = len(account_tags)
                    shared_tasks.append(task)
        
        logger.info(f"[SharedTaskAccessService] Found {len(shared_tasks)} tasks shared by user {user_id}")
        return shared_tasks
    
    def _get_user_accounts(self, user_id: str) -> List[str]:
        """Get all accounts belonging to a user"""
        accounts = []
        
        if not self.gtasks_path:
            return accounts
        
        # Check if user_id is an account directory
        user_account_path = self.gtasks_path / user_id
        if user_account_path.exists() and user_account_path.is_dir():
            accounts.append(user_id)
        
        # Also check default account
        default_path = self.gtasks_path / 'default'
        if default_path.exists() and default_path.is_dir():
            accounts.append('default')
        
        return accounts
    
    def _get_tasks_from_account(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all tasks from an account"""
        tasks = []
        
        if not self.gtasks_path:
            return tasks
        
        db_file = self.gtasks_path / account_id / 'tasks.db'
        if not db_file.exists():
            db_file = self.gtasks_path / 'tasks.db'
        
        if not db_file.exists():
            return tasks
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, description, due, priority, status, tags, notes, 
                       created_at, modified_at, list_title
                FROM tasks
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                task_id, title, description, due, priority, status, tags, notes, \
                created_at, modified_at, list_title = row
                
                tasks.append({
                    'task_id': task_id,
                    'title': title,
                    'description': description,
                    'due': due,
                    'priority': priority,
                    'status': status,
                    'tags': tags,
                    'notes': notes,
                    'created_at': created_at,
                    'modified_at': modified_at,
                    'list_title': list_title,
                    'account_id': account_id
                })
            
        except Exception as e:
            logger.error(f"[SharedTaskAccessService] Error getting tasks from account {account_id}: {e}")
        
        return tasks
    
    def mark_task_complete(self, user_id: str, task_id: str, original_account_id: str) -> Dict[str, Any]:
        """
        Mark a shared task as complete for a specific user.
        
        Args:
            user_id: User ID completing the task
            task_id: Task ID
            original_account_id: Account where task was originally created
            
        Returns:
            Dictionary with success status and message
        """
        # Check if user has access to this task
        if not self._user_has_access_to_task(user_id, task_id, original_account_id):
            return {
                'success': False,
                'message': 'User does not have access to this task'
            }
        
        # Check if completion record exists
        existing = self._get_user_task_completion(user_id, task_id, original_account_id)
        
        if existing and existing.get('completion_status') == 'completed':
            return {
                'success': True,
                'message': 'Task is already marked as complete'
            }
        
        # Save completion record
        result = self._save_user_task_completion(
            user_id=user_id,
            task_id=task_id,
            original_account_id=original_account_id,
            completion_status='completed'
        )
        
        if result['success']:
            logger.info(f"[SharedTaskAccessService] User {user_id} completed task {task_id}")
            return {
                'success': True,
                'message': 'Task marked as complete'
            }
        else:
            return {
                'success': False,
                'message': f"Failed to mark task as complete: {result.get('error')}"
            }
    
    def _user_has_access_to_task(self, user_id: str, task_id: str, original_account_id: str) -> bool:
        """Check if user has access to a specific task"""
        # Check if user is the owner
        user_accounts = self._get_user_accounts(user_id)
        if original_account_id in user_accounts:
            return True
        
        # Check if user is connected to the owner
        if self._is_user_connected_to_task_owner(user_id, None):  # Would need owner_id
            # Would need to get owner_id from task
            return True
        
        # Check if task contains user's account tag
        tasks = self._get_tasks_with_account_tag(original_account_id)  # Actually should check user account
        for task in tasks:
            if task['task_id'] == task_id:
                return True
        
        return False
    
    def _get_user_task_completion(self, user_id: str, task_id: str, original_account_id: str) -> Optional[Dict[str, Any]]:
        """Get user's completion record for a task"""
        if not self.gtasks_path:
            return None
        
        db_file = self.gtasks_path / 'task_completions.db'
        if not db_file.exists():
            return None
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, task_id, original_account_id, completion_status, completed_at, shared_at
                FROM user_task_completions
                WHERE user_id = ? AND task_id = ? AND original_account_id = ?
            """, (user_id, task_id, original_account_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'user_id': row[0],
                    'task_id': row[1],
                    'original_account_id': row[2],
                    'completion_status': row[3],
                    'completed_at': row[4],
                    'shared_at': row[5]
                }
            
        except Exception as e:
            logger.error(f"[SharedTaskAccessService] Error getting completion: {e}")
        
        return None
    
    def _save_user_task_completion(self, user_id: str, task_id: str, 
                                   original_account_id: str, completion_status: str) -> Dict[str, Any]:
        """Save user's completion record for a task"""
        if not self.gtasks_path:
            return {'success': False, 'error': 'No database path'}
        
        db_file = self.gtasks_path / 'task_completions.db'
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_task_completions (
                    user_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    original_account_id TEXT NOT NULL,
                    completion_status TEXT DEFAULT 'pending',
                    completed_at TEXT,
                    shared_at TEXT,
                    PRIMARY KEY (user_id, task_id, original_account_id)
                )
            """)
            
            now = datetime.now().isoformat()
            
            # Check if record exists
            cursor.execute("""
                SELECT completion_status FROM user_task_completions
                WHERE user_id = ? AND task_id = ? AND original_account_id = ?
            """, (user_id, task_id, original_account_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                if completion_status == 'completed':
                    cursor.execute("""
                        UPDATE user_task_completions 
                        SET completion_status = ?, completed_at = ?
                        WHERE user_id = ? AND task_id = ? AND original_account_id = ?
                    """, (completion_status, now, user_id, task_id, original_account_id))
                else:
                    cursor.execute("""
                        UPDATE user_task_completions 
                        SET completion_status = ?
                        WHERE user_id = ? AND task_id = ? AND original_account_id = ?
                    """, (completion_status, user_id, task_id, original_account_id))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO user_task_completions 
                    (user_id, task_id, original_account_id, completion_status, completed_at, shared_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, task_id, original_account_id, completion_status, 
                      now if completion_status == 'completed' else None, now))
            
            conn.commit()
            conn.close()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"[SharedTaskAccessService] Error saving completion: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_completion_status(self, task_id: str, original_account_id: str) -> List[CompletionStatus]:
        """
        Get completion status for all users who have access to a task.
        
        Args:
            task_id: Task ID
            original_account_id: Account where task was originally created
            
        Returns:
            List of CompletionStatus for each user
        """
        if not self.gtasks_path:
            return []
        
        db_file = self.gtasks_path / 'task_completions.db'
        if not db_file.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, completion_status, completed_at
                FROM user_task_completions
                WHERE task_id = ? AND original_account_id = ?
            """, (task_id, original_account_id))
            
            rows = cursor.fetchall()
            conn.close()
            
            statuses = []
            for row in rows:
                # Get user email from users table
                user_email = self._get_user_email(row[0])
                
                statuses.append(CompletionStatus(
                    user_id=row[0],
                    user_email=user_email or row[0],  # Use ID as fallback
                    status=row[1],
                    completed_at=row[2]
                ))
            
            return statuses
            
        except Exception as e:
            logger.error(f"[SharedTaskAccessService] Error getting completion status: {e}")
        
        return []
    
    def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user's email from user ID"""
        if not self.gtasks_path:
            return None
        
        db_file = self.gtasks_path / 'users.db'
        if not db_file.exists():
            return None
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row[0]
            
        except Exception as e:
            logger.error(f"[SharedTaskAccessService] Error getting user email: {e}")
        
        return None
    
    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about shared tasks for a user.
        
        Args:
            user_id: User ID to get statistics for
            
        Returns:
            Dictionary with statistics
        """
        shared_with_me = self.get_shared_tasks_for_user(user_id)
        shared_by_me = self.get_tasks_shared_by_user(user_id)
        
        # Count completion status
        pending = sum(1 for task in shared_with_me if task.completion_status == 'pending')
        completed = sum(1 for task in shared_with_me if task.completion_status == 'completed')
        
        return {
            'shared_with_me_count': len(shared_with_me),
            'shared_by_me_count': len(shared_by_me),
            'pending_completion': pending,
            'completed': completed,
            'total_accounts_shared_with': len(set(task.original_account_id for task in shared_with_me))
        }
