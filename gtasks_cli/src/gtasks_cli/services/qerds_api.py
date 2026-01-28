#!/usr/bin/env python3
"""
QERDS API Client
Handles authentication with QERDS.com for user login.
Only 2 APIs used:
1. Validate Token
2. Get Account Details
"""

import os
import json
import time
import hashlib
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QerdsAccountDetails:
    """Account details returned from QERDS API."""
    user_id: str
    email: str
    display_name: str
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'email': self.email,
            'display_name': self.display_name,
            'created_at': self.created_at
        }


class QerdsApiClient:
    """
    Client for QERDS.com authentication APIs.
    
    Features:
    - Token validation
    - Account details retrieval
    - Dummy fallback for testing without QERDS dependency
    """
    
    def __init__(
        self,
        base_url: str = "https://qerds.com/tools/tgs",
        use_dummy_fallback: bool = True,
        dummy_data_file: Optional[str] = None
    ):
        """
        Initialize the QERDS API client.
        
        Args:
            base_url: QERDS API base URL
            use_dummy_fallback: Whether to use dummy data when API fails
            dummy_data_file: Path to custom dummy data file
        """
        self.base_url = base_url
        self.use_dummy_fallback = use_dummy_fallback
        self.dummy_data_file = dummy_data_file or self._get_default_dummy_file()
        self._dummy_data_cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_default_dummy_file(self) -> str:
        """Get default dummy data file path."""
        # Look for dummy data in various locations
        possible_paths = [
            "qerds_dummy_data.json",
            os.path.expanduser("~/.gtasks/qerds_dummy_data.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "qerds_dummy_data.json"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return possible_paths[0]  # Return first path (will be created if needed)
    
    def _load_dummy_data(self) -> Dict[str, Dict[str, Any]]:
        """Load dummy data from file or create default."""
        if self._dummy_data_cache:
            return self._dummy_data_cache
        
        default_dummy_data = {
            "demo_token_123": {
                "user_id": "demo12345",
                "email": "demo@example.com",
                "display_name": "Demo User",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "test_token_456": {
                "user_id": "test67890",
                "email": "test@example.com",
                "display_name": "Test User",
                "created_at": "2024-01-15T00:00:00Z"
            },
            "admin_token_789": {
                "user_id": "admin11111",
                "email": "admin@example.com",
                "display_name": "Admin User",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
        
        try:
            if os.path.exists(self.dummy_data_file):
                with open(self.dummy_data_file, 'r') as f:
                    self._dummy_data_cache = json.load(f)
            else:
                # Create default dummy data file
                os.makedirs(os.path.dirname(self.dummy_data_file), exist_ok=True) if os.path.dirname(self.dummy_data_file) else None
                with open(self.dummy_data_file, 'w') as f:
                    json.dump(default_dummy_data, f, indent=2)
                self._dummy_data_cache = default_dummy_data
        except Exception as e:
            print(f"Warning: Could not load dummy data file: {e}")
            self._dummy_data_cache = default_dummy_data
        
        return self._dummy_data_cache
    
    def _save_dummy_data(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Save dummy data to file."""
        try:
            with open(self.dummy_data_file, 'w') as f:
                json.dump(data, f, indent=2)
            self._dummy_data_cache = data
        except Exception as e:
            print(f"Warning: Could not save dummy data file: {e}")
    
    def validate_token(self, token: str) -> tuple[bool, str]:
        """
        Validate a QERDS authentication token.
        
        Args:
            token: QERDS authentication token
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Try dummy fallback first if enabled
        if self.use_dummy_fallback:
            dummy_data = self._load_dummy_data()
            if token in dummy_data:
                print(f"[QERDS API] Dummy validation: Token '{token[:10]}...' is valid")
                return True, "Token validated (dummy mode)"
        
        # Try actual API call
        try:
            response = requests.post(
                f"{self.base_url}/validate-token",
                json={"token": token},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    print(f"[QERDS API] Token validated successfully")
                    return True, "Token validated"
                else:
                    print(f"[QERDS API] Token validation failed: {data.get('message')}")
                    return False, data.get('message', 'Invalid token')
            else:
                print(f"[QERDS API] Validation failed with status: {response.status_code}")
                
        except requests.RequestException as e:
            print(f"[QERDS API] Request failed: {e}")
        
        # Fallback to dummy if enabled
        if self.use_dummy_fallback:
            print(f"[QERDS API] Falling back to dummy validation")
            return True, "Token validated (dummy fallback)"
        
        return False, "Could not validate token"
    
    def get_account_details(self, token: str) -> Optional[QerdsAccountDetails]:
        """
        Get account details from QERDS using authentication token.
        
        Args:
            token: QERDS authentication token
            
        Returns:
            QerdsAccountDetails if successful, None otherwise
        """
        # Try dummy fallback first if enabled
        if self.use_dummy_fallback:
            dummy_data = self._load_dummy_data()
            if token in dummy_data:
                data = dummy_data[token]
                print(f"[QERDS API] Dummy account details for '{token[:10]}...'")
                return QerdsAccountDetails(
                    user_id=data['user_id'],
                    email=data['email'],
                    display_name=data['display_name'],
                    created_at=data['created_at']
                )
        
        # Try actual API call
        try:
            response = requests.get(
                f"{self.base_url}/account-details",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"[QERDS API] Account details retrieved")
                return QerdsAccountDetails(
                    user_id=data['user_id'],
                    email=data['email'],
                    display_name=data.get('display_name', data['email'].split('@')[0]),
                    created_at=data.get('created_at', datetime.now().isoformat())
                )
            else:
                print(f"[QERDS API] Account details failed with status: {response.status_code}")
                
        except requests.RequestException as e:
            print(f"[QERDS API] Request failed: {e}")
        
        # Fallback to dummy if enabled
        if self.use_dummy_fallback:
            print(f"[QERDS API] Falling back to dummy account details")
            # Create dummy account details from token
            dummy_data = self._load_dummy_data()
            
            # Generate dummy data from token if not in cache
            if token not in dummy_data:
                # Create new dummy entry
                email = f"user_{token[:8]}@example.com"
                user_id = f"user{hashlib.md5(token.encode()).hexdigest()[:8]}"
                dummy_data[token] = {
                    "user_id": user_id,
                    "email": email,
                    "display_name": email.split('@')[0].replace('_', ' ').title(),
                    "created_at": datetime.now().isoformat()
                }
                self._save_dummy_data(dummy_data)
            
            data = dummy_data[token]
            return QerdsAccountDetails(
                user_id=data['user_id'],
                email=data['email'],
                display_name=data['display_name'],
                created_at=data['created_at']
            )
        
        return None
    
    def authenticate(self, token: str) -> tuple[bool, Optional[QerdsAccountDetails], str]:
        """
        Complete authentication flow with QERDS.
        
        Args:
            token: QERDS authentication token
            
        Returns:
            Tuple of (success, account_details, message)
        """
        # Validate token
        is_valid, message = self.validate_token(token)
        if not is_valid:
            return False, None, message
        
        # Get account details
        account_details = self.get_account_details(token)
        if account_details is None:
            return False, None, "Could not retrieve account details"
        
        return True, account_details, "Authentication successful"
    
    def add_dummy_user(
        self,
        token: str,
        email: str,
        display_name: str
    ) -> bool:
        """
        Add a dummy user for testing.
        
        Args:
            token: Token to associate with user
            email: User email
            display_name: User display name
            
        Returns:
            True if successful
        """
        dummy_data = self._load_dummy_data()
        
        from gtasks_cli.utils.user_id_generator import generate_user_id
        user_id = generate_user_id(email)
        
        dummy_data[token] = {
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "created_at": datetime.now().isoformat()
        }
        
        self._save_dummy_data(dummy_data)
        print(f"[QERDS API] Added dummy user: {email} with ID {user_id}")
        return True
    
    def list_dummy_users(self) -> Dict[str, Dict[str, str]]:
        """List all dummy users."""
        return self._load_dummy_data()


# Singleton instance
_qerds_client: Optional[QerdsApiClient] = None


def get_qerds_client() -> QerdsApiClient:
    """Get the default QERDS API client instance."""
    global _qerds_client
    if _qerds_client is None:
        _qerds_client = QerdsApiClient()
    return _qerds_client


def authenticate_with_qerds(token: str) -> tuple[bool, Optional[QerdsAccountDetails], str]:
    """
    Convenience function to authenticate with QERDS.
    
    Args:
        token: QERDS authentication token
        
    Returns:
        Tuple of (success, account_details, message)
    """
    return get_qerds_client().authenticate(token)


if __name__ == "__main__":
    # Demo usage
    print("QERDS API Client Demo")
    print("=" * 50)
    
    client = QerdsApiClient(use_dummy_fallback=True)
    
    # Test with dummy tokens
    test_tokens = ["demo_token_123", "test_token_456", "new_custom_token"]
    
    for token in test_tokens:
        print(f"\nTesting token: {token[:15]}...")
        success, details, message = client.authenticate(token)
        
        print(f"  Success: {success}")
        print(f"  Message: {message}")
        
        if success and details:
            print(f"  User ID: {details.user_id}")
            print(f"  Email: {details.email}")
            print(f"  Display Name: {details.display_name}")
    
    # Add custom dummy user
    print("\n" + "=" * 50)
    print("Adding custom dummy user...")
    client.add_dummy_user(
        token="my_custom_token",
        email="myuser@example.com",
        display_name="My Custom User"
    )
    
    # Test the new user
    success, details, message = client.authenticate("my_custom_token")
    if success:
        print(f"Custom user created: {details.display_name} ({details.user_id})")
    
    # List all dummy users
    print("\n" + "=" * 50)
    print("All dummy users:")
    users = client.list_dummy_users()
    for token, data in users.items():
        print(f"  {token}: {data['email']} ({data['user_id']})")
