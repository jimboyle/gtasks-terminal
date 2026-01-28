#!/usr/bin/env python3
"""
Comprehensive Test Suite for User Authentication and Account Tags System

This test suite validates:
1. User ID generation from email addresses
2. Authentication service (login, logout, session management)
3. Account tag parsing and management
4. Invitation workflow (create, send, accept, reject)
5. Task sharing and completion tracking
6. Integration tests for the complete workflow
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import unittest

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestUserIDGenerator(unittest.TestCase):
    """Test user ID generation from email addresses"""
    
    def test_basic_email(self):
        """Test basic email to user ID conversion"""
        from gtasks_cli.utils.user_id_generator import generate_user_id
        
        user_id = generate_user_id("abc@gmail.com")
        self.assertTrue(user_id.startswith("abc"))
        self.assertGreater(len(user_id), 3)
        print(f"✓ Basic email: abc@gmail.com → {user_id}")
    
    def test_email_with_dots(self):
        """Test email with dots in username"""
        from gtasks_cli.utils.user_id_generator import generate_user_id
        
        user_id = generate_user_id("john.doe@gmail.com")
        self.assertTrue(user_id.startswith("johndoe") or user_id.startswith("john"))
        print(f"✓ Email with dots: john.doe@gmail.com → {user_id}")
    
    def test_email_with_plus(self):
        """Test email with plus addressing"""
        from gtasks_cli.utils.user_id_generator import generate_user_id
        
        user_id = generate_user_id("user+tag@example.com")
        self.assertTrue(user_id.startswith("user"))
        print(f"✓ Email with plus: user+tag@example.com → {user_id}")
    
    def test_different_domains(self):
        """Test different email domains"""
        from gtasks_cli.utils.user_id_generator import generate_user_id
        
        domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com"]
        for domain in domains:
            user_id = generate_user_id(f"test@{domain}")
            self.assertTrue(user_id.startswith("test"))
            print(f"✓ Different domain: test@{domain} → {user_id}")
    
    def test_unique_ids(self):
        """Test that multiple calls generate unique IDs"""
        from gtasks_cli.utils.user_id_generator import generate_user_id
        
        user_ids = set()
        for _ in range(10):
            user_id = generate_user_id("test@gmail.com")
            user_ids.add(user_id)
        
        # Should have at least some unique IDs
        self.assertGreater(len(user_ids), 1)
        print(f"✓ Generated {len(user_ids)} unique IDs from 10 calls")


class TestAuthenticationService(unittest.TestCase):
    """Test authentication service functionality"""
    
    def setUp(self):
        """Set up test environment"""
        from gtasks_cli.services.auth_service import AuthService
        self.auth_service = AuthService()
    
    def test_login_with_dummy(self):
        """Test dummy login for testing"""
        result = self.auth_service.login(email="test@example.com", api_key="dummy", is_dummy=True)
        
        self.assertTrue(result['success'])
        self.assertIn('user', result)
        self.assertEqual(result['user']['email'], "test@example.com")
        self.assertTrue(result['user']['is_dummy'])
        print(f"✓ Dummy login successful: {result['user']['user_id']}")
    
    def test_login_creates_user(self):
        """Test that login creates a new user"""
        email = f"newuser_{datetime.now().timestamp()}@example.com"
        result = self.auth_service.login(email=email, api_key="dummy", is_dummy=True)
        
        self.assertTrue(result['success'])
        self.assertIn('user', result)
        self.assertEqual(result['user']['email'], email)
        
        # Verify user exists
        user = self.auth_service.get_user(result['user']['user_id'])
        self.assertIsNotNone(user)
        print(f"✓ User created and retrieved: {result['user']['user_id']}")
    
    def test_logout(self):
        """Test user logout"""
        # First login to create a user and session
        result = self.auth_service.login(email="logout_test@example.com", api_key="dummy", is_dummy=True)
        user_id = result['user']['user_id']
        
        # Create a session
        session = self.auth_service.create_session(user_id)
        
        # Then logout with session_id (not user_id)
        logout_result = self.auth_service.logout(session.session_id)
        self.assertTrue(logout_result[0])  # tuple: (success, message)
        print("✓ Logout successful")

    def test_get_all_users(self):
        """Test listing all users"""
        # Create a few users
        for i in range(3):
            self.auth_service.login(email=f"listuser{i}@example.com", api_key="dummy", is_dummy=True)
        
        users = self.auth_service.get_all_users()
        self.assertGreaterEqual(len(users), 3)
        print(f"✓ Listed {len(users)} users")
    
    def test_get_user(self):
        """Test getting user by ID"""
        result = self.auth_service.login(email="getuser_test@example.com", api_key="dummy", is_dummy=True)
        user_id = result['user']['user_id']
        
        user = self.auth_service.get_user(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "getuser_test@example.com")
        print(f"✓ User retrieved by ID: {user_id}")


class TestAccountTagService(unittest.TestCase):
    """Test account tag parsing and management"""
    
    def setUp(self):
        """Set up test environment"""
        from gtasks_cli.services.account_tag_service import AccountTagService
        from gtasks_cli.services.auth_service import AuthService
        
        self.tag_service = AccountTagService()
        self.auth_service = AuthService()
    
    def test_parse_single_account_tag(self):
        """Test parsing a single account tag"""
        tags = self.tag_service.parse_account_tags("Task for [@john]")
        
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0], "john")
        print("✓ Single account tag parsed: [@john] → john")
    
    def test_parse_multiple_account_tags(self):
        """Test parsing multiple account tags"""
        tags = self.tag_service.parse_account_tags("Task for [@john] and [@jane_doe]")
        
        self.assertEqual(len(tags), 2)
        self.assertIn("john", tags)
        self.assertIn("jane_doe", tags)
        print(f"✓ Multiple tags parsed: [@john] and [@jane_doe] → {tags}")
    
    def test_parse_no_account_tags(self):
        """Test parsing text with no account tags"""
        tags = self.tag_service.parse_account_tags("Regular task without tags")
        
        self.assertEqual(len(tags), 0)
        print("✓ No account tags in regular text")
    
    def test_parse_mixed_tags(self):
        """Test parsing mixed account tags and regular tags"""
        tags = self.tag_service.parse_account_tags("Task for [@user1] with #regular_tag")
        
        # Should only extract account tags (@...), not regular tags (#)
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0], "user1")
        print("✓ Mixed tags parsed correctly: [@user1] with #regular_tag → [user1]")
    
    def test_register_and_get_user_tags(self):
        """Test registering and retrieving user account tags"""
        # First create a user
        result = self.auth_service.login(email="tagtest@example.com", api_key="dummy", is_dummy=True)
        user_id = result['user']['user_id']
        
        # Register tags using register_tag_for_user (one at a time)
        self.tag_service.register_tag_for_user("alice", user_id)
        self.tag_service.register_tag_for_user("bob", user_id)
        self.tag_service.register_tag_for_user("charlie", user_id)
        
        # Retrieve tags using get_tags_for_user
        tags = self.tag_service.get_tags_for_user(user_id)
        
        self.assertEqual(len(tags), 3)
        self.assertIn("alice", tags)
        self.assertIn("bob", tags)
        self.assertIn("charlie", tags)
        print(f"✓ User tags registered and retrieved: {tags}")


class TestInvitationService(unittest.TestCase):
    """Test invitation workflow"""
    
    def setUp(self):
        """Set up test environment"""
        from gtasks_cli.services.invitation_service import InvitationService
        from gtasks_cli.services.auth_service import AuthService
        
        self.invitation_service = InvitationService()
        self.auth_service = AuthService()
    
    def test_create_invitation(self):
        """Test creating an invitation"""
        # Create users
        sender = self.auth_service.login(email="sender@example.com", api_key="dummy", is_dummy=True)
        sender_id = sender['user']['user_id']
        
        result = self.invitation_service.create_invitation(
            from_user_id=sender_id,
            from_email="sender@example.com",
            to_email="receiver@example.com",
            task_id="task123",
            message="Please help with this task"
        )
        
        # create_invitation returns dict directly (not tuple)
        self.assertIn('invitation_id', result)
        self.assertIn('from_user_id', result)
        print(f"✓ Invitation created: {result['invitation_id']}")
    
    def test_send_invitation_email(self):
        """Test sending invitation email"""
        # Create invitation first
        sender = self.auth_service.login(email="sender2@example.com", api_key="dummy", is_dummy=True)
        sender_id = sender['user']['user_id']
        
        result = self.invitation_service.create_invitation(
            from_user_id=sender_id,
            from_email="sender2@example.com",
            to_email="receiver2@example.com",
            task_id="task456"
        )
        
        # Send email - returns tuple (success, message)
        email_result = self.invitation_service.send_invitation_email(result['invitation_id'])
        self.assertTrue(email_result[0])  # tuple: (success, message)
        print("✓ Invitation email sent")
    
    def test_accept_invitation(self):
        """Test accepting an invitation"""
        # Create users
        sender = self.auth_service.login(email="sender3@example.com", api_key="dummy", is_dummy=True)
        sender_id = sender['user']['user_id']
        
        receiver = self.auth_service.login(email="receiver3@example.com", api_key="dummy", is_dummy=True)
        receiver_id = receiver['user']['user_id']
        
        # Create invitation
        result = self.invitation_service.create_invitation(
            from_user_id=sender_id,
            from_email="sender3@example.com",
            to_email="receiver3@example.com",
            task_id="task789"
        )
        
        # Accept invitation - returns tuple (success, message)
        accept_result = self.invitation_service.accept_invitation(result['invitation_id'], receiver_id)
        self.assertTrue(accept_result[0])  # tuple: (success, message)
        print("✓ Invitation accepted")
    
    def test_reject_invitation(self):
        """Test rejecting an invitation"""
        # Create users
        sender = self.auth_service.login(email="sender4@example.com", api_key="dummy", is_dummy=True)
        sender_id = sender['user']['user_id']
        
        # Create invitation
        result = self.invitation_service.create_invitation(
            from_user_id=sender_id,
            from_email="sender4@example.com",
            to_email="receiver4@example.com",
            task_id="task101"
        )
        
        # Reject invitation - takes only invitation_id, not user_id
        reject_result = self.invitation_service.reject_invitation(result['invitation_id'])
        self.assertTrue(reject_result[0])  # tuple: (success, message)
        print("✓ Invitation rejected")
    
    def test_get_pending_invitations_for_user(self):
        """Test getting pending invitations for a user email"""
        # Create users with unique emails to avoid test pollution
        unique_suffix = datetime.now().timestamp()
        sender = self.auth_service.login(email=f"sender5_{unique_suffix}@example.com", api_key="dummy", is_dummy=True)
        sender_id = sender['user']['user_id']
        
        receiver = self.auth_service.login(email=f"receiver5_{unique_suffix}@example.com", api_key="dummy", is_dummy=True)
        receiver_id = receiver['user']['user_id']
        
        # Create multiple invitations
        for i in range(3):
            self.invitation_service.create_invitation(
                from_user_id=sender_id,
                from_email=f"sender5_{unique_suffix}@example.com",
                to_email=f"receiver5_{unique_suffix}@example.com",
                task_id=f"task_{i}"
            )
        
        # Get pending invitations for receiver's email (not user_id)
        invitations = self.invitation_service.get_pending_invitations_for_user(f"receiver5_{unique_suffix}@example.com")
        
        # Should have at least 3 new invitations (may have more from previous runs)
        self.assertGreaterEqual(len(invitations), 3)
        print(f"✓ Retrieved {len(invitations)} pending invitations")


class TestTaskSharingService(unittest.TestCase):
    """Test task sharing and completion tracking"""
    
    def setUp(self):
        """Set up test environment"""
        from gtasks_cli.services.task_sharing_service import TaskSharingService
        from gtasks_cli.services.auth_service import AuthService
        
        self.task_service = TaskSharingService()
        self.auth_service = AuthService()
    
    def test_share_task_with_user(self):
        """Test sharing a task with a user"""
        # Create users
        owner = self.auth_service.login(email="owner1@example.com", api_key="dummy", is_dummy=True)
        owner_id = owner['user']['user_id']
        
        user = self.auth_service.login(email="user1@example.com", api_key="dummy", is_dummy=True)
        user_id = user['user']['user_id']
        
        result = self.task_service.share_task_with_user(
            task_id="shared_task_1",
            user_id=user_id,
            shared_by=owner_id
        )
        
        # share_task_with_user returns dict directly
        self.assertIn('task_id', result)
        self.assertIn('user_id', result)
        print("✓ Task shared with user")
    
    def test_share_task_multiple_users(self):
        """Test sharing a task with multiple users"""
        # Create users
        owner = self.auth_service.login(email="owner2@example.com", api_key="dummy", is_dummy=True)
        owner_id = owner['user']['user_id']
        
        user_ids = []
        for i in range(3):
            result = self.auth_service.login(email=f"multi_user{i}@example.com", api_key="dummy", is_dummy=True)
            user_ids.append(result['user']['user_id'])
        
        # Share task with all users
        for user_id in user_ids:
            self.task_service.share_task_with_user(
                task_id="multi_user_task",
                user_id=user_id,
                shared_by=owner_id
            )
        
        print("✓ Task shared with multiple users")
    
    def test_mark_task_complete(self):
        """Test marking a shared task as complete"""
        # Create users
        owner = self.auth_service.login(email="owner3@example.com", api_key="dummy", is_dummy=True)
        owner_id = owner['user']['user_id']
        
        user = self.auth_service.login(email="completer@example.com", api_key="dummy", is_dummy=True)
        user_id = user['user']['user_id']
        
        # Share task
        self.task_service.share_task_with_user(
            task_id="complete_task_1",
            user_id=user_id,
            shared_by=owner_id
        )
        
        # Mark as complete - returns tuple (success, message)
        result = self.task_service.mark_task_complete("complete_task_1", user_id)
        self.assertTrue(result[0])  # tuple: (success, message)
        print("✓ Task marked as complete")
    
    def test_get_tasks_for_user(self):
        """Test getting tasks shared with a user"""
        # Create users
        owner = self.auth_service.login(email="owner4@example.com", api_key="dummy", is_dummy=True)
        owner_id = owner['user']['user_id']
        
        user = self.auth_service.login(email="receiver_tasks@example.com", api_key="dummy", is_dummy=True)
        user_id = user['user']['user_id']
        
        # Share multiple tasks
        for i in range(3):
            self.task_service.share_task_with_user(
                task_id=f"receiver_task_{i}",
                user_id=user_id,
                shared_by=owner_id
            )
        
        # Get tasks for user
        tasks = self.task_service.get_tasks_for_user(user_id)
        
        self.assertEqual(len(tasks), 3)
        print(f"✓ Retrieved {len(tasks)} tasks for user")
    
    def test_get_pending_tasks_for_user(self):
        """Test getting pending (not completed) tasks for a user"""
        # Create users
        owner = self.auth_service.login(email="owner5@example.com", api_key="dummy", is_dummy=True)
        owner_id = owner['user']['user_id']
        
        user = self.auth_service.login(email="pending_user@example.com", api_key="dummy", is_dummy=True)
        user_id = user['user']['user_id']
        
        # Share multiple tasks
        for i in range(3):
            self.task_service.share_task_with_user(
                task_id=f"pending_task_{i}",
                user_id=user_id,
                shared_by=owner_id
            )
        
        # Complete one task
        self.task_service.mark_task_complete("pending_task_0", user_id)
        
        # Get pending tasks
        pending_tasks = self.task_service.get_pending_tasks_for_user(user_id)
        
        self.assertEqual(len(pending_tasks), 2)
        print(f"✓ Retrieved {len(pending_tasks)} pending tasks")
    
    def test_get_task_completion_stats(self):
        """Test getting completion statistics for a task"""
        # Create users
        owner = self.auth_service.login(email="owner6@example.com", api_key="dummy", is_dummy=True)
        owner_id = owner['user']['user_id']
        
        user_ids = []
        for i in range(3):
            result = self.auth_service.login(email=f"stats_user{i}@example.com", api_key="dummy", is_dummy=True)
            user_ids.append(result['user']['user_id'])
        
        # Share task with all users
        for user_id in user_ids:
            self.task_service.share_task_with_user(
                task_id="stats_task",
                user_id=user_id,
                shared_by=owner_id
            )
        
        # Complete task for one user
        self.task_service.mark_task_complete("stats_task", user_ids[0])
        
        # Get stats
        stats = self.task_service.get_task_completion_stats("stats_task")
        
        self.assertEqual(stats['total_assignments'], 3)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['pending'], 2)
        self.assertAlmostEqual(stats['completion_rate'], 33.33, places=1)
        print(f"✓ Task stats: {stats}")
    
    def test_get_overall_stats(self):
        """Test getting overall statistics"""
        # Create some task shares
        owner = self.auth_service.login(email="owner7@example.com", api_key="dummy", is_dummy=True)
        owner_id = owner['user']['user_id']
        
        user = self.auth_service.login(email="overall_user@example.com", api_key="dummy", is_dummy=True)
        user_id = user['user']['user_id']
        
        # Share multiple tasks
        for i in range(3):
            self.task_service.share_task_with_user(
                task_id=f"overall_task_{i}",
                user_id=user_id,
                shared_by=owner_id
            )
        
        # Complete some tasks
        self.task_service.mark_task_complete("overall_task_0", user_id)
        self.task_service.mark_task_complete("overall_task_1", user_id)
        
        # Get overall stats
        stats = self.task_service.get_overall_stats()
        
        # Check that stats are reasonable (may include previous test data)
        self.assertIn('total_shared_tasks', stats)
        self.assertIn('total_shares', stats)
        self.assertIn('total_completed', stats)
        self.assertIn('total_pending', stats)
        print(f"✓ Overall stats: {stats}")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow"""
    
    def test_complete_workflow(self):
        """Test the complete workflow from login to task sharing"""
        # Step 1: Login as sender
        from gtasks_cli.services.auth_service import AuthService
        from gtasks_cli.services.account_tag_service import AccountTagService
        from gtasks_cli.services.invitation_service import InvitationService
        from gtasks_cli.services.task_sharing_service import TaskSharingService
        
        auth_service = AuthService()
        tag_service = AccountTagService()
        invitation_service = InvitationService()
        task_service = TaskSharingService()
        
        # Create users
        sender = auth_service.login(email="workflow_sender@example.com", api_key="dummy", is_dummy=True)
        sender_id = sender['user']['user_id']
        
        receiver = auth_service.login(email="workflow_receiver@example.com", api_key="dummy", is_dummy=True)
        receiver_id = receiver['user']['user_id']
        
        # Step 2: Parse account tags from task description
        task_description = "Review document for [@workflow_receiver]"
        account_tags = tag_service.parse_account_tags(task_description)
        self.assertEqual(len(account_tags), 1)
        self.assertEqual(account_tags[0], "workflow_receiver")
        
        # Step 3: Register user account tag using register_tag_for_user
        tag_service.register_tag_for_user("workflow_receiver", receiver_id)
        stored_tags = tag_service.get_tags_for_user(receiver_id)
        self.assertIn("workflow_receiver", stored_tags)
        
        # Step 4: Create invitation - returns dict
        invitation = invitation_service.create_invitation(
            from_user_id=sender_id,
            from_email="workflow_sender@example.com",
            to_email="workflow_receiver@example.com",
            task_id="workflow_task_123",
            message="Please review this document"
        )
        self.assertIn('invitation_id', invitation)
        
        # Step 5: Accept invitation - returns tuple
        accept_result = invitation_service.accept_invitation(invitation['invitation_id'], receiver_id)
        self.assertTrue(accept_result[0])  # tuple: (success, message)
        
        # Step 6: Share task with user - returns dict
        share_result = task_service.share_task_with_user(
            task_id="workflow_task_123",
            user_id=receiver_id,
            shared_by=sender_id
        )
        self.assertIn('task_id', share_result)
        
        # Step 7: Get tasks for receiver
        receiver_tasks = task_service.get_tasks_for_user(receiver_id)
        self.assertEqual(len(receiver_tasks), 1)
        
        # Step 8: Mark task as complete - returns tuple
        complete_result = task_service.mark_task_complete("workflow_task_123", receiver_id)
        self.assertTrue(complete_result[0])  # tuple: (success, message)
        
        # Step 9: Get completion stats
        stats = task_service.get_task_completion_stats("workflow_task_123")
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['total_assignments'], 1)
        
        print("✓ Complete workflow test passed")
        print(f"  - User ID: {receiver_id}")
        print(f"  - Account tags: {stored_tags}")
        print(f"  - Invitation: {invitation['invitation_id']}")
        print(f"  - Task stats: {stats}")


def run_all_tests():
    """Run all test suites"""
    print("\n" + "=" * 60)
    print("  USER AUTHENTICATION AND ACCOUNT TAGS TEST SUITE")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestUserIDGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthenticationService))
    suite.addTests(loader.loadTestsFromTestCase(TestAccountTagService))
    suite.addTests(loader.loadTestsFromTestCase(TestInvitationService))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskSharingService))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
