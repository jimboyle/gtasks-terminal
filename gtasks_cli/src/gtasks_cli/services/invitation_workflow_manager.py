"""
Invitation Workflow Manager

This service orchestrates the invitation lifecycle:
1. Create invitation when new account tag is detected
2. Send email notification via QERDS API
3. Process invitation acceptance
4. Create bidirectional connections
5. Handle invitation rejection/cancellation

This service integrates with:
- qerds_api (for email notifications)
- invitation_service (for invitation management)
- task_sharing_service (for connection management)
- database_service (for persistence)
"""

import uuid
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InvitationRequest:
    """Request to create and send an invitation"""
    from_user_id: str
    from_user_email: str
    to_email: str
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    message: Optional[str] = None


@dataclass
class InvitationResult:
    """Result of invitation creation"""
    success: bool
    invitation_id: Optional[str]
    message: str
    invitation_data: Optional[Dict[str, Any]] = None


@dataclass
class AcceptanceResult:
    """Result of processing invitation acceptance"""
    success: bool
    connection_id: Optional[str]
    message: str
    connection_data: Optional[Dict[str, Any]] = None


class InvitationWorkflowManager:
    """
    Manages the complete invitation workflow.
    
    Key responsibilities:
    1. Create invitations with proper metadata
    2. Send email notifications via QERDS API
    3. Process invitation acceptance
    4. Create bidirectional connections
    5. Handle invitation rejection/cancellation
    6. Manage invitation expiration
    """
    
    # Invitation expiration period (30 days)
    EXPIRATION_DAYS = 30
    
    def __init__(self, gtasks_path: Optional[Path] = None):
        """Initialize the workflow manager"""
        self.gtasks_path = gtasks_path or self._detect_gtasks_path()
        logger.info("[InvitationWorkflowManager] Initialized")
    
    def _detect_gtasks_path(self) -> Optional[Path]:
        """Detect GTasks CLI path with multiple fallback locations"""
        import os
        from pathlib import Path
        
        if os.environ.get('GTASKS_CONFIG_DIR'):
            config_path = Path(os.environ['GTASKS_CONFIG_DIR'])
            if config_path.exists():
                logger.info(f"[InvitationWorkflowManager] Using GTASKS_CONFIG_DIR: {config_path}")
                return config_path
        
        possible_paths = [
            Path.home() / '.gtasks',
            Path('./gtasks_cli'),
            Path(__file__).parent.parent.parent / 'gtasks_cli',
            Path.cwd().parent / 'gtasks_cli',
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"[InvitationWorkflowManager] Detected gtasks path: {path}")
                return path
        
        logger.warning("[InvitationWorkflowManager] No gtasks path found")
        return None
    
    def _generate_invitation_id(self) -> str:
        """Generate unique invitation ID"""
        return f"inv_{uuid.uuid4().hex[:12]}"
    
    def _generate_connection_id(self) -> str:
        """Generate unique connection ID"""
        return f"conn_{uuid.uuid4().hex[:12]}"
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _extract_account_name_from_email(self, email: str) -> str:
        """Extract account name from email (abc@gmail.com -> abc)"""
        if '@' in email:
            return email.split('@')[0].lower()
        return email.lower()
    
    def create_invitation(self, request: InvitationRequest) -> InvitationResult:
        """
        Create a new invitation and send notification.
        
        Args:
            request: InvitationRequest with invitation details
            
        Returns:
            InvitationResult with creation status
        """
        # Validate request
        if not request.from_user_id:
            return InvitationResult(
                success=False,
                invitation_id=None,
                message="Missing from_user_id"
            )
        
        if not request.to_email:
            return InvitationResult(
                success=False,
                invitation_id=None,
                message="Missing to_email"
            )
        
        if not self._validate_email(request.to_email):
            return InvitationResult(
                success=False,
                invitation_id=None,
                message="Invalid email format"
            )
        
        # Check for existing invitation
        existing_invitation = self._find_pending_invitation(request.from_user_id, request.to_email)
        if existing_invitation:
            return InvitationResult(
                success=True,
                invitation_id=existing_invitation['id'],
                message="Existing pending invitation found",
                invitation_data=existing_invitation
            )
        
        # Check for existing connection
        to_account_name = self._extract_account_name_from_email(request.to_email)
        if self._are_users_connected(request.from_user_id, to_account_name):
            return InvitationResult(
                success=False,
                invitation_id=None,
                message="Users are already connected"
            )
        
        # Create invitation
        invitation_id = self._generate_invitation_id()
        now = datetime.now()
        expires_at = now + timedelta(days=self.EXPIRATION_DAYS)
        
        invitation_data = {
            'id': invitation_id,
            'from_user_id': request.from_user_id,
            'from_user_email': request.from_user_email,
            'to_email': request.to_email,
            'to_account_name': to_account_name,
            'task_id': request.task_id,
            'task_title': request.task_title,
            'message': request.message,
            'status': 'pending',
            'created_at': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'responded_at': None
        }
        
        # Save invitation to database
        save_result = self._save_invitation(invitation_data)
        if not save_result['success']:
            return InvitationResult(
                success=False,
                invitation_id=None,
                message=f"Failed to save invitation: {save_result.get('error', 'Unknown error')}"
            )
        
        # Send email notification via QERDS API
        email_sent = self._send_invitation_email(request, invitation_id)
        if not email_sent:
            logger.warning(f"[InvitationWorkflowManager] Failed to send email for invitation {invitation_id}")
            # Don't fail the invitation creation, just log the warning
        
        logger.info(f"[InvitationWorkflowManager] Created invitation {invitation_id} from {request.from_user_id} to {request.to_email}")
        
        return InvitationResult(
            success=True,
            invitation_id=invitation_id,
            message="Invitation created successfully",
            invitation_data=invitation_data
        )
    
    def _find_pending_invitation(self, from_user_id: str, to_email: str) -> Optional[Dict[str, Any]]:
        """Find existing pending invitation"""
        if not self.gtasks_path:
            return None
        
        db_file = self.gtasks_path / 'invitations.db'
        if not db_file.exists():
            return None
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT id, from_user_id, to_email, status, created_at, expires_at 
                   FROM invitations 
                   WHERE from_user_id = ? AND to_email = ? AND status = 'pending' 
                   AND expires_at > ?""",
                (from_user_id, to_email, datetime.now().isoformat())
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'from_user_id': row[1],
                    'to_email': row[2],
                    'status': row[3],
                    'created_at': row[4],
                    'expires_at': row[5]
                }
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error finding invitation: {e}")
        
        return None
    
    def _are_users_connected(self, user_id: str, account_name: str) -> bool:
        """Check if users are already connected"""
        if not self.gtasks_path:
            return False
        
        db_file = self.gtasks_path / 'connections.db'
        if not db_file.exists():
            return False
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Check if user_id is connected to account_name
            cursor.execute(
                """SELECT id FROM connections 
                   WHERE (user_id1 = ? OR user_id2 = ?) AND status = 'active'
                   AND (user_id1 LIKE ? || '%' OR user_id2 LIKE ? || '%')""",
                (user_id, user_id, account_name, account_name)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error checking connection: {e}")
        
        return False
    
    def _save_invitation(self, invitation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save invitation to database"""
        if not self.gtasks_path:
            return {'success': False, 'error': 'No database path'}
        
        db_file = self.gtasks_path / 'invitations.db'
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invitations (
                    id TEXT PRIMARY KEY,
                    from_user_id TEXT NOT NULL,
                    from_user_email TEXT NOT NULL,
                    to_email TEXT NOT NULL,
                    to_account_name TEXT,
                    task_id TEXT,
                    task_title TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    expires_at TEXT,
                    responded_at TEXT
                )
            """)
            
            cursor.execute("""
                INSERT INTO invitations 
                (id, from_user_id, from_user_email, to_email, to_account_name, 
                 task_id, task_title, message, status, created_at, expires_at, responded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invitation_data['id'],
                invitation_data['from_user_id'],
                invitation_data['from_user_email'],
                invitation_data['to_email'],
                invitation_data.get('to_account_name'),
                invitation_data.get('task_id'),
                invitation_data.get('task_title'),
                invitation_data.get('message'),
                invitation_data['status'],
                invitation_data['created_at'],
                invitation_data['expires_at'],
                invitation_data.get('responded_at')
            ))
            
            conn.commit()
            conn.close()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error saving invitation: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_invitation_email(self, request: InvitationRequest, invitation_id: str) -> bool:
        """Send invitation email via QERDS API"""
        try:
            # Import QERDS API service
            from .qerds_api import QerdsAPIService
            
            api_service = QerdsAPIService()
            
            # Build email content
            subject = f"Invitation to connect from {request.from_user_email}"
            
            body = f"""
Hello,

{request.from_user_email} has invited you to connect on GTasks.

"""
            
            if request.task_title:
                body += f"They shared a task with you: \"{request.task_title}\"\n\n"
            
            if request.message:
                body += f"Message: {request.message}\n\n"
            
            body += f"""
To accept this invitation:
1. Login to GTasks dashboard or CLI
2. Use your email: {request.to_email}
3. Go to Connections to accept the invitation

This invitation will expire in {self.EXPIRATION_DAYS} days.

Best regards,
GTasks Team
"""
            
            # Send email via QERDS API
            result = api_service.send_email(
                to_email=request.to_email,
                subject=subject,
                body=body
            )
            
            if result.get('success'):
                logger.info(f"[InvitationWorkflowManager] Email sent to {request.to_email} for invitation {invitation_id}")
                return True
            else:
                logger.error(f"[InvitationWorkflowManager] Failed to send email: {result.get('error')}")
                return False
                
        except ImportError:
            logger.warning("[InvitationWorkflowManager] QERDS API not available, skipping email")
            return True  # Don't fail invitation creation
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error sending email: {e}")
            return False
    
    def process_acceptance(self, invitation_id: str, accepting_user_id: str, accepting_user_email: str) -> AcceptanceResult:
        """
        Process invitation acceptance and create connection.
        
        Args:
            invitation_id: ID of the invitation to accept
            accepting_user_id: User ID of the person accepting
            accepting_user_email: Email of the person accepting
            
        Returns:
            AcceptanceResult with creation status
        """
        # Validate invitation exists and is pending
        invitation = self._get_invitation(invitation_id)
        if not invitation:
            return AcceptanceResult(
                success=False,
                connection_id=None,
                message="Invitation not found"
            )
        
        if invitation['status'] != 'pending':
            return AcceptanceResult(
                success=False,
                connection_id=None,
                message=f"Invitation status is '{invitation['status']}', not 'pending'"
            )
        
        # Check expiration
        if invitation['expires_at'] and datetime.fromisoformat(invitation['expires_at']) < datetime.now():
            return AcceptanceResult(
                success=False,
                connection_id=None,
                message="Invitation has expired"
            )
        
        # Verify accepting user matches invitation
        if accepting_user_email != invitation['to_email']:
            return AcceptanceResult(
                success=False,
                connection_id=None,
                message="Email doesn't match invitation recipient"
            )
        
        # Create bidirectional connection
        connection_id = self._create_connection(
            user_id1=invitation['from_user_id'],
            user_id2=accepting_user_id
        )
        
        if not connection_id:
            return AcceptanceResult(
                success=False,
                connection_id=None,
                message="Failed to create connection"
            )
        
        # Update invitation status
        self._update_invitation_status(invitation_id, 'accepted')
        
        # Send acceptance notification email
        self._send_acceptance_notification(invitation)
        
        logger.info(f"[InvitationWorkflowManager] Created connection {connection_id} from invitation {invitation_id}")
        
        connection_data = {
            'id': connection_id,
            'user_id1': invitation['from_user_id'],
            'user_id2': accepting_user_id,
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }
        
        return AcceptanceResult(
            success=True,
            connection_id=connection_id,
            message="Connection created successfully",
            connection_data=connection_data
        )
    
    def _get_invitation(self, invitation_id: str) -> Optional[Dict[str, Any]]:
        """Get invitation by ID"""
        if not self.gtasks_path:
            return None
        
        db_file = self.gtasks_path / 'invitations.db'
        if not db_file.exists():
            return None
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT id, from_user_id, from_user_email, to_email, to_account_name,
                          task_id, task_title, message, status, created_at, expires_at, responded_at
                   FROM invitations WHERE id = ?""",
                (invitation_id,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'from_user_id': row[1],
                    'from_user_email': row[2],
                    'to_email': row[3],
                    'to_account_name': row[4],
                    'task_id': row[5],
                    'task_title': row[6],
                    'message': row[7],
                    'status': row[8],
                    'created_at': row[9],
                    'expires_at': row[10],
                    'responded_at': row[11]
                }
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error getting invitation: {e}")
        
        return None
    
    def _create_connection(self, user_id1: str, user_id2: str) -> Optional[str]:
        """Create bidirectional connection between two users"""
        if not self.gtasks_path:
            return None
        
        db_file = self.gtasks_path / 'connections.db'
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    id TEXT PRIMARY KEY,
                    user_id1 TEXT NOT NULL,
                    user_id2 TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TEXT,
                    UNIQUE(user_id1, user_id2)
                )
            """)
            
            connection_id = self._generate_connection_id()
            now = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO connections (id, user_id1, user_id2, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (connection_id, user_id1, user_id2, 'active', now)
            )
            
            conn.commit()
            conn.close()
            
            return connection_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"[InvitationWorkflowManager] Connection already exists between {user_id1} and {user_id2}")
            return None
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error creating connection: {e}")
            return None
    
    def _update_invitation_status(self, invitation_id: str, status: str):
        """Update invitation status"""
        if not self.gtasks_path:
            return
        
        db_file = self.gtasks_path / 'invitations.db'
        if not db_file.exists():
            return
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE invitations SET status = ?, responded_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), invitation_id)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"[InvitationWorkflowManager] Updated invitation {invitation_id} to status '{status}'")
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error updating invitation: {e}")
    
    def _send_acceptance_notification(self, invitation: Dict[str, Any]):
        """Send email notification when invitation is accepted"""
        try:
            from .qerds_api import QerdsAPIService
            
            api_service = QerdsAPIService()
            
            subject = f"{invitation['to_email']} accepted your invitation"
            
            body = f"""
Hello,

{invitation['to_email']} has accepted your invitation to connect on GTasks.

"""
            
            if invitation.get('task_title'):
                body += f"They can now see the shared task: \"{invitation['task_title']}\"\n\n"
            
            body += """You can now share tasks with each other and track completion.

Best regards,
GTasks Team
"""
            
            api_service.send_email(
                to_email=invitation['from_user_email'],
                subject=subject,
                body=body
            )
            
            logger.info(f"[InvitationWorkflowManager] Sent acceptance notification to {invitation['from_user_email']}")
            
        except Exception as e:
            logger.warning(f"[InvitationWorkflowManager] Failed to send acceptance notification: {e}")
    
    def process_rejection(self, invitation_id: str, rejecting_user_id: str) -> Dict[str, Any]:
        """Process invitation rejection"""
        invitation = self._get_invitation(invitation_id)
        if not invitation:
            return {'success': False, 'message': 'Invitation not found'}
        
        if invitation['status'] != 'pending':
            return {'success': False, 'message': f"Invitation status is '{invitation['status']}'"}
        
        self._update_invitation_status(invitation_id, 'rejected')
        
        logger.info(f"[InvitationWorkflowManager] Invitation {invitation_id} rejected by {rejecting_user_id}")
        
        return {'success': True, 'message': 'Invitation rejected'}
    
    def cancel_invitation(self, invitation_id: str, cancelling_user_id: str) -> Dict[str, Any]:
        """Cancel an invitation (can only be done by sender)"""
        invitation = self._get_invitation(invitation_id)
        if not invitation:
            return {'success': False, 'message': 'Invitation not found'}
        
        if invitation['from_user_id'] != cancelling_user_id:
            return {'success': False, 'message': 'Only sender can cancel invitation'}
        
        self._update_invitation_status(invitation_id, 'cancelled')
        
        logger.info(f"[InvitationWorkflowManager] Invitation {invitation_id} cancelled by {cancelling_user_id}")
        
        return {'success': True, 'message': 'Invitation cancelled'}
    
    def get_pending_invitations_for_user(self, user_email: str) -> List[Dict[str, Any]]:
        """Get all pending invitations for a user email"""
        if not self.gtasks_path:
            return []
        
        db_file = self.gtasks_path / 'invitations.db'
        if not db_file.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT id, from_user_id, from_user_email, to_email, to_account_name,
                          task_id, task_title, message, status, created_at, expires_at
                   FROM invitations 
                   WHERE to_email = ? AND status = 'pending' AND expires_at > ?
                   ORDER BY created_at DESC""",
                (user_email, datetime.now().isoformat())
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            invitations = []
            for row in rows:
                invitations.append({
                    'id': row[0],
                    'from_user_id': row[1],
                    'from_user_email': row[2],
                    'to_email': row[3],
                    'to_account_name': row[4],
                    'task_id': row[5],
                    'task_title': row[6],
                    'message': row[7],
                    'status': row[8],
                    'created_at': row[9],
                    'expires_at': row[10]
                })
            
            return invitations
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error getting invitations: {e}")
        
        return []
    
    def get_sent_invitations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all invitations sent by a user"""
        if not self.gtasks_path:
            return []
        
        db_file = self.gtasks_path / 'invitations.db'
        if not db_file.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT id, from_user_id, from_user_email, to_email, to_account_name,
                          task_id, task_title, message, status, created_at, expires_at, responded_at
                   FROM invitations 
                   WHERE from_user_id = ?
                   ORDER BY created_at DESC""",
                (user_id,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            invitations = []
            for row in rows:
                invitations.append({
                    'id': row[0],
                    'from_user_id': row[1],
                    'from_user_email': row[2],
                    'to_email': row[3],
                    'to_account_name': row[4],
                    'task_id': row[5],
                    'task_title': row[6],
                    'message': row[7],
                    'status': row[8],
                    'created_at': row[9],
                    'expires_at': row[10],
                    'responded_at': row[11]
                })
            
            return invitations
            
        except Exception as e:
            logger.error(f"[InvitationWorkflowManager] Error getting sent invitations: {e}")
        
        return []
