#!/usr/bin/env python3
"""
Database Service for Turso DB
Handles database connections, schema creation, and CRUD operations.
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path


class DatabaseService:
    """
    Database service for Turso/SQLite operations.
    
    Manages:
    - User storage
    - Invitations
    - Connections
    - Task assignments (many-to-many)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database service.
        
        Args:
            db_path: Path to database file (defaults to ~/.gtasks/auth.db)
        """
        if db_path is None:
            # Use default path
            auth_dir = os.environ.get('GTASKS_AUTH_DIR', os.path.expanduser('~/.gtasks/auth'))
            os.makedirs(auth_dir, exist_ok=True)
            db_path = os.path.join(auth_dir, 'auth.db')
        
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        
        # Initialize schema
        self._create_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def _create_schema(self) -> None:
        """Create database schema if not exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT,
                qerds_token TEXT,
                created_at TEXT,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Create index on email
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        
        # Invitations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                invitation_id TEXT PRIMARY KEY,
                from_user_id TEXT,
                to_email TEXT NOT NULL,
                to_user_id TEXT,
                task_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                expires_at TEXT,
                FOREIGN KEY (from_user_id) REFERENCES users(user_id),
                FOREIGN KEY (to_user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create indexes for invitations
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(to_email)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invitations_status ON invitations(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invitations_from_user ON invitations(from_user_id)
        """)
        
        # Connections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                connection_id TEXT PRIMARY KEY,
                user_a_id TEXT NOT NULL,
                user_b_id TEXT NOT NULL,
                created_at TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_a_id) REFERENCES users(user_id),
                FOREIGN KEY (user_b_id) REFERENCES users(user_id)
            )
        """)
        
        # Create indexes for connections
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_connections_user_a ON connections(user_a_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_connections_user_b ON connections(user_b_id)
        """)
        
        # Task assignments table (many-to-many)
        # Note: No foreign key to tasks table since tasks come from external source (Google Tasks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_assignments (
                assignment_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                assigned_to_user_id TEXT NOT NULL,
                assigned_by_user_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                completed_at TEXT,
                assigned_at TEXT,
                FOREIGN KEY (assigned_to_user_id) REFERENCES users(user_id),
                FOREIGN KEY (assigned_by_user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create indexes for task assignments
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_task_user_assignment 
            ON task_assignments(task_id, assigned_to_user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assignments_user ON task_assignments(assigned_to_user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assignments_task ON task_assignments(task_id)
        """)
        
        conn.commit()
        print(f"Database schema created/verified at: {self.db_path}")
    
    # ==================== USER OPERATIONS ====================
    
    def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create a new user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (user_id, email, display_name, qerds_token, created_at, last_login, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data['user_id'],
                user_data['email'],
                user_data.get('display_name'),
                user_data.get('qerds_token'),
                user_data.get('created_at', datetime.now().isoformat()),
                user_data.get('last_login'),
                user_data.get('is_active', 1)
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"User with email {user_data['email']} already exists")
            return False
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by user ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['email', 'display_name', 'qerds_token', 'last_login', 'is_active']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return False
        
        values.append(user_id)
        
        cursor.execute(f"""
            UPDATE users SET {', '.join(set_clauses)} WHERE user_id = ?
        """, values)
        
        conn.commit()
        return cursor.rowcount > 0
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== INVITATION OPERATIONS ====================
    
    def create_invitation(self, invitation_data: Dict[str, Any]) -> bool:
        """Create a new invitation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO invitations (invitation_id, from_user_id, to_email, to_user_id, task_id, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invitation_data.get('invitation_id', str(uuid.uuid4())),
                invitation_data.get('from_user_id'),
                invitation_data['to_email'],
                invitation_data.get('to_user_id'),
                invitation_data.get('task_id'),
                invitation_data.get('status', 'pending'),
                invitation_data.get('created_at', datetime.now().isoformat()),
                invitation_data.get('expires_at', (datetime.now() + timedelta(days=7)).isoformat())
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_invitation_by_id(self, invitation_id: str) -> Optional[Dict[str, Any]]:
        """Get invitation by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM invitations WHERE invitation_id = ?", (invitation_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_pending_invitations_for_email(self, email: str) -> List[Dict[str, Any]]:
        """Get pending invitations for an email."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM invitations 
            WHERE to_email = ? AND status = 'pending'
            ORDER BY created_at DESC
        """, (email,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_invitations_from_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending invitations sent by a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM invitations 
            WHERE from_user_id = ? AND status = 'pending'
            ORDER BY created_at DESC
        """, (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_invitation_status(self, invitation_id: str, status: str, to_user_id: Optional[str] = None) -> bool:
        """Update invitation status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if to_user_id:
            cursor.execute("""
                UPDATE invitations SET status = ?, to_user_id = ? WHERE invitation_id = ?
            """, (status, to_user_id, invitation_id))
        else:
            cursor.execute("""
                UPDATE invitations SET status = ? WHERE invitation_id = ?
            """, (status, invitation_id))
        
        conn.commit()
        return cursor.rowcount > 0
    
    # ==================== CONNECTION OPERATIONS ====================
    
    def create_connection(self, connection_data: Dict[str, Any]) -> bool:
        """Create a new connection between two users."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO connections (connection_id, user_a_id, user_b_id, created_at, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                connection_data.get('connection_id', str(uuid.uuid4())),
                connection_data['user_a_id'],
                connection_data['user_b_id'],
                connection_data.get('created_at', datetime.now().isoformat()),
                connection_data.get('status', 'active')
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_connection(self, user_a_id: str, user_b_id: str) -> Optional[Dict[str, Any]]:
        """Get connection between two users (order independent)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM connections 
            WHERE (user_a_id = ? AND user_b_id = ?) OR (user_a_id = ? AND user_b_id = ?)
        """, (user_a_id, user_b_id, user_b_id, user_a_id))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all connections for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM connections 
            WHERE (user_a_id = ? OR user_b_id = ?) AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id, user_id))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_connection_status(self, connection_id: str, status: str) -> bool:
        """Update connection status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE connections SET status = ? WHERE connection_id = ?
        """, (status, connection_id))
        
        conn.commit()
        return cursor.rowcount > 0
    
    # ==================== TASK ASSIGNMENT OPERATIONS ====================
    
    def create_task_assignment(self, assignment_data: Dict[str, Any]) -> bool:
        """Create a task assignment."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO task_assignments (assignment_id, task_id, assigned_to_user_id, assigned_by_user_id, status, completed_at, assigned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment_data.get('assignment_id', str(uuid.uuid4())),
                assignment_data['task_id'],
                assignment_data['assigned_to_user_id'],
                assignment_data['assigned_by_user_id'],
                assignment_data.get('status', 'pending'),
                assignment_data.get('completed_at'),
                assignment_data.get('assigned_at', datetime.now().isoformat())
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_task_assignments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all assignments for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM task_assignments WHERE task_id = ?
        """, (task_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_task_assignments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all tasks assigned to a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM task_assignments WHERE assigned_to_user_id = ? ORDER BY assigned_at DESC
        """, (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_assigned_tasks(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks assigned to user with optional status filter."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM task_assignments 
                WHERE assigned_to_user_id = ? AND status = ?
                ORDER BY assigned_at DESC
            """, (user_id, status))
        else:
            cursor.execute("""
                SELECT * FROM task_assignments 
                WHERE assigned_to_user_id = ?
                ORDER BY assigned_at DESC
            """, (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_task_assignment_status(
        self, 
        task_id: str, 
        user_id: str, 
        status: str
    ) -> bool:
        """Update assignment status for specific task and user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        completed_at = datetime.now().isoformat() if status == 'completed' else None
        
        cursor.execute("""
            UPDATE task_assignments 
            SET status = ?, completed_at = ?
            WHERE task_id = ? AND assigned_to_user_id = ?
        """, (status, completed_at, task_id, user_id))
        
        conn.commit()
        return cursor.rowcount > 0
    
    def get_task_completion_status(self, task_id: str) -> Dict[str, Any]:
        """Get completion status for a task with multiple assignments."""
        assignments = self.get_task_assignments(task_id)
        
        total = len(assignments)
        completed = sum(1 for a in assignments if a['status'] == 'completed')
        pending = total - completed
        
        assigned_users = []
        for a in assignments:
            user = self.get_user_by_id(a['assigned_to_user_id'])
            if user:
                assigned_users.append({
                    'user_id': user['user_id'],
                    'display_name': user['display_name'],
                    'status': a['status'],
                    'completed_at': a.get('completed_at')
                })
        
        return {
            'task_id': task_id,
            'total_assignments': total,
            'completed_count': completed,
            'pending_count': pending,
            'assigned_users': assigned_users,
            'completion_percentage': (completed / total * 100) if total > 0 else 0
        }
    
    def delete_task_assignment(self, task_id: str, user_id: str) -> bool:
        """Delete a task assignment."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM task_assignments 
            WHERE task_id = ? AND assigned_to_user_id = ?
        """, (task_id, user_id))
        
        conn.commit()
        return cursor.rowcount > 0


# Singleton instance
_db_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get the default database service instance."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


if __name__ == "__main__":
    # Demo usage
    print("Database Service Demo")
    print("=" * 50)
    
    db = DatabaseService()
    
    # Create test user
    print("\n1. Creating test user...")
    test_user = {
        'user_id': 'test12345',
        'email': 'test@example.com',
        'display_name': 'Test User',
        'created_at': datetime.now().isoformat()
    }
    success = db.create_user(test_user)
    print(f"   User created: {success}")
    
    # Retrieve user
    print("\n2. Retrieving user...")
    user = db.get_user_by_id('test12345')
    if user:
        print(f"   Found: {user['display_name']} ({user['email']})")
    
    # Create second user
    print("\n3. Creating second user...")
    test_user2 = {
        'user_id': 'user26789',
        'email': 'user@example.com',
        'display_name': 'Second User'
    }
    db.create_user(test_user2)
    
    # Create connection
    print("\n4. Creating connection...")
    connection_success = db.create_connection({
        'user_a_id': 'test12345',
        'user_b_id': 'user26789'
    })
    print(f"   Connection created: {connection_success}")
    
    connections = db.get_user_connections('test12345')
    print(f"   User connections: {len(connections)}")
    
    # Test task assignments
    print("\n5. Testing task assignments...")
    db.create_task_assignment({
        'task_id': 'task001',
        'assigned_to_user_id': 'test12345',
        'assigned_by_user_id': 'user26789'
    })
    db.create_task_assignment({
        'task_id': 'task001',
        'assigned_to_user_id': 'user26789',
        'assigned_by_user_id': 'test12345'
    })
    
    status = db.get_task_completion_status('task001')
    print(f"   Task completion status: {status['completed_count']}/{status['total_assignments']}")
    print(f"   Assigned users: {[u['display_name'] for u in status['assigned_users']]}")
    
    # Update assignment status
    print("\n6. Updating assignment status...")
    db.update_task_assignment_status('task001', 'test12345', 'completed')
    status = db.get_task_completion_status('task001')
    print(f"   Updated: {status['completed_count']}/{status['total_assignments']} completed")
    
    # Test invitation
    print("\n7. Testing invitation...")
    db.create_invitation({
        'from_user_id': 'test12345',
        'to_email': 'newuser@example.com',
        'task_id': 'task002'
    })
    
    invitations = db.get_pending_invitations_for_email('newuser@example.com')
    print(f"   Pending invitations: {len(invitations)}")
    
    print("\n" + "=" * 50)
    print("Database demo completed!")
    
    # Close connection
    db.close()
