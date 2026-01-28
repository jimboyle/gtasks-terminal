#!/usr/bin/env python3
"""
User ID Generator Utility
Generates unique user IDs from email addresses.
Logic: abc@gmail.com -> abc12345 (email prefix + unique suffix)
"""

import hashlib
import secrets
import re
from typing import Optional


class UserIDGenerator:
    """Generates unique user IDs from email addresses."""
    
    def __init__(self, salt: str = "gtasks_user_id"):
        """
        Initialize the generator with an optional salt for hashing.
        
        Args:
            salt: Salt string for generating unique suffixes
        """
        self.salt = salt
        self._used_ids: set[str] = set()
    
    def extract_email_prefix(self, email: str) -> str:
        """
        Extract the prefix from an email address.
        
        Args:
            email: Full email address (e.g., "abc@gmail.com")
            
        Returns:
            Email prefix (e.g., "abc")
            
        Raises:
            ValueError: If email format is invalid
        """
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email format: {email}")
        
        # Extract prefix (everything before @)
        prefix = email.split('@')[0].lower()
        
        # Sanitize prefix (keep only alphanumeric and underscores)
        sanitized = re.sub(r'[^a-z0-9_]', '', prefix)
        
        if not sanitized:
            raise ValueError(f"Email prefix is empty after sanitization: {email}")
        
        return sanitized
    
    def generate_suffix(self, email: str, length: int = 5) -> str:
        """
        Generate a unique suffix for the user ID.
        
        Args:
            email: Full email address
            length: Length of the suffix (default 5)
            
        Returns:
            Unique suffix string
        """
        # Generate a hash-based suffix for uniqueness
        data = f"{email}{self.salt}{secrets.token_hex(8)}"
        hash_value = hashlib.sha256(data.encode()).hexdigest()
        
        # Take first 'length' characters of the hash, convert to alphanumeric
        suffix = re.sub(r'[^a-z0-9]', '', hash_value.lower())[:length]
        
        # Ensure suffix is not empty and doesn't start with digit
        while len(suffix) < length or suffix[0].isdigit():
            data = f"{email}{self.salt}{secrets.token_hex(4)}"
            hash_value = hashlib.sha256(data.encode()).hexdigest()
            suffix = re.sub(r'[^a-z0-9]', '', hash_value.lower())[:length]
        
        return suffix
    
    def generate_user_id(self, email: str, check_collision: bool = True) -> str:
        """
        Generate a unique user ID from an email address.
        
        Args:
            email: Full email address (e.g., "abc@gmail.com")
            check_collision: Whether to check for ID collisions
            
        Returns:
            Unique user ID (e.g., "abc12345")
            
        Raises:
            ValueError: If email format is invalid
        """
        prefix = self.extract_email_prefix(email)
        suffix = self.generate_suffix(email)
        
        user_id = f"{prefix}{suffix}"
        
        # Check for collisions if required
        if check_collision:
            attempts = 0
            max_attempts = 10
            
            while user_id in self._used_ids and attempts < max_attempts:
                suffix = self.generate_suffix(email)
                user_id = f"{prefix}{suffix}"
                attempts += 1
            
            if user_id in self._used_ids:
                raise RuntimeError(f"Failed to generate unique user ID for {email}")
            
            self._used_ids.add(user_id)
        
        return user_id
    
    def is_valid_user_id(self, user_id: str) -> bool:
        """
        Validate a user ID format.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # User ID should be alphanumeric, start with letter, 6+ characters
        pattern = r'^[a-zA-Z][a-zA-Z0-9]{5,}$'
        return bool(re.match(pattern, user_id))
    
    def extract_prefix(self, user_id: str) -> Optional[str]:
        """
        Extract the prefix (email part) from a user ID.
        
        Args:
            user_id: User ID (e.g., "abc12345")
            
        Returns:
            Email prefix (e.g., "abc") or None if invalid
        """
        if not self.is_valid_user_id(user_id):
            return None
        
        # Extract prefix (everything before the numeric suffix)
        # The suffix is typically the last 5 characters that are mostly numeric
        match = re.match(r'^([a-zA-Z][a-zA-Z0-9]*)', user_id)
        if match:
            return match.group(1)
        
        return None
    
    def reset(self) -> None:
        """Reset the collision tracking cache."""
        self._used_ids.clear()


# Singleton instance for common usage
_default_generator: Optional[UserIDGenerator] = None


def get_user_id_generator() -> UserIDGenerator:
    """Get the default UserIDGenerator instance."""
    global _default_generator
    if _default_generator is None:
        _default_generator = UserIDGenerator()
    return _default_generator


def generate_user_id(email: str) -> str:
    """
    Convenience function to generate a user ID from an email.
    
    Args:
        email: Full email address
        
    Returns:
        Unique user ID
    """
    return get_user_id_generator().generate_user_id(email)


def extract_email_prefix(email: str) -> str:
    """
    Convenience function to extract email prefix.
    
    Args:
        email: Full email address
        
    Returns:
        Email prefix
    """
    return get_user_id_generator().extract_email_prefix(email)


if __name__ == "__main__":
    # Demo usage
    generator = UserIDGenerator()
    
    test_emails = [
        "abc@gmail.com",
        "john.doe@example.org",
        "user123@company.net",
        "test_email@test.com",
    ]
    
    print("User ID Generator Demo")
    print("=" * 50)
    
    for email in test_emails:
        try:
            user_id = generator.generate_user_id(email)
            prefix = generator.extract_email_prefix(email)
            print(f"Email: {email}")
            print(f"  Prefix: {prefix}")
            print(f"  User ID: {user_id}")
            print(f"  Valid: {generator.is_valid_user_id(user_id)}")
            print()
        except ValueError as e:
            print(f"Email: {email}")
            print(f"  Error: {e}")
            print()
    
    # Test collision handling
    print("Collision Test:")
    print("-" * 50)
    generator2 = UserIDGenerator()
    email = "test@example.com"
    
    ids = set()
    for i in range(100):
        user_id = generator2.generate_user_id(email)
        if user_id in ids:
            print(f"Collision detected at iteration {i}!")
            break
        ids.add(user_id)
    else:
        print(f"Generated 100 unique IDs without collision")
        print(f"Last ID: {list(ids)[-1]}")
