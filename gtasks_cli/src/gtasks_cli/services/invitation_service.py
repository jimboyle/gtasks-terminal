#!/usr/bin/env python3
"""
Invitation Service
Handles the invitation flow for connecting users via @account tags.

Flow:
1. User creates task with [@account] tag
2. System detects untagged account and shows popup
3. User confirms to send invitation
4. System asks for email address
5. System sends invitation email
6. Recipient logs in and sees pending invitations
7. Recipient accepts/rejects invitation
8. Upon acceptance, users are connected
"""

import os
import json
import uuid
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path


class InvitationError(Exception):
    """Exception raised for invitation errors."""
    pass


class InvitationStatus:
    """Invitation status constants."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class InvitationService:
    """
    Service for managing user invitations.
    
    Handles the complete invitation flow:
    - Create invitations
    - Send invitation emails
    - Track invitation status
    - Accept/reject invitations
    - Manage user connections
    """
    
    INVITATION_EXPIRY_DAYS = 7
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        smtp_config: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the invitation service.
        
        Args:
            data_dir: Directory for storing invitation data
            smtp_config: SMTP configuration for sending emails
        """
        self.data_dir = data_dir or self._get_default_data_dir()
        self.smtp_config = smtp_config or self._get_default_smtp_config()
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # File paths
        self.invitations_file = os.path.join(self.data_dir, "invitations.json")
        self.connections_file = os.path.join(self.data_dir, "connections.json")
        
        # In-memory caches
        self._invitations_cache: Dict[str, Dict[str, Any]] = {}
        self._connections_cache: Dict[str, Dict[str, Any]] = {}
        
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
    
    def _get_default_smtp_config(self) -> Dict[str, str]:
        """Get default SMTP configuration from environment."""
        return {
            'smtp_host': os.environ.get('SMTP_HOST', 'localhost'),
            'smtp_port': os.environ.get('SMTP_PORT', '587'),
            'smtp_user': os.environ.get('SMTP_USER', ''),
            'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
            'from_email': os.environ.get('FROM_EMAIL', 'gtasks@localhost'),
            'from_name': os.environ.get('FROM_NAME', 'GTasks')
        }
    
    def _load_data(self) -> None:
        """Load invitations and connections from files."""
        # Load invitations
        if os.path.exists(self.invitations_file):
            try:
                with open(self.invitations_file, 'r') as f:
                    data = json.load(f)
                    self._invitations_cache = data.get('invitations', {})
            except Exception as e:
                print(f"Warning: Could not load invitations: {e}")
        
        # Load connections
        if os.path.exists(self.connections_file):
            try:
                with open(self.connections_file, 'r') as f:
                    data = json.load(f)
                    self._connections_cache = data.get('connections', {})
            except Exception as e:
                print(f"Warning: Could not load connections: {e}")
    
    def _save_data(self) -> None:
        """Save invitations and connections to files."""
        try:
            # Save invitations
            invitations_data = {
                'invitations': self._invitations_cache,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.invitations_file, 'w') as f:
                json.dump(invitations_data, f, indent=2)
            
            # Save connections
            connections_data = {
                'connections': self._connections_cache,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.connections_file, 'w') as f:
                json.dump(connections_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save invitation data: {e}")
    
    def create_invitation(
        self,
        from_user_id: str,
        from_email: str,
        to_email: str,
        task_id: Optional[str] = None,
        task_title: Optional[str] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new invitation.
        
        Args:
            from_user_id: User ID of the inviter
            from_email: Email of the inviter
            to_email: Email of the invitee
            task_id: Optional task ID that prompted the invitation
            task_title: Optional task title
            message: Optional personal message
            
        Returns:
            Dict with invitation details
        """
        invitation_id = str(uuid.uuid4())
        now = datetime.now()
        expiry_date = now + timedelta(days=self.INVITATION_EXPIRY_DAYS)
        
        invitation = {
            'invitation_id': invitation_id,
            'from_user_id': from_user_id,
            'from_email': from_email,
            'to_email': to_email.lower().strip(),
            'task_id': task_id,
            'task_title': task_title,
            'message': message,
            'status': InvitationStatus.PENDING,
            'created_at': now.isoformat(),
            'expires_at': expiry_date.isoformat(),
            'responded_at': None,
            'response_message': None
        }
        
        self._invitations_cache[invitation_id] = invitation
        self._save_data()
        
        return invitation
    
    def send_invitation_email(self, invitation_id: str) -> Tuple[bool, str]:
        """
        Send invitation email to the invitee.
        
        Args:
            invitation_id: ID of the invitation to send
            
        Returns:
            Tuple of (success, message)
        """
        if invitation_id not in self._invitations_cache:
            return False, "Invitation not found"
        
        invitation = self._invitations_cache[invitation_id]
        
        if invitation['status'] != InvitationStatus.PENDING:
            return False, f"Invitation already {invitation['status']}"
        
        try:
            # Build email content
            subject = f"GTasks: You've been invited by {invitation['from_email']}"
            
            body = f"""
Hello,

{invitation['from_email']} has invited you to connect on GTasks.

"""
            
            if invitation.get('task_title'):
                body += f"They want to share a task with you: \"{invitation['task_title']}\"\n\n"
            
            if invitation.get('message'):
                body += f"Personal message: {invitation['message']}\n\n"
            
            body += f"""
To accept this invitation:
1. Log in to GTasks (or create an account if you don't have one)
2. Go to your pending invitations
3. Click "Accept" on this invitation

This invitation will expire on {invitation['expires_at'][:10]}.

Best regards,
The GTasks Team
"""
            
            # Send email (or simulate in test mode)
            if self.smtp_config.get('smtp_host') == 'localhost':
                # Test mode - just log
                print(f"[TEST] Would send email to {invitation['to_email']}")
                print(f"[TEST] Subject: {subject}")
                print(f"[TEST] Body: {body}")
                return True, "Invitation email simulated (SMTP not configured)"
            
            # Real email sending
            msg = MIMEMultipart()
            msg['From'] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
            msg['To'] = invitation['to_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect and send
            server = smtplib.SMTP(
                self.smtp_config['smtp_host'],
                int(self.smtp_config['smtp_port'])
            )
            server.starttls()
            
            if self.smtp_config.get('smtp_user'):
                server.login(
                    self.smtp_config['smtp_user'],
                    self.smtp_config['smtp_password']
                )
            
            server.send_message(msg)
            server.quit()
            
            return True, "Invitation email sent successfully"
            
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def get_pending_invitations_for_user(self, email: str) -> List[Dict[str, Any]]:
        """
        Get all pending invitations for a user's email.
        
        Args:
            email: User's email address
            
        Returns:
            List of invitation dicts
        """
        email = email.lower().strip()
        pending = []
        
        for invitation in self._invitations_cache.values():
            if invitation['to_email'] == email and invitation['status'] == InvitationStatus.PENDING:
                # Check if expired
                expires_at = datetime.fromisoformat(invitation['expires_at'])
                if datetime.now() > expires_at:
                    invitation['status'] = InvitationStatus.EXPIRED
                    self._save_data()
                else:
                    pending.append(invitation)
        
        return pending
    
    def get_sent_invitations(self, from_user_id: str) -> List[Dict[str, Any]]:
        """
        Get all invitations sent by a user.
        
        Args:
            from_user_id: User ID of the inviter
            
        Returns:
            List of invitation dicts
        """
        sent = []
        for invitation in self._invitations_cache.values():
            if invitation['from_user_id'] == from_user_id:
                sent.append(invitation)
        return sent
    
    def accept_invitation(self, invitation_id: str, to_user_id: str) -> Tuple[bool, str]:
        """
        Accept an invitation and create connection between users.
        
        Args:
            invitation_id: ID of the invitation
            to_user_id: User ID of the invitee (must match email)
            
        Returns:
            Tuple of (success, message)
        """
        if invitation_id not in self._invitations_cache:
            return False, "Invitation not found"
        
        invitation = self._invitations_cache[invitation_id]
        
        if invitation['status'] != InvitationStatus.PENDING:
            return False, f"Invitation already {invitation['status']}"
        
        # Check expiry
        expires_at = datetime.fromisoformat(invitation['expires_at'])
        if datetime.now() > expires_at:
            invitation['status'] = InvitationStatus.EXPIRED
            self._save_data()
            return False, "Invitation has expired"
        
        # Accept the invitation
        invitation['status'] = InvitationStatus.ACCEPTED
        invitation['responded_at'] = datetime.now().isoformat()
        invitation['to_user_id'] = to_user_id
        
        # Create connection between users
        connection_id = self.create_connection(
            user_id_1=invitation['from_user_id'],
            user_id_2=to_user_id,
            task_id=invitation.get('task_id'),
            task_title=invitation.get('task_title')
        )
        
        invitation['connection_id'] = connection_id
        self._save_data()
        
        return True, f"Invitation accepted! You are now connected with {invitation['from_email']}"
    
    def reject_invitation(self, invitation_id: str) -> Tuple[bool, str]:
        """
        Reject an invitation.
        
        Args:
            invitation_id: ID of the invitation
            
        Returns:
            Tuple of (success, message)
        """
        if invitation_id not in self._invitations_cache:
            return False, "Invitation not found"
        
        invitation = self._invitations_cache[invitation_id]
        
        if invitation['status'] != InvitationStatus.PENDING:
            return False, f"Invitation already {invitation['status']}"
        
        # Reject the invitation
        invitation['status'] = InvitationStatus.REJECTED
        invitation['responded_at'] = datetime.now().isoformat()
        self._save_data()
        
        return True, "Invitation rejected"
    
    def create_connection(
        self,
        user_id_1: str,
        user_id_2: str,
        task_id: Optional[str] = None,
        task_title: Optional[str] = None
    ) -> str:
        """
        Create a connection between two users.
        
        Args:
            user_id_1: First user ID
            user_id_2: Second user ID
            task_id: Optional task that prompted the connection
            task_title: Optional task title
            
        Returns:
            Connection ID
        """
        connection_id = str(uuid.uuid4())
        
        # Ensure consistent ordering of user IDs
        users = sorted([user_id_1, user_id_2])
        
        connection = {
            'connection_id': connection_id,
            'user_id_1': users[0],
            'user_id_2': users[1],
            'task_id': task_id,
            'task_title': task_title,
            'created_at': datetime.now().isoformat()
        }
        
        self._connections_cache[connection_id] = connection
        self._save_data()
        
        return connection_id
    
    def get_connections_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all connections for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of connection dicts
        """
        connections = []
        for connection in self._connections_cache.values():
            if connection['user_id_1'] == user_id or connection['user_id_2'] == user_id:
                connections.append(connection)
        return connections
    
    def is_connected(self, user_id_1: str, user_id_2: str) -> bool:
        """
        Check if two users are connected.
        
        Args:
            user_id_1: First user ID
            user_id_2: Second user ID
            
        Returns:
            True if users are connected
        """
        users = sorted([user_id_1, user_id_2])
        for connection in self._connections_cache.values():
            if connection['user_id_1'] == users[0] and connection['user_id_2'] == users[1]:
                return True
        return False
    
    def get_invitation_by_id(self, invitation_id: str) -> Optional[Dict[str, Any]]:
        """Get invitation by ID."""
        return self._invitations_cache.get(invitation_id)
    
    def cancel_invitation(self, invitation_id: str) -> Tuple[bool, str]:
        """
        Cancel a pending invitation.
        
        Args:
            invitation_id: ID of the invitation
            
        Returns:
            Tuple of (success, message)
        """
        if invitation_id not in self._invitations_cache:
            return False, "Invitation not found"
        
        invitation = self._invitations_cache[invitation_id]
        
        if invitation['status'] != InvitationStatus.PENDING:
            return False, f"Cannot cancel invitation with status: {invitation['status']}"
        
        # Remove the invitation
        del self._invitations_cache[invitation_id]
        self._save_data()
        
        return True, "Invitation cancelled"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get invitation statistics."""
        stats = {
            'total_invitations': len(self._invitations_cache),
            'pending': 0,
            'accepted': 0,
            'rejected': 0,
            'expired': 0,
            'total_connections': len(self._connections_cache)
        }
        
        for invitation in self._invitations_cache.values():
            stats[invitation['status']] += 1
        
        return stats


# Singleton instance
_invitation_service: Optional[InvitationService] = None


def get_invitation_service() -> InvitationService:
    """Get the default invitation service instance."""
    global _invitation_service
    if _invitation_service is None:
        _invitation_service = InvitationService()
    return _invitation_service


if __name__ == "__main__":
    # Demo usage
    print("Invitation Service Demo")
    print("=" * 50)
    
    service = InvitationService()
    
    # Create an invitation
    print("\n1. Creating invitation...")
    invitation = service.create_invitation(
        from_user_id="user123",
        from_email="john@example.com",
        to_email="jane@example.com",
        task_id="task456",
        task_title="Review document",
        message="Please help me review this document"
    )
    print(f"   Invitation ID: {invitation['invitation_id']}")
    print(f"   From: {invitation['from_email']}")
    print(f"   To: {invitation['to_email']}")
    
    # Send invitation email (simulated)
    print("\n2. Sending invitation email...")
    success, message = service.send_invitation_email(invitation['invitation_id'])
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    
    # Check pending invitations for user
    print("\n3. Checking pending invitations for jane@example.com...")
    pending = service.get_pending_invitations_for_user("jane@example.com")
    print(f"   Pending: {len(pending)}")
    
    # Get statistics
    print("\n4. Invitation statistics:")
    stats = service.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Accept invitation
    print("\n5. Jane accepting invitation...")
    success, message = service.accept_invitation(invitation['invitation_id'], "jane456")
    print(f"   Success: {success}")
    print(f"   Message: {message}")
    
    # Check if users are connected
    print("\n6. Checking connection between users...")
    connected = service.is_connected("user123", "jane456")
    print(f"   Connected: {connected}")
    
    # Get connections for user
    print("\n7. Connections for user123:")
    connections = service.get_connections_for_user("user123")
    print(f"   Connections: {len(connections)}")
    for conn in connections:
        print(f"   - {conn['connection_id']}: {conn['user_id_1']} <-> {conn['user_id_2']}")
    
    print("\n" + "=" * 50)
    print("Demo completed!")
