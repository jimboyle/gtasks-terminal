# Account Tags Feature - Implementation Plan

## Overview

This plan addresses the completion of the account tags feature, including fixing existing issues and completing remaining implementation work.

## Current State Assessment

### Backend (Mostly Complete ✅)
- User authentication and ID generation
- Account tag service for managing @account tags
- Invitation service for sending/accepting invitations
- Task sharing service for managing shared tasks
- Database service for data persistence
- QERDS API integration for remote storage
- CLI user commands (partial)

### Frontend (Issues Found ❌)
- Tags page missing sidebar navigation
- Settings page features incomplete
- Tags integration in Tasks view incomplete
- Import existing tags functionality missing

## Issues to Fix

### 1. Tags Page Missing Sidebar

**Problem:** The tags.html page doesn't have the standard dashboard sidebar navigation.

**Solution:**
1. Examine dashboard.html to understand sidebar structure
2. Apply same sidebar to tags.html
3. Ensure consistent navigation across all pages

**Files to Modify:**
- `gtasks_dashboard/templates/tags.html` - Add sidebar
- `gtasks_dashboard/static/css/tags.css` - Ensure proper styling

### 2. Settings Page Features

**Problem:** Settings page needs feature parity with dashboard header.

**Solution:**
1. Check dashboard.html for header features (night mode, user info, etc.)
2. Apply same features to settings.html
3. Fix any broken functionality

**Files to Modify:**
- `gtasks_dashboard/templates/settings.html` - Add header features
- `gtasks_dashboard/static/css/settings.css` - Ensure proper styling

### 3. Tags Integration in Tasks View

**Problem:** Tags should be visible in task list and synced properly without duplicates.

**Solution:**
1. Ensure tags are displayed in task list
2. Prevent duplicate tags during sync
3. Add tag filtering/display in task view

**Files to Modify:**
- `gtasks_dashboard/templates/dashboard.html` - Update task display
- `gtasks_dashboard/static/js/dashboard.js` - Add tag integration
- `gtasks_cli/src/gtasks_cli/core/task_manager.py` - Fix tag sync logic

### 4. Import Existing Tags

**Problem:** Need to import existing Google Tasks tags as regular tags.

**Solution:**
1. Create script to extract existing Google Tasks tags
2. Import them as regular tags (not @account tags)
3. Ensure no duplicates

**Files to Create:**
- `gtasks_cli/scripts/import_existing_tags.py` - Import script

**Files to Modify:**
- `gtasks_cli/src/gtasks_cli/services/tag_service.py` - Add import functionality

## Remaining Implementation

### 5. CLI Commands for Connections

**Commands to Implement:**

#### 5.1 `gtasks user connections`
List all user connections.

**Implementation:**
- Add command to `gtasks_cli/src/gtasks_cli/commands/user.py`
- Use `account_tag_service.get_connections()` to fetch connections
- Display connections in tabular format

#### 5.2 `gtasks user invite <email>`
Send invitation to connect with another user.

**Implementation:**
- Add command to `gtasks_cli/src/gtasks_cli/commands/user.py`
- Use `invitation_service.send_invitation(email)` to send invitation
- Display invitation details and status

#### 5.3 `gtasks user invitations`
List pending invitations.

**Implementation:**
- Add command to `gtasks_cli/src/gtasks_cli/commands/user.py`
- Use `invitation_service.get_pending_invitations()` to fetch invitations
- Display invitations in tabular format

#### 5.4 `gtasks user accept <invitation_id>`
Accept a pending invitation.

**Implementation:**
- Add command to `gtasks_cli/src/gtasks_cli/commands/user.py`
- Use `invitation_service.accept_invitation(invitation_id)` to accept invitation
- Display acceptance status and details

### 6. Email Service Integration

**Configuration:**

Create `gtasks_cli/config/email_config.yaml`:

```yaml
email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "${EMAIL_USER}"
  smtp_password: "${EMAIL_PASSWORD}"
  from_address: "noreply@gtasks.local"
  from_name: "GTasks Automation"
  
invitation:
  subject: "You've been invited to connect on GTasks"
  template: "invitation_email.html"
```

**Implementation:**

1. **Create email service:**
   - `gtasks_cli/src/gtasks_cli/services/email_service.py`
   - SMTP configuration and sending functionality
   - Email templates for invitations

2. **Environment variables:**
   - `EMAIL_USER` - SMTP username
   - `EMAIL_PASSWORD` - SMTP password
   - Add to `gtasks_cli/config/default_config.yaml`

3. **Test email delivery:**
   - Create test script to verify email sending
   - Test with real SMTP server

### 7. Integration Testing

**Test Cases:**

#### 7.1 Complete User Flow
1. User logs in (creates unique ID)
2. User creates task with @account tag
3. System sends invitation email
4. Recipient accepts invitation
5. Both users can see the shared task
6. Task completion is tracked per user

**Test Script:** `gtasks_cli/tests/test_complete_flow.py`

#### 7.2 CLI Commands
1. `gtasks user connections` - Lists connections correctly
2. `gtasks user invite` - Sends invitation successfully
3. `gtasks user invitations` - Shows pending invitations
4. `gtasks user accept` - Accepts invitation correctly

**Test Script:** `gtasks_cli/tests/test_cli_connections.py`

#### 7.3 Dashboard Integration
1. Tags page displays correctly with sidebar
2. Settings page has all features
3. Tags are visible in task list
4. Sync doesn't create duplicate tags

**Test Script:** `gtasks_dashboard/tests/test_integration.py`

## Implementation Order

### Phase 1: Fix Critical Issues
1. Fix tags page sidebar
2. Fix settings page features
3. Fix tags integration in tasks view

### Phase 2: Import Existing Tags
1. Create import script
2. Test import functionality
3. Verify no duplicates

### Phase 3: Complete CLI Commands
1. Implement `gtasks user connections`
2. Implement `gtasks user invite`
3. Implement `gtasks user invitations`
4. Implement `gtasks user accept`

### Phase 4: Email Integration
1. Create email service
2. Configure SMTP settings
3. Create email templates
4. Test email delivery

### Phase 5: Integration Testing
1. Test complete user flow
2. Test CLI commands
3. Verify dashboard integration
4. Fix any issues found

## Success Criteria

1. ✅ Tags page has proper sidebar navigation
2. ✅ Settings page has feature parity with dashboard
3. ✅ Tags are visible and synced properly in tasks view
4. ✅ Existing Google Tasks tags can be imported
5. ✅ All CLI connection commands work correctly
6. ✅ Email invitations are sent and received
7. ✅ Complete user flow works end-to-end
8. ✅ No duplicate tags are created during sync

## Risk Mitigation

1. **Email delivery issues:** Provide clear error messages and fallback options
2. **Duplicate tags:** Implement deduplication logic in import and sync
3. **Frontend compatibility:** Test across different browsers and devices
4. **Performance:** Optimize tag sync for large datasets

## Timeline

- Phase 1: 2-3 hours (critical fixes)
- Phase 2: 1-2 hours (import functionality)
- Phase 3: 2-3 hours (CLI commands)
- Phase 4: 2-3 hours (email integration)
- Phase 5: 2-4 hours (testing and fixes)

**Total Estimated Time:** 9-15 hours

## Next Steps

1. Review and approve this plan
2. Start with Phase 1 (critical fixes)
3. Proceed through phases sequentially
4. Regular testing after each phase
5. Update documentation as needed
