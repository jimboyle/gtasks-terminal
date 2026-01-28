# User Accounts, Tags & Task Sharing Feature - Implementation Checklist

## Overview
Implementation of user accounts, account tags with [@account] format, invitation system, and task sharing between connected users.

## Phase 1: Integration Layer (Orchestration Services)

### 1.1 AccountTagIntegrationService
- [ ] Create `services/account_tag_integration_service.py`
- [ ] Implement `detect_new_account_tags(tasks)` method
- [ ] Implement `check_connection_status(account_name)` method
- [ ] Implement `trigger_invitation_workflow(account_name, task_id)` method
- [ ] Add caching for detected account tags
- [ ] Write unit tests

### 1.2 InvitationWorkflowManager
- [ ] Create `services/invitation_workflow_manager.py`
- [ ] Implement `create_and_send_invitation(from_user, to_email, task_id)` method
- [ ] Implement `process_acceptance(invitation_id, user_id)` method
- [ ] Implement `create_bidirectional_connection(user1_id, user2_id)` method
- [ ] Integrate with QERDS API for email notifications
- [ ] Write unit tests

### 1.3 SharedTaskAccessService
- [ ] Create `services/shared_task_access_service.py`
- [ ] Implement `get_shared_tasks_for_user(user_id)` method
- [ ] Implement `get_tasks_shared_by_user(user_id)` method
- [ ] Implement `mark_task_complete(user_id, task_id, original_account)` method
- [ ] Implement `get_completion_status(task_id, original_account)` method
- [ ] Write unit tests

## Phase 2: Database Schema Enhancements

### 2.1 New Tables
- [ ] Create `user_task_completions` table schema
- [ ] Create `account_tags_cache` table schema
- [ ] Add database migration script
- [ ] Add indexes for performance

### 2.2 Database Service Updates
- [ ] Update `services/database_service.py` with new table operations
- [ ] Implement `save_user_task_completion()` method
- [ ] Implement `get_user_task_completion()` method
- [ ] Implement `update_user_task_completion()` method
- [ ] Implement `get_account_tags_cache()` methods
- [ ] Write unit tests

## Phase 3: CLI Commands Implementation

### 3.1 Connection Management Commands
- [ ] Update `commands/user.py` with connection commands
- [ ] Implement `gtasks user connections list`
- [ ] Implement `gtasks user invitations list`
- [ ] Implement `gtasks user invitations accept <id>`
- [ ] Implement `gtasks user invitations reject <id>`
- [ ] Implement `gtasks user invitations send <email> [--message TEXT]`

### 3.2 Shared Task Commands
- [ ] Update `commands/list.py` with shared task filters
- [ ] Implement `gtasks list --shared`
- [ ] Implement `gtasks list --shared-with-me`
- [ ] Implement `gtasks list --shared-by-me`
- [ ] Update `commands/done.py` to handle shared tasks

### 3.3 Account Tag Commands
- [ ] Create `commands/account_tags.py`
- [ ] Implement `gtasks account-tags list`
- [ ] Implement `gtasks account-tags scan`
- [ ] Implement `gtasks account-tags stats <tag>`

## Phase 4: Dashboard API Endpoints

### 4.1 Authentication APIs
- [ ] `POST /api/auth/login` - Login with QERDS API key
- [ ] `POST /api/auth/logout` - Logout
- [ ] `GET /api/auth/me` - Get current user info

### 4.2 Connection APIs
- [ ] `GET /api/connections` - List all connections
- [ ] `GET /api/connections/pending` - List pending invitations received
- [ ] `POST /api/connections/:connection_id/accept` - Accept invitation
- [ ] `POST /api/connections/:connection_id/reject` - Reject invitation
- [ ] `DELETE /api/connections/:connection_id` - Remove connection

### 4.3 Invitation APIs
- [ ] `GET /api/invitations/sent` - List invitations sent by me
- [ ] `POST /api/invitations` - Create new invitation
- [ ] `DELETE /api/invitations/:invitation_id` - Cancel invitation

### 4.4 Task Sharing APIs
- [ ] `GET /api/tasks/shared-with-me` - Get tasks shared with current user
- [ ] `GET /api/tasks/shared-by-me` - Get tasks shared by current user
- [ ] `POST /api/tasks/:task_id/complete` - Mark task as complete
- [ ] `GET /api/tasks/:task_id/completion-status` - Get completion status

### 4.5 Account Tag APIs
- [ ] `GET /api/account-tags` - List all known account tags
- [ ] `POST /api/account-tags/scan` - Scan tasks for new account tags
- [ ] `GET /api/account-tags/:tag/statistics` - Get statistics

## Phase 5: Dashboard UI Components

### 5.1 Connections Management Page
- [ ] Create `templates/settings/connections.html`
- [ ] Add CSS styles for connections page
- [ ] Implement JavaScript for connections management
- [ ] Add API calls for connections operations
- [ ] Add accept/reject invitation UI
- [ ] Add connection activity timeline

### 5.2 Shared Tasks View
- [ ] Update `templates/dashboard.html` with shared tasks filter
- [ ] Add "Shared with me" filter option
- [ ] Implement shared task cards with completion status
- [ ] Add visual indicator for shared tasks
- [ ] Implement per-user completion status display

### 5.3 Invitation Notifications
- [ ] Add toast notification component
- [ ] Implement real-time invitation checking
- [ ] Add badge count on connections menu
- [ ] Add email notification status display

### 5.4 Account Tag Insights Dashboard
- [ ] Create account tag statistics widget
- [ ] Add tag usage visualization
- [ ] Show connection status per account tag
- [ ] Display pending invitations count

## Phase 6: Integration & Testing

### 6.1 Integration Tests
- [ ] Test complete invitation workflow
- [ ] Test task sharing between connected users
- [ ] Test task completion tracking per user
- [ ] Test CLI commands with API integration
- [ ] Test dashboard UI with API integration

### 6.2 User Acceptance Testing
- [ ] Test user registration and login flow
- [ ] Test task creation with [@account] tags
- [ ] Test invitation sending and acceptance
- [ ] Test shared task visibility
- [ ] Test task completion in shared context

### 6.3 Performance Testing
- [ ] Test with large number of tasks
- [ ] Test with many connections
- [ ] Test database query performance
- [ ] Test API response times
- [ ] Optimize slow queries

## Phase 7: Documentation

### 7.1 User Documentation
- [ ] Create user guide for connections feature
- [ ] Document invitation workflow
- [ ] Create CLI command reference
- [ ] Add screenshots for dashboard features
- [ ] Write FAQ for common questions

### 7.2 Developer Documentation
- [ ] Document architecture and data flow
- [ ] Document API endpoints
- [ ] Add database schema documentation
- [ ] Document integration points
- [ ] Add contribution guidelines

## Implementation Order

### Sprint 1 (Week 1)
- [ ] Create integration services (1.1, 1.2, 1.3)
- [ ] Add database schema and migration
- [ ] Update database service
- [ ] Complete CLI connection commands (3.1)
- [ ] Complete CLI shared task commands (3.2)

### Sprint 2 (Week 2)
- [ ] Complete account tag commands (3.3)
- [ ] Implement all API endpoints (4.1-4.5)
- [ ] Create connections management page (5.1)
- [ ] Implement shared tasks view (5.2)

### Sprint 3 (Week 3)
- [ ] Add invitation notifications (5.3)
- [ ] Create account tag insights (5.4)
- [ ] Run integration tests (6.1)
- [ ] Fix bugs and issues

### Sprint 4 (Week 4)
- [ ] User acceptance testing (6.2)
- [ ] Performance testing and optimization (6.3)
- [ ] Complete documentation (7.1, 7.2)
- [ ] Final polish and release

## Dependencies

### External Dependencies
- QERDS API key for email notifications
- Database SQLite (already in use)

### Internal Dependencies
- Existing user authentication service
- Existing invitation service
- Existing task sharing service
- Existing account tag service
- Existing database service

### Files to Create
- `gtasks_cli/src/gtasks_cli/services/account_tag_integration_service.py`
- `gtasks_cli/src/gtasks_cli/services/invitation_workflow_manager.py`
- `gtasks_cli/src/gtasks_cli/services/shared_task_access_service.py`
- `gtasks_cli/src/gtasks_cli/commands/account_tags.py`
- `gtasks_dashboard/templates/settings/connections.html`

### Files to Modify
- `gtasks_cli/src/gtasks_cli/services/database_service.py`
- `gtasks_cli/src/gtasks_cli/commands/user.py`
- `gtasks_cli/src/gtasks_cli/commands/list.py`
- `gtasks_cli/src/gtasks_cli/commands/done.py`
- `gtasks_dashboard/routes/api.py`
- `gtasks_dashboard/templates/dashboard.html`
- `gtasks_dashboard/static/css/dashboard.css`
- `gtasks_dashboard/static/js/dashboard.js`

## Success Criteria

1. **Functional Requirements**
   - Users can create tasks with [@account] tags
   - System auto-creates invitations for new account tags
   - Invited users can accept/reject invitations
   - Connected users can see each other's shared tasks
   - Task completion is tracked per user

2. **Performance Requirements**
   - API response time < 500ms
   - Database queries optimized with indexes
   - Dashboard loads in < 2 seconds with 1000+ tasks
   - Invitation emails sent within 5 seconds

3. **User Experience**
   - Intuitive connection management UI
   - Clear indication of shared tasks
   - Easy invitation acceptance flow
   - Responsive design for all devices

4. **Reliability**
   - 99% uptime for API endpoints
   - Automatic retry for failed email notifications
   - Graceful handling of missing users/connections
   - Comprehensive error messages

## Notes

- All features must be API-driven for CLI and dashboard
- QERDS API key required for email notifications
- User IDs generated from email prefix + hash
- Task completion tracked per user, not globally
- Connections are bidirectional once accepted
- Invitations expire after 30 days by default

---

**Created:** 2024-01-23
**Status:** Implementation Started
**Priority:** High
