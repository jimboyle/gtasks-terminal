# User Authentication & Account Tags Implementation Plan

## Overview
This plan outlines the implementation of a comprehensive user authentication system with account tags, invitation workflow, and Turso DB integration for the gtasks automation project.

**NOTE**: QERDS.com is only used for authentication via https://qerds.com/tools/tgs. All other features (invitations, tasks, connections) are managed locally using Turso DB.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    gtasks_automation                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │   gtasks_cli     │    │  gtasks_dashboard │               │
│  └────────┬─────────┘    └────────┬─────────┘               │
│           │                       │                          │
│           └───────────┬───────────┘                          │
│                       ▼                                      │
│           ┌───────────────────────┐                          │
│           │   Auth Service        │                          │
│           │   (QERDS Integration) │                          │
│           └───────────┬───────────┘                          │
│                       ▼                                      │
│           ┌───────────────────────┐                          │
│           │  Local Services       │                          │
│           │  - Invitations        │                          │
│           │  - Connections        │                          │
│           │  - Task Assignment    │                          │
│           └───────────┬───────────┘                          │
│                       ▼                                      │
│           ┌───────────────────────┐                          │
│           │      Turso DB         │                          │
│           │   (Remote Database)   │                          │
│           └───────────────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## User Authentication & Identity System

### 1. QERDS.com Authentication Integration
- **Login Flow**: User authenticates via https://qerds.com/tools/tgs
- **Token Generation**: QERDS provides authentication token
- **Two QERDS APIs**:
  1. **Validate Token**: `POST /api/validate-token` - Validate QERDS token
  2. **Get Account Details**: `GET /api/account-details` - Get user info from token

### 2. User ID Generation (Local)
- **Logic**: `abc@gmail.com` → `abc12345` (email prefix + unique suffix)
- **Implementation**: Create `utils/user_id_generator.py`
- **Features**:
  - Extract email prefix (before @)
  - Generate 5-character unique suffix
  - Collision detection and resolution
  - Case-insensitive matching

### 3. User Model
- **File**: `models/user.py`
- **Fields**:
  - `user_id`: str (unique identifier like abc12345)
  - `email`: str (full email address)
  - `display_name`: str (user-friendly name)
  - `qerds_token`: str (QERDS authentication token)
  - `created_at`: datetime
  - `last_login`: datetime

### 4. Authentication System
- **CLI Commands**:
  - `gtasks login --token <qerds_token>` - Login with QERDS token
  - `gtasks logout` - Logout current user
  - `gtasks auth status` - Check authentication status
  
- **Dashboard**: Login page with token input
- **Session Management**: Token-based sessions stored locally
- **Token Validation**: Validate against QERDS APIs (with dummy fallback for testing)

## Account Tag System

### 1. Enhanced Tag Extraction
- **Current**: Tags extracted as `@user`, `#tag`, `[bracket]`
- **New**: Differentiate `@account` tags from `@user` tags
- **Logic**:
  - When creating task with `[@account_name]`, treat as account tag
  - Store separately from regular user tags
  - Index for fast lookups

### 2. Task Assignment Model (Many-to-Many)
**Key Change**: Tasks can be assigned to MULTIPLE accounts simultaneously

**Task Assignments Table**:
```sql
CREATE TABLE task_assignments (
    assignment_id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL,
    assigned_to_user_id VARCHAR(50) NOT NULL,
    assigned_by_user_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    completed_at TIMESTAMP,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (assigned_to_user_id) REFERENCES users(user_id),
    FOREIGN KEY (assigned_by_user_id) REFERENCES users(user_id)
);

-- Composite unique constraint
CREATE UNIQUE INDEX idx_task_user_assignment 
ON task_assignments(task_id, assigned_to_user_id);
```

**Task Status Display Logic**:
- **Completed by some accounts**: Show both "completed by X accounts" and "pending from Y accounts"
- **Example**: Task assigned to 3 users, 2 completed → "Completed (2/3), Pending from 1"

### 3. Tag Classification
- **Account Tags**: `[@username]` - refers to user accounts
- **User Tags**: `@username` - general mentions (not account-linked)
- **Hash Tags**: `#tag` - categorization
- **Priority Tags**: `[priority]` - task priority

## Invitation System

### 1. Invitation Workflow
```
1. User A creates task with [@UserB]
2. System detects account tag not in database
3. Popup: "Send invitation to UserB?"
4. User A enters UserB's email
5. System creates invitation record in Turso DB
6. System sends invitation email (local email service)
7. User B receives email with link
8. User B must login via QERDS
9. User B sees invitation notification
10. User B accepts invitation
11. Connection established between User A and UserB
12. User B can now view and manage assigned tasks
```

### 2. Invitation Data Model
- **File**: `models/invitation.py`
- **Fields**:
  - `invitation_id`: str (unique identifier)
  - `from_user_id`: str (user sending invitation)
  - `to_email`: str (recipient email)
  - `to_user_id`: str (nullable, populated on acceptance)
  - `task_id`: str (optional, specific task)
  - `status`: enum (pending, accepted, expired)
  - `created_at`: datetime
  - `expires_at`: datetime

### 3. Connection Data Model
- **File**: `models/connection.py`
- **Fields**:
  - `connection_id`: str
  - `user_a_id`: str
  - `user_b_id`: str
  - `created_at`: datetime
  - `status`: enum (active, blocked)

## Local Services (Turso DB)

### 1. Turso Database Setup
- **Use existing remote sync service structure**
- **Database**: Turso DB (libSQL)
- **Tables**: Users, Invitations, Connections, Task_Assignments

### 2. Local API Endpoints (Micro Service)
- **File**: `services/local_api_service.py`
- **Endpoints**:
  - `POST /api/invitations/send` - Create invitation
  - `GET /api/invitations/pending` - Get pending invitations
  - `POST /api/invitations/accept` - Accept invitation
  - `GET /api/tasks/assigned` - Get tasks assigned to user
  - `POST /api/tasks/sync` - Sync task data
  - `GET /api/connections` - Get user connections
  - `POST /api/connections` - Create connection

### 3. QERDS.com API Client
- **File**: `services/qerds_api.py`
- **Limited to Authentication Only**:
  1. **Validate Token**: Validate QERDS authentication token
  2. **Get Account Details**: Extract user info from QERDS token
- **Dummy Fallback**: For testing without QERDS dependency

## Database Schema (Turso DB)

### 1. Users Table
```sql
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    qerds_token VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX idx_users_email ON users(email);
```

### 2. Invitations Table
```sql
CREATE TABLE invitations (
    invitation_id VARCHAR(50) PRIMARY KEY,
    from_user_id VARCHAR(50) REFERENCES users(user_id),
    to_email VARCHAR(255) NOT NULL,
    to_user_id VARCHAR(50) REFERENCES users(user_id),
    task_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_invitations_email ON invitations(to_email);
CREATE INDEX idx_invitations_status ON invitations(status);
CREATE INDEX idx_invitations_from_user ON invitations(from_user_id);
```

### 3. Connections Table
```sql
CREATE TABLE connections (
    connection_id VARCHAR(50) PRIMARY KEY,
    user_a_id VARCHAR(50) REFERENCES users(user_id),
    user_b_id VARCHAR(50) REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

-- Indexes for performance
CREATE INDEX idx_connections_user_a ON connections(user_a_id);
CREATE INDEX idx_connections_user_b ON connections(user_b_id);
```

### 4. Task Assignments Table (Many-to-Many)
**Key Feature**: Tasks can be assigned to MULTIPLE accounts

```sql
CREATE TABLE task_assignments (
    assignment_id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL,
    assigned_to_user_id VARCHAR(50) NOT NULL,
    assigned_by_user_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    completed_at TIMESTAMP,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (assigned_to_user_id) REFERENCES users(user_id),
    FOREIGN KEY (assigned_by_user_id) REFERENCES users(user_id)
);

-- Composite unique constraint (one assignment per user per task)
CREATE UNIQUE INDEX idx_task_user_assignment 
ON task_assignments(task_id, assigned_to_user_id);

-- Index for user's assigned tasks
CREATE INDEX idx_assignments_user ON task_assignments(assigned_to_user_id);

-- Index for task assignments
CREATE INDEX idx_assignments_task ON task_assignments(task_id);
```

### 5. Query for Task Status with Multiple Assignments

**SQL Query for Task Status**:
```sql
-- Get task with completion status from all assigned users
SELECT 
    t.id,
    t.title,
    COUNT(DISTINCT ta.assignment_id) as total_assignments,
    SUM(CASE WHEN ta.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
    SUM(CASE WHEN ta.status = 'pending' THEN 1 ELSE 0 END) as pending_count,
    GROUP_CONCAT(DISTINCT u.display_name) as assigned_users
FROM tasks t
LEFT JOIN task_assignments ta ON t.id = ta.task_id
LEFT JOIN users u ON ta.assigned_to_user_id = u.user_id
WHERE t.id = 'task123'
GROUP BY t.id;
```

**Display Logic**:
- If `completed_count > 0` AND `pending_count > 0`: Show "Completed (2/3), Pending from 1"
- If `completed_count = total_assignments`: Show "Completed by all"
- If `pending_count = total_assignments`: Show "Pending from all"

## CLI Commands

### 1. Authentication Commands
```bash
# Login with QERDS token
gtasks login --token <qerds_token>

# Logout
gtasks logout

# Check authentication status
gtasks auth status

# Show current user
gtasks auth whoami
```

### 2. Connection Commands
```bash
# List connections
gtasks connections list

# Remove connection
gtasks connections remove <connection_id>
```

### 3. Invitation Commands
```bash
# Send invitation
gtasks invitations send user@example.com --task task123

# List pending invitations
gtasks invitations list

# Accept invitation
gtasks invitations accept <invitation_id>

# Decline invitation
gtasks invitations decline <invitation_id>
```

### 4. Task Commands
```bash
# View tasks assigned to you
gtasks list --assigned

# View tasks for specific account tag
gtasks list --account-tag @username

# Complete task (assigned to you)
gtasks done task123

# View task assignment status
gtasks view task123 --show-assignments
```

## Dashboard Integration

### 1. Login Page
- **File**: `templates/login.html`
- **Features**:
  - QERDS token input form
  - Login button
  - "Get Token from QERDS" link
  - Session persistence
  - **Demo mode for testing (dummy data)**

### 2. User Profile
- **File**: `templates/profile.html`
- **Features**:
  - Display user ID
  - Show QERDS token status
  - Manage connections
  - View invitation history

### 3. Invitations Panel
- **File**: `templates/invitations.html`
- **Features**:
  - List pending invitations
  - Accept/Decline buttons
  - Invitation details
  - Task preview

### 4. Connections Page
- **File**: `templates/connections.html`
- **Features**:
  - List active connections
  - Connection details
  - Remove connection option
  - Search connections

### 5. Assigned Tasks View
- **Features**:
  - Filter tasks by assignment
  - View tasks assigned to current user
  - Complete assigned tasks
  - Task details with assigner info
  - **Multi-assignment status**: Show "Completed (2/3), Pending from 1"

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Create user_id_generator utility
- [ ] Implement User model
- [ ] Set up Turso DB schema
- [ ] Create QERDS API client (2 APIs only)
- [ ] Implement basic authentication service
- [ ] **Add dummy data fallback for testing**

### Phase 2: CLI Authentication (Week 2-3)
- [ ] Add login/logout commands with token
- [ ] Implement session management
- [ ] Create auth status command
- [ ] Write unit tests with dummy data

### Phase 3: Dashboard Login (Week 3-4)
- [ ] Create login page HTML/CSS
- [ ] Implement login API endpoints
- [ ] Add session handling to dashboard
- [ ] Create profile page
- [ ] Integrate with existing dashboard

### Phase 4: Account Tag System (Week 4-5)
- [ ] Enhance tag extraction logic
- [ ] Implement task_assignments table
- [ ] Implement tag classification
- [ ] Create account tag indexing
- [ ] Update task creation/update logic

### Phase 5: Invitation System (Week 5-6)
- [ ] Create Invitation model
- [ ] Create Connection model
- [ ] Implement invitation workflow (local Turso DB)
- [ ] Add local email service
- [ ] Build invitation acceptance logic

### Phase 6: Task Sharing (Week 6-7)
- [ ] Implement assigned tasks endpoint
- [ ] Add completion by assigned users
- [ ] Create multi-assignment status display
- [ ] Build access control validation
- [ ] Add task assignment UI

### Phase 7: Dashboard Integration (Week 7-8)
- [ ] Create invitations panel
- [ ] Build connections management page
- [ ] Implement assigned tasks view
- [ ] Add notification system
- [ ] Final integration testing

### Phase 8: Performance & Polish (Week 8-9)
- [ ] Database optimization
- [ ] Caching implementation
- [ ] Error handling improvements
- [ ] Documentation
- [ ] Final testing and bug fixes

## File Structure

```
gtasks_cli/src/gtasks_cli/
├── commands/
│   ├── auth.py              # Updated authentication commands
│   ├── connections.py       # New: connection management
│   └── invitations.py       # New: invitation management
├── models/
│   ├── user.py              # New: User model
│   ├── invitation.py        # New: Invitation model
│   ├── connection.py        # New: Connection model
│   └── task.py              # Updated: Enhanced with assignments
├── services/
│   ├── auth_service.py      # New: Authentication logic
│   ├── invitation_service.py # New: Invitation workflow
│   ├── connection_service.py # New: Connection management
│   ├── task_assignment_service.py # New: Task assignment logic
│   └── qerds_api.py         # New: QERDS.com API client (2 APIs)
└── utils/
    ├── user_id_generator.py # New: abc@gmail.com -> abc12345
    └── tag_classifier.py    # New: Classify tags as account/user/hash

gtasks_dashboard/
├── routes/
│   ├── auth.py              # New: Login/logout endpoints
│   ├── connections.py       # New: Connection management
│   └── invitations.py       # New: Invitation handling
├── services/
│   └── auth_service.py      # New: Dashboard auth logic
├── templates/
│   ├── login.html           # New: Login page
│   ├── profile.html         # New: User profile
│   ├── invitations.html     # New: Invitation management
│   └── connections.html     # New: Connections page
└── static/js/
    ├── auth.js              # New: Auth state management
    └── invitations.js       # New: Invitation handling
```

## API Endpoints

### QERDS.com Integration (Authentication Only)
- `POST /api/qerds/validate-token` - Validate QERDS token (**dummy fallback for testing**)
- `GET /api/qerds/account-details` - Get account details from token (**dummy fallback for testing**)

### Local API Endpoints (Turso DB)

#### Authentication
- `POST /api/v1/auth/login` - Login with QERDS token
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/status` - Check auth status
- `GET /api/v1/auth/profile` - Get user profile

#### Connections
- `GET /api/v1/connections` - List user connections
- `POST /api/v1/connections` - Create connection
- `DELETE /api/v1/connections/<id>` - Remove connection

#### Invitations
- `POST /api/v1/invitations/send` - Send invitation (local Turso DB)
- `GET /api/v1/invitations` - List pending invitations
- `POST /api/v1/invitations/<id>/accept` - Accept invitation
- `POST /api/v1/invitations/<id>/decline` - Decline invitation

#### Tasks
- `GET /api/v1/tasks/assigned` - Get tasks assigned to user
- `POST /api/v1/tasks/<id>/complete` - Complete assigned task
- `GET /api/v1/tasks/<id>/assignments` - Get task assignment status
- `POST /api/v1/tasks/<id>/assign` - Assign task to user
- `GET /api/v1/tasks?account_tag=<tag>` - Filter by account tag
- `POST /api/v1/tasks/sync` - Sync task data (local Turso DB)

## Performance Considerations

### 1. Database Optimization
- Index on `account_tags` for fast lookups
- Compound indexes for common query patterns
- Connection pooling for database access
- Pagination for large result sets

### 2. Caching Strategy
- Cache user data (with invalidation)
- Cache connection lists
- Cache pending invitations
- Use Redis for session storage

### 3. Query Optimization
- Use parameterized queries
- Batch database operations
- Limit result sets with pagination
- Use read replicas for heavy reads

### 4. Scalability
- Stateless authentication
- Horizontal scaling support
- Rate limiting per API key
- Async processing for emails

## Security Considerations

### 1. Authentication
- Secure session management
- API key rotation
- Rate limiting
- Input validation

### 2. Data Protection
- Encrypt sensitive data
- Secure API key storage
- HTTPS for all API calls
- Input sanitization

### 3. Access Control
- Validate user permissions
- Check connection status before sharing
- Audit logging for all actions
- Session timeout management

## Testing Strategy

### 1. Unit Tests
- User ID generation logic
- Tag classification
- Authentication flow
- Invitation workflow

### 2. Integration Tests
- CLI commands
- Dashboard API endpoints
- QERDS.com API integration
- Database operations

### 3. End-to-End Tests
- Complete login flow
- Invitation acceptance workflow
- Task sharing and completion
- Dashboard user journey

## Migration Strategy

### 1. Database Migration
- Create new tables
- Migrate existing data if needed
- Add new columns to tasks table
- Create necessary indexes

### 2. Backward Compatibility
- Maintain existing tag format
- Support old task format during transition
- Provide migration utilities
- Gradual rollout plan

### 3. Rollback Plan
- Database backup before migration
- Feature flags for gradual rollout
- Quick rollback procedure
- Data recovery plan

## Documentation Requirements

### 1. User Documentation
- Login instructions
- Account tag usage guide
- Invitation workflow explanation
- CLI command reference

### 2. Developer Documentation
- API documentation
- Database schema
- Architecture overview
- Contributing guidelines

### 3. API Documentation
- Endpoint descriptions
- Request/response formats
- Error codes
- Authentication requirements

## Success Metrics

### 1. Performance
- Login response time < 2s
- Task loading with account tags < 500ms
- Invitation delivery < 5s
- Dashboard load time < 3s

### 2. Reliability
- 99.9% uptime for authentication
- 99.5% email delivery rate
- Zero data loss during sync
- < 1% error rate for API calls

### 3. User Adoption
- 80% of users login within first week
- 50% of users use account tags
- 30% of users send invitations
- Positive user feedback scores

## Risk Assessment

### 1. Technical Risks
- QERDS.com API reliability
- Database performance at scale
- Security vulnerabilities
- Integration complexity

### 2. Mitigation Strategies
- Fallback authentication methods
- Database optimization
- Security audits
- Phased implementation

## Timeline and Resources

### Estimated Effort
- **Total Duration**: 9 weeks
- **Team Size**: 1-2 developers
- **Effort Estimate**: 720-960 person-hours

### Key Milestones
- **Week 2**: Core infrastructure complete
- **Week 4**: CLI authentication working
- **Week 6**: Invitation system functional
- **Week 8**: Dashboard integration complete
- **Week 9**: Performance optimization and testing

## Conclusion

This implementation plan provides a comprehensive roadmap for building a user authentication system with account tags and invitation workflow. The phased approach allows for incremental development and testing while maintaining backward compatibility. The focus on performance, security, and scalability ensures the system can grow with user needs.
