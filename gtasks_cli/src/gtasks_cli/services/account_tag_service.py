#!/usr/bin/env python3
"""
Account Tag Service
Handles parsing and management of @account tags for task sharing and user connections.

Features:
- Parse @account tags from task descriptions
- Store per-user tag mappings
- Find users by their account tags
- Support for tag-based task assignment
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Tuple
from pathlib import Path


class AccountTagError(Exception):
    """Exception raised for account tag errors."""
    pass


class AccountTagService:
    """
    Service for managing account tags in tasks.
    
    Account tags are special tags in the format [@account_name] that represent
    user accounts. When a task contains an account tag, it means the task is
    assigned to or shared with that user account.
    
    Features:
    - Parse and extract @account tags from task descriptions
    - Store per-user tag mappings
    - Find users by their account tags
    - Support for tag-based task assignment
    """
    
    # Pattern to match account tags: [@tagname] or [@tag_name-123]
    ACCOUNT_TAG_PATTERN = re.compile(r'\[@([a-zA-Z0-9_-]+)\]')
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        auth_service=None
    ):
        """
        Initialize the account tag service.
        
        Args:
            data_dir: Directory for storing tag data
            auth_service: Optional auth service for user lookups
        """
        self.data_dir = data_dir or self._get_default_data_dir()
        self.auth_service = auth_service
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # File paths
        self.tags_file = os.path.join(self.data_dir, "account_tags.json")
        
        # In-memory cache: {tag_name: {user_id: True, ...}}
        self._tags_cache: Dict[str, Dict[str, bool]] = {}
        
        # Reverse cache: {user_id: Set[tag_name], ...}
        self._user_tags_cache: Dict[str, Set[str]] = {}
        
        # Load existing data
        self._load_tags()
    
    def _get_default_data_dir(self) -> str:
        """Get default data directory for tag storage."""
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
    
    def _load_tags(self) -> None:
        """Load tags from file."""
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, 'r') as f:
                    data = json.load(f)
                    self._tags_cache = data.get('tags', {})
                    
                    # Convert lists to sets for user_tags
                    user_tags_raw = data.get('user_tags', {})
                    self._user_tags_cache = {
                        user_id: set(tags) 
                        for user_id, tags in user_tags_raw.items()
                    }
            except Exception as e:
                print(f"Warning: Could not load account tags: {e}")
    
    def _save_tags(self) -> None:
        """Save tags to file."""
        try:
            # Convert sets to lists for JSON serialization
            user_tags_serializable = {
                user_id: list(tags) 
                for user_id, tags in self._user_tags_cache.items()
            }
            
            data = {
                'tags': self._tags_cache,
                'user_tags': user_tags_serializable,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.tags_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save account tags: {e}")
    
    def parse_account_tags(self, text: str) -> List[str]:
        """
        Parse and extract account tags from text.
        
        Args:
            text: Text to parse (e.g., task description)
            
        Returns:
            List of account tag names (without @ and brackets)
        """
        if not text:
            return []
        
        matches = self.ACCOUNT_TAG_PATTERN.findall(text)
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in matches:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    def parse_account_tags_with_context(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Parse account tags with their positions in the text.
        
        Args:
            text: Text to parse
            
        Returns:
            List of tuples: (tag_name, start_position, end_position)
        """
        if not text:
            return []
        
        matches = []
        for match in self.ACCOUNT_TAG_PATTERN.finditer(text):
            tag_name = match.group(1)
            start_pos = match.start()
            end_pos = match.end()
            matches.append((tag_name, start_pos, end_pos))
        
        return matches
    
    def register_tag_for_user(self, tag_name: str, user_id: str) -> bool:
        """
        Register an account tag for a user.
        
        Args:
            tag_name: Account tag name (without @)
            user_id: User ID to associate with the tag
            
        Returns:
            True if registered, False if already exists
        """
        tag_name = tag_name.lower().strip()
        
        # Initialize tag if not exists
        if tag_name not in self._tags_cache:
            self._tags_cache[tag_name] = {}
        
        # Check if already registered
        if user_id in self._tags_cache[tag_name]:
            return False
        
        # Register the tag
        self._tags_cache[tag_name][user_id] = True
        
        # Update user tags cache
        if user_id not in self._user_tags_cache:
            self._user_tags_cache[user_id] = set()
        self._user_tags_cache[user_id].add(tag_name)
        
        self._save_tags()
        return True
    
    def unregister_tag_for_user(self, tag_name: str, user_id: str) -> bool:
        """
        Unregister an account tag for a user.
        
        Args:
            tag_name: Account tag name (without @)
            user_id: User ID
            
        Returns:
            True if unregistered, False if not found
        """
        tag_name = tag_name.lower().strip()
        
        if tag_name not in self._tags_cache:
            return False
        
        if user_id not in self._tags_cache[tag_name]:
            return False
        
        # Remove from tag cache
        del self._tags_cache[tag_name][user_id]
        
        # Clean up empty tags
        if not self._tags_cache[tag_name]:
            del self._tags_cache[tag_name]
        
        # Update user tags cache
        if user_id in self._user_tags_cache:
            self._user_tags_cache[user_id].discard(tag_name)
            if not self._user_tags_cache[user_id]:
                del self._user_tags_cache[user_id]
        
        self._save_tags()
        return True
    
    def get_users_for_tag(self, tag_name: str) -> List[str]:
        """
        Get all user IDs associated with an account tag.
        
        Args:
            tag_name: Account tag name (without @)
            
        Returns:
            List of user IDs
        """
        tag_name = tag_name.lower().strip()
        
        if tag_name not in self._tags_cache:
            return []
        
        return list(self._tags_cache[tag_name].keys())
    
    def get_tags_for_user(self, user_id: str) -> Set[str]:
        """
        Get all account tags for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Set of account tag names
        """
        return self._user_tags_cache.get(user_id, set()).copy()
    
    def get_user_by_tag(self, tag_name: str) -> Optional[str]:
        """
        Get a user ID for an account tag (returns first if multiple).
        
        Args:
            tag_name: Account tag name (without @)
            
        Returns:
            User ID or None if not found
        """
        users = self.get_users_for_tag(tag_name)
        return users[0] if users else None
    
    def get_user_by_tag_with_email(self, tag_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get user ID and email for an account tag.
        
        Args:
            tag_name: Account tag name (without @)
            
        Returns:
            Tuple of (user_id, email) or (None, None) if not found
        """
        user_id = self.get_user_by_tag(tag_name)
        if not user_id:
            return None, None
        
        # Get email from auth service if available
        email = None
        if self.auth_service:
            user = self.auth_service.get_user(user_id)
            if user:
                email = user.email
        
        return user_id, email
    
    def extract_and_register_tags(
        self,
        text: str,
        user_id: str,
        create_connections: bool = True
    ) -> List[str]:
        """
        Extract account tags from text and register them for a user.
        
        Args:
            text: Text to parse (task description)
            user_id: User ID to associate tags with
            create_connections: Whether to create connections between users
            
        Returns:
            List of registered tag names
        """
        tags = self.parse_account_tags(text)
        registered_tags = []
        
        for tag in tags:
            if self.register_tag_for_user(tag, user_id):
                registered_tags.append(tag)
        
        return registered_tags
    
    def find_tagged_users_in_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Find all users tagged in text.
        
        Args:
            text: Text to search
            
        Returns:
            List of dicts with user_id, email, and tag_name
        """
        tags = self.parse_account_tags(text)
        tagged_users = []
        
        for tag in tags:
            user_id, email = self.get_user_by_tag_with_email(tag)
            if user_id:
                tagged_users.append({
                    'user_id': user_id,
                    'email': email,
                    'tag_name': tag
                })
        
        return tagged_users
    
    def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about account tags.
        
        Returns:
            Dict with tag statistics
        """
        total_tags = len(self._tags_cache)
        total_associations = sum(len(users) for users in self._tags_cache.values())
        
        # Find most popular tags
        tag_counts = [(tag, len(users)) for tag, users in self._tags_cache.items()]
        tag_counts.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'total_unique_tags': total_tags,
            'total_associations': total_associations,
            'top_tags': tag_counts[:10],
            'users_with_tags': len(self._user_tags_cache)
        }
    
    def clear_all_tags(self) -> None:
        """Clear all tag data (for testing)."""
        self._tags_cache = {}
        self._user_tags_cache = {}
        self._save_tags()


# Singleton instance
_account_tag_service: Optional[AccountTagService] = None


def get_account_tag_service() -> AccountTagService:
    """Get the default account tag service instance."""
    global _account_tag_service
    if _account_tag_service is None:
        _account_tag_service = AccountTagService()
    return _account_tag_service


if __name__ == "__main__":
    # Demo usage
    print("Account Tag Service Demo")
    print("=" * 50)
    
    service = AccountTagService()
    
    # Clear any existing data
    service.clear_all_tags()
    
    # Test parsing tags
    test_text = "Task for [@john] and [@jane_doe]. Also [@bob-123] should review."
    tags = service.parse_account_tags(test_text)
    print(f"\n1. Parsed tags from text:")
    print(f"   Text: {test_text}")
    print(f"   Tags: {tags}")
    
    # Register tags for users
    print(f"\n2. Registering tags for users...")
    service.register_tag_for_user("john", "user123")
    service.register_tag_for_user("john", "user456")  # Multiple users can have same tag
    service.register_tag_for_user("jane_doe", "user456")
    service.register_tag_for_user("bob-123", "user789")
    
    # Get users for a tag
    print(f"\n3. Users for 'john' tag: {service.get_users_for_tag('john')}")
    print(f"   Users for 'jane_doe' tag: {service.get_users_for_tag('jane_doe')}")
    
    # Get tags for a user
    print(f"\n4. Tags for user456: {service.get_tags_for_user('user456')}")
    
    # Statistics
    stats = service.get_tag_statistics()
    print(f"\n5. Tag statistics:")
    print(f"   Total unique tags: {stats['total_unique_tags']}")
    print(f"   Total associations: {stats['total_associations']}")
    print(f"   Top tags: {stats['top_tags']}")
    
    # Test finding tagged users
    print(f"\n6. Tagged users in text:")
    tagged = service.find_tagged_users_in_text(test_text)
    for user in tagged:
        print(f"   - {user['tag_name']}: {user['user_id']} ({user['email']})")
    
    print("\n" + "=" * 50)
    print("Demo completed!")