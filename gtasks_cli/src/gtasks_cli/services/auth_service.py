#!/usr/bin/env python3
"""
Authentication Service
Handles user authentication, session management, and login/logout operations.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

from gtasks_cli.models.user import User, UserSession
from gtasks_cli.services.qerds_api import QerdsApiClient, QerdsAccountDetails, get_qerds_client


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""
    pass


class AuthService:
    """
    Authentication service for managing user login and sessions.
    
    Features:
    - Login with QERDS token
    - Session management
    - User persistence
    - Logout functionality
    """
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        qerds_client: Optional[QerdsApiClient] = None,
        session_duration_hours: int = 24
    ):
        """
        Initialize the authentication service.
        
        Args:
            data_dir: Directory for storing auth data
            qerds_client: QERDS API client instance
            session_duration_hours: Session validity duration
        """
        self.data_dir = data_dir or self._get_default_data_dir()
        self.qerds_client = qerds_client or get_qerds_client()
        self.session_duration = timedelta(hours=session_duration_hours)
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # File paths
        self.users_file = os.path.join(self.data_dir, "users.json")
        self.sessions_file = os.path.join(self.data_dir, "sessions.json")
        
        # In-memory caches
        self._users_cache: Dict[str, User] = {}
        self._sessions_cache: Dict[str, UserSession] = {}
        
        # Load existing data
        self._load_users()
        self._load_sessions()
    
    def _get_default_data_dir(self) -> str:
        """Get default data directory for auth storage."""
        # Check environment variable first
        if os.environ.get('GTASKS_AUTH_DIR'):
            return os.environ['GTASKS_AUTH_DIR']
        
        # Fall back to default locations
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
        
        # Last resort
        return os.path.expanduser("~/.gtasks/auth")
    
    def _load_users(self) -> None:
        """Load users from file."""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        user = User.from_dict(user_data)
                        self._users_cache[user.user_id] = user
            except Exception as e:
                print(f"Warning: Could not load users: {e}")
    
    def _save_users(self) -> None:
        """Save users to file."""
        try:
            data = {
                'users': [user.to_dict() for user in self._users_cache.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save users: {e}")
    
    def _load_sessions(self) -> None:
        """Load sessions from file."""
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r') as f:
                    data = json.load(f)
                    for session_data in data.get('sessions', []):
                        session = UserSession.from_dict(session_data)
                        if session.is_valid and not session.is_expired():
                            self._sessions_cache[session.session_id] = session
            except Exception as e:
                print(f"Warning: Could not load sessions: {e}")
    
    def _save_sessions(self) -> None:
        """Save sessions to file."""
        try:
            data = {
                'sessions': [session.to_dict() for session in self._sessions_cache.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.sessions_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save sessions: {e}")
    
    def login(
        self,
        email: str,
        api_key: str,
        is_dummy: bool = False
    ) -> Dict[str, Any]:
        """
        Login user with email and API key.
        
        Args:
            email: User email address
            api_key: QERDS API key
            is_dummy: Whether to use dummy authentication for testing
            
        Returns:
            Dict with success status, user data, and message
        """
        try:
            # Check if user already exists
            existing_user = self.get_user_by_email(email)
            
            if existing_user:
                # Update existing user
                existing_user.qerds_token = api_key
                existing_user.update_login()
                self._save_users()
                return {
                    'success': True,
                    'user': existing_user.to_dict(),
                    'message': 'Login successful (existing user)',
                    'is_new_user': False
                }
            
            # Create new user
            user = User.create_from_email(
                email=email,
                qerds_token=api_key
            )
            
            if is_dummy:
                user.is_dummy = True
                user.display_name = email.split('@')[0].title()
            
            # Save new user
            self._users_cache[user.user_id] = user
            self._save_users()
            
            return {
                'success': True,
                'user': user.to_dict(),
                'message': 'Login successful (new user created)',
                'is_new_user': True
            }
            
        except Exception as e:
            print(f"Login error: {e}")
            return {
                'success': False,
                'error': f'Login failed: {str(e)}',
                'user': None,
                'message': str(e)
            }
    
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by user ID (convenience method).
        
        Args:
            user_id: User ID
            
        Returns:
            User instance or None
        """
        return self.get_user_by_id(user_id)
    
    def logout(self, session_id: str) -> tuple[bool, str]:
        """
        Logout user by invalidating session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            Tuple of (success, message)
        """
        if session_id in self._sessions_cache:
            session = self._sessions_cache[session_id]
            session.invalidate()
            self._save_sessions()
            return True, "Logged out successfully"
        
        return False, "Session not found"
    
    def logout_all_sessions(self, user_id: str) -> tuple[bool, str]:
        """
        Logout user from all sessions.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        sessions_to_remove = [
            session_id for session_id, session in self._sessions_cache.items()
            if session.user_id == user_id
        ]
        
        for session_id in sessions_to_remove:
            if session_id in self._sessions_cache:
                self._sessions_cache[session_id].invalidate()
        
        self._save_sessions()
        
        if sessions_to_remove:
            return True, f"Logged out from {len(sessions_to_remove)} sessions"
        return True, "No active sessions found"
    
    def create_session(self, user_id: str) -> UserSession:
        """
        Create a new session for user.
        
        Args:
            user_id: User ID
            
        Returns:
            New UserSession instance
        """
        session = UserSession(
            user_id=user_id,
            expires_at=datetime.now() + self.session_duration
        )
        
        self._sessions_cache[session.session_id] = session
        self._save_sessions()
        
        return session
    
    def validate_session(self, session_id: str) -> tuple[bool, Optional[User], str]:
        """
        Validate a session and return associated user.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            Tuple of (is_valid, user, message)
        """
        if session_id not in self._sessions_cache:
            return False, None, "Session not found"
        
        session = self._sessions_cache[session_id]
        
        if not session.is_valid:
            return False, None, "Session invalidated"
        
        if session.is_expired():
            return False, None, "Session expired"
        
        user = self.get_user_by_id(session.user_id)
        if user is None:
            return False, None, "User not found"
        
        if not user.is_active:
            return False, None, "User account deactivated"
        
        return True, user, "Session valid"
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by user ID."""
        return self._users_cache.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        for user in self._users_cache.values():
            if user.email.lower() == email.lower():
                return user
        return None
    
    def get_all_users(self) -> List[User]:
        """Get all registered users."""
        return list(self._users_cache.values())
    
    def deactivate_user(self, user_id: str) -> tuple[bool, str]:
        """
        Deactivate a user account.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        if user_id in self._users_cache:
            self._users_cache[user_id].deactivate()
            self._save_users()
            # Logout from all sessions
            self.logout_all_sessions(user_id)
            return True, "User deactivated"
        
        return False, "User not found"
    
    def activate_user(self, user_id: str) -> tuple[bool, str]:
        """
        Activate a user account.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        if user_id in self._users_cache:
            self._users_cache[user_id].activate()
            self._save_users()
            return True, "User activated"
        
        return False, "User not found"
    
    def delete_user(self, user_id: str) -> tuple[bool, str]:
        """
        Delete a user account.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        if user_id in self._users_cache:
            # Logout from all sessions
            self.logout_all_sessions(user_id)
            # Remove user
            del self._users_cache[user_id]
            self._save_users()
            return True, "User deleted"
        
        return False, "User not found"
    
    def get_session_count(self, user_id: str) -> int:
        """Get number of active sessions for user."""
        count = 0
        for session in self._sessions_cache.values():
            if session.user_id == user_id and session.is_valid and not session.is_expired():
                count += 1
        return count
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from cache."""
        expired_sessions = [
            session_id for session_id, session in self._sessions_cache.items()
            if session.is_expired() or not session.is_valid
        ]
        
        for session_id in expired_sessions:
            del self._sessions_cache[session_id]
        
        if expired_sessions:
            self._save_sessions()
        
        return len(expired_sessions)


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the default authentication service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def login_with_token(qerds_token: str) -> tuple[bool, Optional[User], str]:
    """
    Convenience function to login with QERDS token.
    
    Args:
        qerds_token: QERDS authentication token
        
    Returns:
        Tuple of (success, user, message)
    """
    return get_auth_service().login(qerds_token)


def validate_session(session_id: str) -> tuple[bool, Optional[User], str]:
    """
    Convenience function to validate a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Tuple of (is_valid, user, message)
    """
    return get_auth_service().validate_session(session_id)


def logout(session_id: str) -> tuple[bool, str]:
    """
    Convenience function to logout.
    
    Args:
        session_id: Session ID
        
    Returns:
        Tuple of (success, message)
    """
    return get_auth_service().logout(session_id)


if __name__ == "__main__":
    # Demo usage
    print("Authentication Service Demo")
    print("=" * 50)
    
    auth_service = AuthService()
    
    # Test login with dummy token
    print("\n1. Testing login with dummy token...")
    success, user, message = auth_service.login("demo_token_123")
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    if user:
        print(f"   User: {user.display_name} ({user.user_id})")
        print(f"   Email: {user.email}")
    
    # Create session
    if user:
        print("\n2. Creating session...")
        session = auth_service.create_session(user.user_id)
        print(f"   Session ID: {session.session_id}")
        print(f"   Expires at: {session.expires_at}")
        
        # Validate session
        print("\n3. Validating session...")
        valid, validated_user, msg = auth_service.validate_session(session.session_id)
        print(f"   Valid: {valid}")
        print(f"   Message: {msg}")
        if validated_user:
            print(f"   User: {validated_user.display_name}")
        
        # Logout
        print("\n4. Testing logout...")
        success, msg = auth_service.logout(session.session_id)
        print(f"   Success: {success}")
        print(f"   Message: {msg}")
        
        # Validate again (should fail)
        print("\n5. Validating expired session...")
        valid, _, msg = auth_service.validate_session(session.session_id)
        print(f"   Valid: {valid}")
        print(f"   Message: {msg}")
    
    # Test with new token
    print("\n6. Testing login with new token...")
    success, user, message = auth_service.login("new_user_token")
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    if user:
        print(f"   User: {user.display_name} ({user.user_id})")
    
    # List all users
    print("\n7. All registered users:")
    users = auth_service.get_all_users()
    for u in users:
        print(f"   - {u.display_name} ({u.email}): {u.user_id}")
    
    print("\n" + "=" * 50)
    print("Demo completed!")
