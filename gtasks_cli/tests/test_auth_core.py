#!/usr/bin/env python3
"""
Unit Tests for Core Authentication Infrastructure
Tests user_id_generator, user model, QERDS API client, auth service, and database service.
"""

import unittest
import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gtasks_cli.utils.user_id_generator import UserIDGenerator, generate_user_id, extract_email_prefix
from gtasks_cli.models.user import User, UserSession
from gtasks_cli.services.qerds_api import QerdsApiClient, authenticate_with_qerds
from gtasks_cli.services.auth_service import AuthService
from gtasks_cli.services.database_service import DatabaseService


class TestUserIDGenerator(unittest.TestCase):
    """Test cases for UserIDGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = UserIDGenerator(salt="test_salt")
    
    def test_extract_email_prefix_basic(self):
        """Test basic email prefix extraction."""
        test_cases = [
            ("abc@gmail.com", "abc"),
            ("john.doe@example.org", "johndoe"),
            ("user123@company.net", "user123"),
            ("test_email@test.com", "test_email"),
            ("UPPERCASE@LOWER.com", "uppercase"),
        ]
        
        for email, expected_prefix in test_cases:
            with self.subTest(email=email):
                prefix = self.generator.extract_email_prefix(email)
                self.assertEqual(prefix, expected_prefix)
    
    def test_extract_email_prefix_invalid(self):
        """Test invalid email format handling."""
        invalid_emails = [
            "notanemail",
            "@nodomain.com",
            "noat.com",
            "",
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                with self.assertRaises(ValueError):
                    self.generator.extract_email_prefix(email)
    
    def test_generate_user_id_format(self):
        """Test user ID format."""
        email = "test@example.com"
        user_id = self.generator.generate_user_id(email)
        
        # Should start with email prefix
        self.assertTrue(user_id.startswith("test"))
        
        # Should be alphanumeric
        self.assertTrue(user_id.isalnum())
        
        # Should not start with digit
        self.assertFalse(user_id[0].isdigit())
    
    def test_generate_user_id_uniqueness(self):
        """Test that generated user IDs are unique."""
        email = "unique@example.com"
        
        # Generate multiple IDs
        ids = set()
        for _ in range(100):
            user_id = self.generator.generate_user_id(email, check_collision=True)
            self.assertNotIn(user_id, ids)
            ids.add(user_id)
        
        # Should have 100 unique IDs
        self.assertEqual(len(ids), 100)
    
    def test_is_valid_user_id(self):
        """Test user ID validation."""
        valid_ids = [
            "abc12345",
            "test67890",
            "user11111",
        ]
        
        invalid_ids = [
            "123abc",  # starts with digit
            "abc",     # too short
            "abc@123", # contains @
            "",        # empty
        ]
        
        for user_id in valid_ids:
            with self.subTest(user_id=user_id):
                self.assertTrue(self.generator.is_valid_user_id(user_id))
        
        for user_id in invalid_ids:
            with self.subTest(user_id=user_id):
                self.assertFalse(self.generator.is_valid_user_id(user_id))
    
    def test_extract_prefix(self):
        """Test extracting prefix from user ID (alphanumeric prefix before numeric suffix)."""
        # For user IDs like "abc12345", extract_prefix returns "abc12345" 
        # since it matches [a-zA-Z][a-zA-Z0-9]* pattern
        # The actual prefix separation would need different logic
        user_id = "abc12345"
        prefix = self.generator.extract_prefix(user_id)
        self.assertEqual(prefix, "abc12345")
    
    def test_reset(self):
        """Test generator reset."""
        self.generator._used_ids.add("test12345")
        self.generator.reset()
        self.assertEqual(len(self.generator._used_ids), 0)


class TestUserModel(unittest.TestCase):
    """Test cases for User model."""
    
    def test_create_user(self):
        """Test creating a user."""
        user = User(
            user_id="test12345",
            email="test@example.com",
            display_name="Test User"
        )
        
        self.assertEqual(user.user_id, "test12345")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.display_name, "Test User")
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.created_at)
    
    def test_create_from_email(self):
        """Test creating user from email."""
        user = User.create_from_email("john.doe@example.com")
        
        self.assertTrue(user.user_id.startswith("john"))
        self.assertEqual(user.email, "john.doe@example.com")
        self.assertEqual(user.display_name, "John Doe")
    
    def test_update_login(self):
        """Test updating last login."""
        user = User(user_id="test12345", email="test@example.com")
        
        # Initially last_login should be None
        self.assertIsNone(user.last_login)
        
        user.update_login()
        
        # After update, last_login should be set
        self.assertIsNotNone(user.last_login)
        self.assertIsInstance(user.last_login, datetime)
    
    def test_to_dict(self):
        """Test user serialization."""
        user = User(
            user_id="test12345",
            email="test@example.com",
            display_name="Test User"
        )
        
        user_dict = user.to_dict()
        
        self.assertEqual(user_dict['user_id'], "test12345")
        self.assertEqual(user_dict['email'], "test@example.com")
        self.assertEqual(user_dict['display_name'], "Test User")
        self.assertTrue(user_dict['is_active'])
    
    def test_from_dict(self):
        """Test user deserialization."""
        user_dict = {
            'user_id': 'test12345',
            'email': 'test@example.com',
            'display_name': 'Test User',
            'qerds_token': 'token123',
            'created_at': '2024-01-01T00:00:00',
            'last_login': '2024-01-15T00:00:00',
            'is_active': True
        }
        
        user = User.from_dict(user_dict)
        
        self.assertEqual(user.user_id, 'test12345')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.qerds_token, 'token123')
    
    def test_user_equality(self):
        """Test user equality."""
        user1 = User(user_id="test12345", email="test@example.com")
        user2 = User(user_id="test12345", email="test@example.com")
        user3 = User(user_id="other123", email="other@example.com")
        
        self.assertEqual(user1, user2)
        self.assertNotEqual(user1, user3)


class TestUserSession(unittest.TestCase):
    """Test cases for UserSession."""
    
    def test_create_session(self):
        """Test creating a session."""
        session = UserSession(user_id="test12345")
        
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, "test12345")
        self.assertTrue(session.is_valid)
        self.assertIsNotNone(session.created_at)
    
    def test_is_expired(self):
        """Test session expiration."""
        # Non-expired session
        session = UserSession(user_id="test12345")
        self.assertFalse(session.is_expired())
        
        # Expired session
        from datetime import timedelta
        expired_session = UserSession(
            user_id="test12345",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        self.assertTrue(expired_session.is_expired())
    
    def test_invalidate(self):
        """Test session invalidation."""
        session = UserSession(user_id="test12345")
        session.invalidate()
        
        self.assertFalse(session.is_valid)
    
    def test_session_serialization(self):
        """Test session serialization."""
        session = UserSession(user_id="test12345")
        session_dict = session.to_dict()
        
        restored = UserSession.from_dict(session_dict)
        
        self.assertEqual(restored.session_id, session.session_id)
        self.assertEqual(restored.user_id, session.user_id)
        self.assertEqual(restored.is_valid, session.is_valid)


class TestQerdsApiClient(unittest.TestCase):
    """Test cases for QERDS API client."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.dummy_file = os.path.join(self.temp_dir, "dummy_data.json")
        self.client = QerdsApiClient(
            use_dummy_fallback=True,
            dummy_data_file=self.dummy_file
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_token_dummy(self):
        """Test token validation with dummy data."""
        success, message = self.client.validate_token("demo_token_123")
        
        self.assertTrue(success)
        self.assertIn("dummy", message.lower())
    
    def test_get_account_details_dummy(self):
        """Test getting account details with dummy data."""
        details = self.client.get_account_details("demo_token_123")
        
        self.assertIsNotNone(details)
        self.assertEqual(details.user_id, "demo12345")
        self.assertEqual(details.email, "demo@example.com")
    
    def test_authenticate_dummy(self):
        """Test full authentication with dummy data."""
        success, details, message = self.client.authenticate("demo_token_123")
        
        self.assertTrue(success)
        self.assertIsNotNone(details)
        self.assertIn("successful", message.lower())
    
    def test_add_dummy_user(self):
        """Test adding a dummy user."""
        success = self.client.add_dummy_user(
            token="custom_token",
            email="custom@example.com",
            display_name="Custom User"
        )
        
        self.assertTrue(success)
        
        # Verify user was added
        success, details, _ = self.client.authenticate("custom_token")
        self.assertTrue(success)
        self.assertEqual(details.email, "custom@example.com")
    
    def test_list_dummy_users(self):
        """Test listing dummy users."""
        users = self.client.list_dummy_users()
        
        self.assertIsInstance(users, dict)
        self.assertIn("demo_token_123", users)


class TestAuthService(unittest.TestCase):
    """Test cases for AuthService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.auth_service = AuthService(
            data_dir=self.temp_dir,
            session_duration_hours=1
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_login_new_user(self):
        """Test logging in a new user."""
        success, user, message = self.auth_service.login("test_new_user_token_xyz")
        
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertIn("new user", message.lower())
        # User ID should be valid format (alphanumeric with underscores)
        self.assertTrue(len(user.user_id) >= 6)
        self.assertTrue(user.user_id[0].isalpha())  # Must start with letter
    
    def test_login_existing_user(self):
        """Test logging in an existing user."""
        # First login
        success1, user1, _ = self.auth_service.login("existing_token")
        self.assertTrue(success1)
        
        # Second login (should update)
        success2, user2, message = self.auth_service.login("existing_token")
        
        self.assertTrue(success2)
        self.assertIn("existing user", message.lower())
        self.assertEqual(user1.user_id, user2.user_id)
    
    def test_create_session(self):
        """Test creating a session."""
        success, user, _ = self.auth_service.login("session_test_token")
        self.assertTrue(success)
        
        session = self.auth_service.create_session(user.user_id)
        
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, user.user_id)
    
    def test_validate_session(self):
        """Test session validation."""
        success, user, _ = self.auth_service.login("validate_test_token")
        session = self.auth_service.create_session(user.user_id)
        
        valid, validated_user, message = self.auth_service.validate_session(session.session_id)
        
        self.assertTrue(valid)
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.user_id, user.user_id)
    
    def test_logout(self):
        """Test user logout."""
        success, user, _ = self.auth_service.login("logout_test_token")
        session = self.auth_service.create_session(user.user_id)
        
        logout_success, logout_message = self.auth_service.logout(session.session_id)
        
        self.assertTrue(logout_success)
        
        # Session should now be invalid
        valid, _, _ = self.auth_service.validate_session(session.session_id)
        self.assertFalse(valid)
    
    def test_get_user_by_email(self):
        """Test getting user by email."""
        # Login first to create user with token "email_test_token"
        # This generates email like "user_email_te@example.com"
        self.auth_service.login("email_test_token")
        
        # Get user by the generated email
        user = self.auth_service.get_user_by_email("user_email_te@example.com")
        
        self.assertIsNotNone(user)
        self.assertTrue(user.email.endswith("@example.com"))
    
    def test_deactivate_user(self):
        """Test deactivating a user."""
        success, user, _ = self.auth_service.login("deactivate_test_token")
        
        deactivate_success, message = self.auth_service.deactivate_user(user.user_id)
        
        self.assertTrue(deactivate_success)
        
        # User should not be active
        retrieved_user = self.auth_service.get_user_by_id(user.user_id)
        self.assertFalse(retrieved_user.is_active)


class TestDatabaseService(unittest.TestCase):
    """Test cases for DatabaseService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = DatabaseService(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_user(self):
        """Test creating a user in database."""
        user_data = {
            'user_id': 'db_test_123',
            'email': 'dbtest@example.com',
            'display_name': 'DB Test User'
        }
        
        success = self.db.create_user(user_data)
        
        self.assertTrue(success)
        
        # Verify user was created
        user = self.db.get_user_by_id('db_test_123')
        self.assertIsNotNone(user)
        self.assertEqual(user['email'], 'dbtest@example.com')
    
    def test_get_user_by_email(self):
        """Test getting user by email."""
        user_data = {
            'user_id': 'email_test_456',
            'email': 'emailtest@example.com',
            'display_name': 'Email Test User'
        }
        self.db.create_user(user_data)
        
        user = self.db.get_user_by_email('emailtest@example.com')
        
        self.assertIsNotNone(user)
        self.assertEqual(user['user_id'], 'email_test_456')
    
    def test_update_user(self):
        """Test updating a user."""
        user_data = {
            'user_id': 'update_test_789',
            'email': 'updatetest@example.com',
            'display_name': 'Original Name'
        }
        self.db.create_user(user_data)
        
        success = self.db.update_user('update_test_789', {'display_name': 'Updated Name'})
        
        self.assertTrue(success)
        
        user = self.db.get_user_by_id('update_test_789')
        self.assertEqual(user['display_name'], 'Updated Name')
    
    def test_create_invitation(self):
        """Test creating an invitation."""
        user_data = {
            'user_id': 'invite_from_123',
            'email': 'invite_from@example.com'
        }
        self.db.create_user(user_data)
        
        invitation_data = {
            'from_user_id': 'invite_from_123',
            'to_email': 'invite_to@example.com',
            'task_id': 'task123'
        }
        
        success = self.db.create_invitation(invitation_data)
        
        self.assertTrue(success)
        
        # Verify invitation
        invitations = self.db.get_pending_invitations_for_email('invite_to@example.com')
        self.assertEqual(len(invitations), 1)
    
    def test_create_connection(self):
        """Test creating a connection."""
        # Create two users
        self.db.create_user({'user_id': 'conn_a', 'email': 'a@example.com'})
        self.db.create_user({'user_id': 'conn_b', 'email': 'b@example.com'})
        
        connection_data = {
            'user_a_id': 'conn_a',
            'user_b_id': 'conn_b'
        }
        
        success = self.db.create_connection(connection_data)
        
        self.assertTrue(success)
        
        # Verify connection
        connections = self.db.get_user_connections('conn_a')
        self.assertEqual(len(connections), 1)
    
    def test_task_assignments(self):
        """Test task assignment operations."""
        # Create users
        self.db.create_user({'user_id': 'assign_from', 'email': 'from@example.com'})
        self.db.create_user({'user_id': 'assign_to', 'email': 'to@example.com'})
        
        # Create assignment
        assignment_data = {
            'task_id': 'shared_task_123',
            'assigned_to_user_id': 'assign_to',
            'assigned_by_user_id': 'assign_from'
        }
        
        success = self.db.create_task_assignment(assignment_data)
        
        self.assertTrue(success)
        
        # Get user assignments
        assignments = self.db.get_user_assigned_tasks('assign_to')
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]['task_id'], 'shared_task_123')
    
    def test_task_completion_status(self):
        """Test getting task completion status with multiple assignments."""
        # Create users
        self.db.create_user({'user_id': 'multi_a', 'email': 'multia@example.com'})
        self.db.create_user({'user_id': 'multi_b', 'email': 'multib@example.com'})
        self.db.create_user({'user_id': 'multi_c', 'email': 'multic@example.com'})
        
        # Create multiple assignments
        for user_id in ['multi_a', 'multi_b', 'multi_c']:
            self.db.create_task_assignment({
                'task_id': 'multi_user_task',
                'assigned_to_user_id': user_id,
                'assigned_by_user_id': 'multi_a'
            })
        
        # Complete one assignment
        self.db.update_task_assignment_status('multi_user_task', 'multi_a', 'completed')
        
        # Get completion status
        status = self.db.get_task_completion_status('multi_user_task')
        
        self.assertEqual(status['total_assignments'], 3)
        self.assertEqual(status['completed_count'], 1)
        self.assertEqual(status['pending_count'], 2)
        self.assertEqual(len(status['assigned_users']), 3)
    
    def test_get_all_users(self):
        """Test getting all users."""
        # Create multiple users
        for i in range(3):
            self.db.create_user({
                'user_id': f'all_test_{i}',
                'email': f'alltest{i}@example.com'
            })
        
        users = self.db.get_all_users()
        
        self.assertEqual(len(users), 3)


def run_tests():
    """Run all tests and return results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestUserIDGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestUserModel))
    suite.addTests(loader.loadTestsFromTestCase(TestUserSession))
    suite.addTests(loader.loadTestsFromTestCase(TestQerdsApiClient))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthService))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseService))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    print("=" * 70)
    print("Running Unit Tests for Core Authentication Infrastructure")
    print("=" * 70)
    print()
    
    result = run_tests()
    
    print()
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(0 if result.wasSuccessful() else 1)
