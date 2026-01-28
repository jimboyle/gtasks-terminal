#!/usr/bin/env python3
"""
User Model
Represents a user in the gtasks authentication system.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any


class User:
    """
    User model for authentication and account management.
    
    Attributes:
        user_id: Unique identifier (e.g., "abc12345")
        email: Full email address
        display_name: User-friendly name
        qerds_token: QERDS authentication token
        created_at: Account creation timestamp
        last_login: Last login timestamp
        is_active: Whether the account is active
        is_dummy: Whether this is a dummy/test account
    """
    
    def __init__(
        self,
        user_id: str,
        email: str,
        display_name: Optional[str] = None,
        qerds_token: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
        is_active: bool = True,
        is_dummy: bool = False
    ):
        """
        Initialize a User instance.
        
        Args:
            user_id: Unique user identifier
            email: Full email address
            display_name: User-friendly name (defaults to email prefix)
            qerds_token: QERDS authentication token
            created_at: Creation timestamp (defaults to now)
            last_login: Last login timestamp
            is_active: Account active status
            is_dummy: Whether this is a dummy/test account
        """
        self.user_id = user_id
        self.email = email
        self.display_name = display_name or self._generate_display_name(email)
        self.qerds_token = qerds_token
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
        self.is_active = is_active
        self.is_dummy = is_dummy
    
    def _generate_display_name(self, email: str) -> str:
        """Generate a display name from email."""
        prefix = email.split('@')[0]
        # Convert to title case and replace underscores/dots with spaces
        name = prefix.replace('_', ' ').replace('.', ' ')
        return name.title()
    
    @classmethod
    def create_from_email(cls, email: str, qerds_token: Optional[str] = None) -> 'User':
        """
        Create a new User from an email address.
        
        Args:
            email: Full email address
            qerds_token: QERDS authentication token
            
        Returns:
            New User instance
        """
        from gtasks_cli.utils.user_id_generator import generate_user_id
        
        user_id = generate_user_id(email)
        
        return cls(
            user_id=user_id,
            email=email,
            qerds_token=qerds_token
        )
    
    def update_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.now()
    
    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
    
    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert User to dictionary for storage."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'display_name': self.display_name,
            'qerds_token': self.qerds_token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'is_dummy': self.is_dummy
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary."""
        created_at = None
        last_login = None
        
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        if data.get('last_login'):
            last_login = datetime.fromisoformat(data['last_login'])
        
        return cls(
            user_id=data['user_id'],
            email=data['email'],
            display_name=data.get('display_name'),
            qerds_token=data.get('qerds_token'),
            created_at=created_at,
            last_login=last_login,
            is_active=data.get('is_active', True),
            is_dummy=data.get('is_dummy', False)
        )
    
    def __repr__(self) -> str:
        return f"User(user_id='{self.user_id}', email='{self.email}', display_name='{self.display_name}')"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return False
        return self.user_id == other.user_id
    
    def __hash__(self) -> int:
        return hash(self.user_id)


class UserSession:
    """
    User session management.
    
    Attributes:
        session_id: Unique session identifier
        user_id: Associated user ID
        created_at: Session creation time
        expires_at: Session expiration time
        is_valid: Whether session is still valid
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        is_valid: bool = True
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.created_at = created_at or datetime.now()
        self.expires_at = expires_at
        self.is_valid = is_valid
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def invalidate(self) -> None:
        """Invalidate the session."""
        self.is_valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_valid': self.is_valid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create session from dictionary."""
        created_at = None
        expires_at = None
        
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        return cls(
            session_id=data.get('session_id'),
            user_id=data.get('user_id'),
            created_at=created_at,
            expires_at=expires_at,
            is_valid=data.get('is_valid', True)
        )


if __name__ == "__main__":
    # Demo usage
    print("User Model Demo")
    print("=" * 50)
    
    # Create user from email
    user = User.create_from_email("john.doe@example.com")
    print(f"Created user: {user}")
    print(f"User ID: {user.user_id}")
    print(f"Display name: {user.display_name}")
    print()
    
    # Test session
    session = UserSession(user_id=user.user_id)
    print(f"Session created: {session.session_id}")
    print(f"Session valid: {session.is_valid}")
    print()
    
    # Test serialization
    user_dict = user.to_dict()
    print("User as dictionary:")
    for key, value in user_dict.items():
        print(f"  {key}: {value}")
    print()
    
    # Test deserialization
    user2 = User.from_dict(user_dict)
    print(f"Restored user: {user2}")
    print(f"Equal to original: {user == user2}")
