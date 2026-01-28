#!/usr/bin/env python3
"""
Task Sharing Service
Handles task assignment to @account tags and tracks completion status per user.

Features:
- Assign tasks to @account tags
- Track completion status per user
- Get tasks shared with a user
- Mark tasks as complete for specific users
- Provide completion statistics for shared tasks
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Tuple
from pathlib import Path


class TaskSharingError(Exception):
    """Exception raised for task sharing errors."""
    pass


class TaskSharingService:
    """
    Service for managing task sharing with @account tags.
    
    This service tracks:
    - Which tasks are assigned to which users via @account tags
    - Completion status per user (not all users need to complete)
    - Statistics about task completion across multiple users
    
    A single task can have multiple @account tags, each representing
    a different user the task is shared with.
    """
    
    def __init__(
        self,
        data_dir: Optional[str] = None
    ):
        """
        Initialize the task sharing service.
        
        Args:
            data_dir: Directory for storing task sharing data
        """
        self.data_dir = data_dir or self._get_default_data_dir()
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # File paths
        self.task_sharing_file = os.path.join(self.data_dir, "task_sharing.json")
        
        # In-memory cache
        # Structure: {task_id: {user_id: {status, completed_at, shared_by}}}
        self._sharing_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # Load existing data
        self._load_data()
    
    def _get_default_data_dir(self) -> str:
        """Get default data directory."""
        if os.environ.get('GTASKS_AUTH_DIR'):
            return os.environ['GTASKS_AUTH_DIR']
        
        possible_paths = [
            os.path.expanduser("~/.gtasks/auth"),
            os.path.join(os.getcwd(), ".gtasks_auth"),
        ]
        
        for path in possible_paths:
            try:
                os.makedirs(path, exist_ok=True)
                return path
            except Exception:
                continue
        
        return os.path.expanduser("~/.gtasks/auth")
    
    def _load_data(self) -> None:
        """Load task sharing data from file."""
        if os.path.exists(self.task_sharing_file):
            try:
                with open(self.task_sharing_file, 'r') as f:
                    data = json.load(f)
                    self._sharing_cache = data.get('sharing', {})
            except Exception as e:
                print(f"Warning: Could not load task sharing data: {e}")
    
    def _save_data(self) -> None:
        """Save task sharing data to file."""
        try:
            data = {
                'sharing': self._sharing_cache,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.task_sharing_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save task sharing data: {e}")
    
    def share_task_with_user(
        self,
        task_id: str,
        user_id: str,
        shared_by: str,
        task_title: Optional[str] = None,
        task_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Share a task with a user via @account tag.
        
        Args:
            task_id: ID of the task
            user_id: User ID to share with
            shared_by: User ID who is sharing the task
            task_title: Optional task title
            task_description: Optional task description
            
        Returns:
            Dict with sharing details
        """
        # Initialize task if not exists
        if task_id not in self._sharing_cache:
            self._sharing_cache[task_id] = {}
        
        # Check if already shared
        if user_id in self._sharing_cache[task_id]:
            return self._sharing_cache[task_id][user_id]
        
        # Create sharing record
        sharing = {
            'task_id': task_id,
            'user_id': user_id,
            'shared_by': shared_by,
            'task_title': task_title,
            'task_description': task_description,
            'status': 'pending',  # pending, completed
            'completed_at': None,
            'shared_at': datetime.now().isoformat()
        }
        
        self._sharing_cache[task_id][user_id] = sharing
        self._save_data()
        
        return sharing
    
    def share_task_with_users(
        self,
        task_id: str,
        user_ids: List[str],
        shared_by: str,
        task_title: Optional[str] = None,
        task_description: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Share a task with multiple users.
        
        Args:
            task_id: ID of the task
            user_ids: List of user IDs to share with
            shared_by: User ID who is sharing the task
            task_title: Optional task title
            task_description: Optional task description
            
        Returns:
            List of sharing details
        """
        shared = []
        for user_id in user_ids:
            sharing = self.share_task_with_user(
                task_id=task_id,
                user_id=user_id,
                shared_by=shared_by,
                task_title=task_title,
                task_description=task_description
            )
            shared.append(sharing)
        
        return shared
    
    def mark_task_complete(
        self,
        task_id: str,
        user_id: str,
        completed_by: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Mark a task as complete for a specific user.
        
        Args:
            task_id: ID of the task
            user_id: User ID who completed the task
            completed_by: User ID (should match user_id for self-completion)
            
        Returns:
            Tuple of (success, message)
        """
        if task_id not in self._sharing_cache:
            return False, "Task not found in sharing records"
        
        if user_id not in self._sharing_cache[task_id]:
            return False, "Task not shared with this user"
        
        sharing = self._sharing_cache[task_id][user_id]
        sharing['status'] = 'completed'
        sharing['completed_at'] = datetime.now().isoformat()
        
        self._save_data()
        
        return True, f"Task marked as complete for user"
    
    def mark_task_incomplete(
        self,
        task_id: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """
        Mark a task as incomplete for a specific user.
        
        Args:
            task_id: ID of the task
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        if task_id not in self._sharing_cache:
            return False, "Task not found in sharing records"
        
        if user_id not in self._sharing_cache[task_id]:
            return False, "Task not shared with this user"
        
        sharing = self._sharing_cache[task_id][user_id]
        sharing['status'] = 'pending'
        sharing['completed_at'] = None
        
        self._save_data()
        
        return True, f"Task marked as incomplete for user"
    
    def get_sharing_for_task(self, task_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all sharing records for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dict mapping user_id to sharing details
        """
        return self._sharing_cache.get(task_id, {})
    
    def get_tasks_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks shared with a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of sharing details with task info
        """
        tasks = []
        for task_id, sharing_by_user in self._sharing_cache.items():
            if user_id in sharing_by_user:
                task_info = sharing_by_user[user_id].copy()
                task_info['task_id'] = task_id
                tasks.append(task_info)
        
        return tasks
    
    def get_pending_tasks_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all pending tasks for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of pending sharing details
        """
        pending = []
        for task in self.get_tasks_for_user(user_id):
            if task['status'] == 'pending':
                pending.append(task)
        
        return pending
    
    def get_completed_tasks_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all completed tasks for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of completed sharing details
        """
        completed = []
        for task in self.get_tasks_for_user(user_id):
            if task['status'] == 'completed':
                completed.append(task)
        
        return completed
    
    def get_task_completion_stats(self, task_id: str) -> Dict[str, Any]:
        """
        Get completion statistics for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dict with completion statistics
        """
        if task_id not in self._sharing_cache:
            return {
                'total_assignments': 0,
                'completed': 0,
                'pending': 0,
                'completion_rate': 0.0
            }
        
        sharing = self._sharing_cache[task_id]
        total = len(sharing)
        completed = sum(1 for s in sharing.values() if s['status'] == 'completed')
        pending = total - completed
        
        return {
            'total_assignments': total,
            'completed': completed,
            'pending': pending,
            'completion_rate': (completed / total * 100) if total > 0 else 0.0
        }
    
    def revoke_task_sharing(
        self,
        task_id: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """
        Revoke task sharing for a specific user.
        
        Args:
            task_id: ID of the task
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        if task_id not in self._sharing_cache:
            return False, "Task not found in sharing records"
        
        if user_id not in self._sharing_cache[task_id]:
            return False, "Task not shared with this user"
        
        del self._sharing_cache[task_id][user_id]
        
        # Clean up empty tasks
        if not self._sharing_cache[task_id]:
            del self._sharing_cache[task_id]
        
        self._save_data()
        
        return True, "Task sharing revoked"
    
    def delete_task_sharing(self, task_id: str) -> Tuple[bool, str]:
        """
        Delete all sharing records for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Tuple of (success, message)
        """
        if task_id not in self._sharing_cache:
            return False, "Task not found in sharing records"
        
        del self._sharing_cache[task_id]
        self._save_data()
        
        return True, "All sharing records deleted for task"
    
    def is_task_shared_with_user(self, task_id: str, user_id: str) -> bool:
        """
        Check if a task is shared with a user.
        
        Args:
            task_id: ID of the task
            user_id: User ID
            
        Returns:
            True if task is shared with user
        """
        return (
            task_id in self._sharing_cache and
            user_id in self._sharing_cache[task_id]
        )
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Get overall task sharing statistics.
        
        Returns:
            Dict with statistics
        """
        total_tasks = len(self._sharing_cache)
        total_shares = sum(len(sharing) for sharing in self._sharing_cache.values())
        total_completed = sum(
            1 for sharing in self._sharing_cache.values()
            for s in sharing.values() if s['status'] == 'completed'
        )
        
        return {
            'total_shared_tasks': total_tasks,
            'total_shares': total_shares,
            'total_completed': total_completed,
            'total_pending': total_shares - total_completed
        }


# Singleton instance
_task_sharing_service: Optional[TaskSharingService] = None


def get_task_sharing_service() -> TaskSharingService:
    """Get the default task sharing service instance."""
    global _task_sharing_service
    if _task_sharing_service is None:
        _task_sharing_service = TaskSharingService()
    return _task_sharing_service


if __name__ == "__main__":
    # Demo usage
    print("Task Sharing Service Demo")
    print("=" * 50)
    
    service = TaskSharingService()
    
    # Share a task with multiple users
    print("\n1. Sharing task 'task123' with multiple users...")
    service.share_task_with_user(
        task_id="task123",
        user_id="user_abc",
        shared_by="owner123",
        task_title="Review document",
        task_description="Please review this document"
    )
    service.share_task_with_user(
        task_id="task123",
        user_id="user_xyz",
        shared_by="owner123",
        task_title="Review document",
        task_description="Please review this document"
    )
    
    # Share another task
    print("\n2. Sharing task 'task456' with one user...")
    service.share_task_with_user(
        task_id="task456",
        user_id="user_abc",
        shared_by="owner123",
        task_title="Complete survey"
    )
    
    # Get task completion stats
    print("\n3. Task completion statistics:")
    stats = service.get_task_completion_stats("task123")
    print(f"   Task 123: {stats['completed']}/{stats['total_assignments']} completed")
    print(f"   Completion rate: {stats['completion_rate']:.1f}%")
    
    # Mark task as complete for one user
    print("\n4. User 'user_abc' completing task 'task123'...")
    success, message = service.mark_task_complete("task123", "user_abc")
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    
    # Updated stats
    print("\n5. Updated task completion statistics:")
    stats = service.get_task_completion_stats("task123")
    print(f"   Task 123: {stats['completed']}/{stats['total_assignments']} completed")
    print(f"   Completion rate: {stats['completion_rate']:.1f}%")
    
    # Get tasks for user
    print("\n6. Tasks for user_abc:")
    tasks = service.get_tasks_for_user("user_abc")
    for task in tasks:
        print(f"   - {task['task_title']} ({task['status']})")
    
    # Get pending tasks
    print("\n7. Pending tasks for user_abc:")
    pending = service.get_pending_tasks_for_user("user_abc")
    print(f"   Count: {len(pending)}")
    for task in pending:
        print(f"   - {task['task_title']}")
    
    # Overall stats
    print("\n8. Overall statistics:")
    overall = service.get_overall_stats()
    for key, value in overall.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 50)
    print("Demo completed!")
