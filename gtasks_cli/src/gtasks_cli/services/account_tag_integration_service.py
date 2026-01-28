"""
Account Tag Integration Service

This service orchestrates the detection of new [@account] tags in tasks
and triggers the invitation workflow when new account tags are detected.

This is the integration layer that connects:
- account_tag_service (for parsing tags)
- invitation_service (for creating invitations)
- database_service (for persistence)
- qerds_api (for email notifications)
"""

import re
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DetectedAccountTag:
    """Represents a detected account tag from task analysis"""
    account_name: str
    task_id: str
    task_title: str
    detected_at: str
    source: str = "task_description"  # task_description, tags_field, notes


@dataclass
class PendingInvitationInfo:
    """Information about pending invitation for an account"""
    account_name: str
    invitation_id: Optional[str]
    status: str  # pending, connected, no_user
    from_user_id: str
    task_id: Optional[str]
    created_at: Optional[str]


class AccountTagIntegrationService:
    """
    Orchestrates account tag detection and invitation workflow.
    
    Key responsibilities:
    1. Scan tasks for new [@account] tags
    2. Check connection status for detected accounts
    3. Trigger invitation workflow for unconnected accounts
    4. Maintain cache of detected account tags
    5. Provide status information for UI/API
    """
    
    def __init__(self, gtasks_path: Optional[Path] = None):
        """Initialize the integration service"""
        self.gtasks_path = gtasks_path or self._detect_gtasks_path()
        self._account_tags_cache: Dict[str, DetectedAccountTag] = {}
        self._connection_status_cache: Dict[str, PendingInvitationInfo] = {}
        logger.info("[AccountTagIntegrationService] Initialized")
    
    def _detect_gtasks_path(self) -> Optional[Path]:
        """Detect GTasks CLI path with multiple fallback locations"""
        import os
        from pathlib import Path
        
        # Check GTASKS_CONFIG_DIR environment variable first
        if os.environ.get('GTASKS_CONFIG_DIR'):
            config_path = Path(os.environ['GTASKS_CONFIG_DIR'])
            if config_path.exists():
                logger.info(f"[AccountTagIntegrationService] Using GTASKS_CONFIG_DIR: {config_path}")
                return config_path
        
        # Check multiple possible locations
        possible_paths = [
            Path.home() / '.gtasks',
            Path('./gtasks_cli'),
            Path(__file__).parent.parent.parent / 'gtasks_cli',
            Path.cwd().parent / 'gtasks_cli',
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"[AccountTagIntegrationService] Detected gtasks path: {path}")
                return path
        
        logger.warning("[AccountTagIntegrationService] No gtasks path found")
        return None
    
    def extract_account_tags_from_text(self, text: str) -> List[str]:
        """
        Extract account tags from text in [@account] format.
        
        Args:
            text: Text to search for account tags
            
        Returns:
            List of account names (without @ symbol)
        """
        if not text:
            return []
        
        # Match [@account] pattern - account name can include letters, numbers, underscores, hyphens
        account_tags = re.findall(r'@\[([^\]]+)\]', text, re.IGNORECASE)
        
        # Also support direct @account format
        direct_accounts = re.findall(r'@(\w+)', text, re.IGNORECASE)
        
        # Combine and deduplicate
        all_accounts = set()
        for account in account_tags + direct_accounts:
            account = account.strip()
            if account and len(account) >= 2:  # Minimum 2 characters
                all_accounts.add(account.lower())
        
        return list(all_accounts)
    
    def detect_account_tags_from_tasks(self, tasks: List[Dict[str, Any]]) -> List[DetectedAccountTag]:
        """
        Scan a list of tasks for account tags.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            List of DetectedAccountTag objects
        """
        detected_tags: List[DetectedAccountTag] = []
        seen_accounts: Set[str] = set()
        
        for task in tasks:
            task_id = task.get('id', 'unknown')
            title = task.get('title', '')
            description = task.get('description', '')
            notes = task.get('notes', '')
            structured_tags = task.get('tags', [])
            
            # Combine all text sources
            full_text = f"{title} {description} {notes}"
            
            # Extract account tags
            account_names = self.extract_account_tags_from_text(full_text)
            
            # Also check structured tags field for account tags
            if isinstance(structured_tags, str):
                structured_tags = structured_tags.split(',')
            
            for tag in structured_tags:
                tag = tag.strip()
                if tag.startswith('@') and len(tag) > 1:
                    account_name = tag[1:].lower()
                    if len(account_name) >= 2:
                        account_names.append(account_name)
            
            # Process each detected account tag
            for account_name in account_names:
                if account_name in seen_accounts:
                    continue
                
                seen_accounts.add(account_name)
                
                # Create detection record
                detected_tag = DetectedAccountTag(
                    account_name=account_name,
                    task_id=task_id,
                    task_title=title[:100] if title else 'Untitled Task',  # Truncate long titles
                    detected_at=datetime.now().isoformat()
                )
                
                detected_tags.append(detected_tag)
                self._account_tags_cache[account_name] = detected_tag
        
        logger.info(f"[AccountTagIntegrationService] Detected {len(detected_tags)} unique account tags from {len(tasks)} tasks")
        return detected_tags
    
    def get_connection_status(self, account_name: str, db_path: Optional[Path] = None) -> PendingInvitationInfo:
        """
        Check the connection status for an account.
        
        Args:
            account_name: Account name to check
            db_path: Optional path to database
            
        Returns:
            PendingInvitationInfo with connection status
        """
        # Check cache first
        cache_key = account_name.lower()
        if cache_key in self._connection_status_cache:
            return self._connection_status_cache[cache_key]
        
        # Try to find user in database
        user_id = self._find_user_by_account_name(account_name, db_path)
        
        if not user_id:
            # No user registered for this account
            info = PendingInvitationInfo(
                account_name=account_name,
                invitation_id=None,
                status="no_user",
                from_user_id="",
                task_id=None,
                created_at=None
            )
            self._connection_status_cache[cache_key] = info
            return info
        
        # Check for existing connection or pending invitation
        connection_status = self._check_connection_or_invitation(user_id, db_path)
        
        info = PendingInvitationInfo(
            account_name=account_name,
            invitation_id=connection_status.get('invitation_id'),
            status=connection_status.get('status', 'unknown'),
            from_user_id=connection_status.get('from_user_id', ''),
            task_id=connection_status.get('task_id'),
            created_at=connection_status.get('created_at')
        )
        
        self._connection_status_cache[cache_key] = info
        return info
    
    def _find_user_by_account_name(self, account_name: str, db_path: Optional[Path] = None) -> Optional[str]:
        """
        Find user ID by account name in the database.
        
        Args:
            account_name: Account name to search for
            db_path: Optional path to database
            
        Returns:
            User ID if found, None otherwise
        """
        if not db_path and not self.gtasks_path:
            return None
        
        db_file = db_path or self.gtasks_path
        db_file = db_file / 'users.db'
        
        if not db_file.exists():
            return None
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Search for user by account name (user_id is derived from email prefix)
            # Account name "abc" could correspond to user "abc12345" from abc@gmail.com
            cursor.execute(
                "SELECT id FROM users WHERE id LIKE ? || '%'",
                (account_name.lower(),)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            
        except Exception as e:
            logger.error(f"[AccountTagIntegrationService] Error finding user: {e}")
        
        return None
    
    def _check_connection_or_invitation(self, user_id: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Check if there's an existing connection or pending invitation.
        
        Args:
            user_id: User ID to check
            db_path: Optional path to database
            
        Returns:
            Dictionary with connection/invitation status
        """
        if not db_path and not self.gtasks_path:
            return {'status': 'unknown'}
        
        db_file = db_path or self.gtasks_path
        db_file = db_file / 'connections.db'
        
        if not db_file.exists():
            return {'status': 'no_connection'}
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Check for existing connection
            cursor.execute(
                "SELECT id, created_at FROM connections WHERE (user_id1 = ? OR user_id2 = ?) AND status = 'active'",
                (user_id, user_id)
            )
            
            connection = cursor.fetchone()
            if connection:
                conn.close()
                return {
                    'status': 'connected',
                    'connection_id': connection[0],
                    'created_at': connection[1]
                }
            
            # Check for pending invitation
            cursor.execute(
                "SELECT id, from_user_id, created_at FROM invitations WHERE to_user_id = ? AND status = 'pending' AND expires_at > ?",
                (user_id, datetime.now().isoformat())
            )
            
            invitation = cursor.fetchone()
            if invitation:
                conn.close()
                return {
                    'status': 'pending',
                    'invitation_id': invitation[0],
                    'from_user_id': invitation[1],
                    'created_at': invitation[2]
                }
            
            conn.close()
            
        except Exception as e:
            logger.error(f"[AccountTagIntegrationService] Error checking connection: {e}")
        
        return {'status': 'no_connection'}
    
    def get_accounts_needing_invitation(self, detected_tags: List[DetectedAccountTag]) -> List[Tuple[DetectedAccountTag, PendingInvitationInfo]]:
        """
        Filter account tags that need invitations sent.
        
        Args:
            detected_tags: List of detected account tags
            
        Returns:
            List of tuples (detected_tag, invitation_info) for accounts needing invitation
        """
        accounts_needing_action: List[Tuple[DetectedAccountTag, PendingInvitationInfo]] = []
        
        for detected_tag in detected_tags:
            invitation_info = self.get_connection_status(detected_tag.account_name)
            
            # Need invitation if:
            # 1. No user registered for this account
            # 2. No pending invitation
            # 3. Not already connected
            
            if invitation_info.status == "no_user":
                accounts_needing_action.append((detected_tag, invitation_info))
            elif invitation_info.status == "no_connection":
                # Could send invitation to potential user
                accounts_needing_action.append((detected_tag, invitation_info))
        
        logger.info(f"[AccountTagIntegrationService] {len(accounts_needing_action)} accounts need attention out of {len(detected_tags)} detected")
        return accounts_needing_action
    
    def scan_all_accounts(self, accounts: List[str] = None) -> Dict[str, PendingInvitationInfo]:
        """
        Scan all accounts and return their connection status.
        
        Args:
            accounts: Optional list of accounts to check (default: all cached)
            
        Returns:
            Dictionary mapping account_name to PendingInvitationInfo
        """
        accounts_to_check = accounts or list(self._account_tags_cache.keys())
        
        status_dict: Dict[str, PendingInvitationInfo] = {}
        for account_name in accounts_to_check:
            status = self.get_connection_status(account_name)
            status_dict[account_name] = status
        
        logger.info(f"[AccountTagIntegrationService] Scanned {len(status_dict)} accounts")
        return status_dict
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about account tags and connections.
        
        Returns:
            Dictionary with statistics
        """
        total_cached = len(self._account_tags_cache)
        
        # Count by status
        status_counts = {
            'connected': 0,
            'pending': 0,
            'no_user': 0,
            'no_connection': 0,
            'unknown': 0
        }
        
        for account_name in self._account_tags_cache:
            status = self.get_connection_status(account_name)
            status_counts[status.status] = status_counts.get(status.status, 0) + 1
        
        return {
            'total_accounts_detected': total_cached,
            'accounts_connected': status_counts.get('connected', 0),
            'accounts_pending': status_counts.get('pending', 0),
            'accounts_no_user': status_counts.get('no_user', 0),
            'accounts_no_connection': status_counts.get('no_connection', 0),
            'accounts_unknown': status_counts.get('unknown', 0),
            'accounts_needing_action': status_counts.get('no_user', 0) + status_counts.get('no_connection', 0)
        }
    
    def clear_cache(self):
        """Clear the internal caches"""
        self._account_tags_cache.clear()
        self._connection_status_cache.clear()
        logger.info("[AccountTagIntegrationService] Cache cleared")
    
    def refresh_from_database(self, db_path: Optional[Path] = None):
        """
        Refresh cached data from database.
        
        Args:
            db_path: Optional path to database
        """
        # Reload account tags cache from database if needed
        # This would query the account_tags_cache table if it exists
        
        # Clear and rebuild connection status cache
        self._connection_status_cache.clear()
        
        # Re-scan all cached accounts
        if self._account_tags_cache:
            self.scan_all_accounts()
        
        logger.info("[AccountTagIntegrationService] Cache refreshed from database")
