# GTasks Automation - Architecture Overview

## Project Purpose
Google Tasks automation tool with CLI and Web Dashboard interfaces for managing tasks, reports, and multi-account support.

---

## Core Components

### 1. gtasks_cli (Command Line Interface)
**Purpose**: Primary CLI application for managing Google Tasks

**Key Components**:

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **Entry Point** | `gtasks_cli/src/gtasks_cli/main.py` | CLI group, command routing, global options |
| **Commands** | `gtasks_cli/src/gtasks_cli/commands/` | Individual command modules (add, list, search, view, done, delete, update, auth, user, summary, interactive, deduplicate, account, advanced_sync, generate_report, config, ai, mcp, tasklist, import-tags) |
| **Models** | `gtasks_cli/src/gtasks_cli/models/` | Data structures (Task, TaskList, Account) |
| **Reports** | `gtasks_cli/src/gtasks_cli/reports/` | Report generators (base_report, task_completion_report, pending_tasks_report, organized_tasks_report, etc.) |
| **Utils** | `gtasks_cli/src/gtasks_cli/utils/` | Helper utilities (email_sender, exceptions, logger) |
| **Interactive Utils** | `gtasks_cli/src/gtasks_cli/commands/interactive_utils/` | Interactive mode helpers (add_commands, delete_commands, list_commands, update_commands, display, search, undo_manager, etc.) |

**Storage Options**: JSON or SQLite backends, sync with Google Tasks API

---

### 2. gtasks_dashboard (Web Dashboard)
**Purpose**: Visual web interface for task management using Flask + D3.js

**Key Components**:

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **Entry Point** | `gtasks_dashboard/main_dashboard.py` | Flask app initialization, blueprint registration, feature flag management |
| **Routes** | `gtasks_dashboard/routes/api.py` | REST API endpoints for task operations |
| **Routes** | `gtasks_dashboard/routes/dashboard.py` | Page routes and view rendering |
| **Services** | `gtasks_dashboard/services/data_manager.py` | Business logic, data transformation, task operations |
| **Services** | `gtasks_dashboard/services/sync_service.py` | Thread-safe sync operations with progress tracking for advanced sync |
| **Services** | `gtasks_dashboard/services/dashboard_generator.py` | Static HTML dashboard generation (optional export) |
| **Models** | `gtasks_dashboard/models/` | Data models (Task, Account, DashboardStats, HybridTags) |
| **Modules** | `gtasks_dashboard/modules/priority_system.py` | Priority calculation and management |
| **Modules** | `gtasks_dashboard/modules/tag_manager.py` | Hybrid tag extraction (@user, #tag, [bracket]) |
| **Modules** | `gtasks_dashboard/modules/account_manager.py` | Multi-account support |
| **Modules** | `gtasks_dashboard/modules/settings_manager.py` | Dashboard configuration persistence |
| **Templates** | `gtasks_dashboard/templates/dashboard.html` | Main dashboard template |
| **Templates** | `gtasks_dashboard/templates/static_dashboard.html` | Standalone export template (optional) |
| **UI Components** | `gtasks_dashboard/ui_components.py` | Reusable UI components |
| **Config** | `gtasks_dashboard/config.py` | Dashboard configuration, feature flags |
| **Frontend Modules** | `gtasks_dashboard/static/js/` | Modular JavaScript for dashboard |

**Frontend JavaScript Modules**:

| Module | File | Responsibility |
|--------|------|---------------|
| **Constants** | `constants.js` | Configuration, color scales, API endpoints, storage keys |
| **Utils** | `utils.js` | Utility functions (date parsing, filtering, sorting) |
| **State** | `state.js` | Centralized state management |
| **Task Card** | `task-card.js` | Task card component rendering |
| **Dashboard** | `dashboard.js` | Main dashboard functionality and initialization |
| **Hierarchy** | `hierarchy.js` | D3.js hierarchy visualization |
| **Hierarchy Renderer** | `hierarchy-renderer.js` | D3.js graph rendering logic |
| **Hierarchy Interactions** | `hierarchy-interactions.js` | Node click, drag, and tooltip handling |
| **Hierarchy Filters** | `hierarchy-filters.js` | Filtering hierarchy data by tags, status, date |
| **Hierarchy Task Panel** | `hierarchy-task-panel.js` | Task display panel for selected nodes |
| **Hierarchy Ledger** | `hierarchy-ledger.js` | Tabular ledger view with click interactions |

**Frontend CSS Modules**:

| Module | File | Responsibility |
|--------|------|---------------|
| **Base Styles** | `dashboard.css` | Core layout, components, responsive design |
| **Dark Mode** | `dark-mode.css` | Dark mode specific styles |
| **Components** | `components.css` | Button, header, toggle styles |
| **Modal** | `modal.css` | Settings modal and overlay |
| **Hierarchy Filter** | `hierarchy-filter.css` | Hierarchy filter panel styles |
| **Hierarchy Ledger** | `hierarchy-ledger.css` | Ledger table and related tasks panel styles |

**Frontend**: HTML + JavaScript with Force-Graph/D3.js for hierarchical visualization + DataTables for task listing

**Architecture Principles**:
- **Single Source of Truth**: One dashboard implementation with feature flags
- **Modular Design**: Services handle business logic, routes handle HTTP, templates handle presentation
- **Configuration-Driven**: Features enabled/disabled via `config.py`, not duplicate files

---

### 3. Shared Concepts

| Concept | Description |
|---------|-------------|
| **Task Model** | Core entity representing a task with title, notes, due date, status, parent/child relationships, tags |
| **Multi-Account Support** | Ability to switch between multiple Google accounts |
| **Tag System** | Hybrid tagging with `@user`, `#tag`, `[priority]` formats |
| **Sync** | Two-way synchronization with Google Tasks API |
| **Reports** | Various task reports (completion, pending, timeline, distribution) |

---

## Data Flow

```
User Input (CLI or Web)
        ↓
Command/Route Handler
        ↓
Service Layer (data_manager, sync)
        ↓
Storage (SQLite/JSON) or Google Tasks API
        ↓
Response/View Rendering
```

---

## Entry Points

| Application | Command |
|-------------|---------|
| CLI | `python -m gtasks_cli` or `gtasks` (after installation) |
| Dashboard | `python gtasks_dashboard/main_dashboard.py` |
| Installation | `python install.py` |

---

## Dependencies

- **Python 3.x**
- **Google APIs**: google-auth, google-api-python-client
- **CLI**: click (command-line interface)
- **Dashboard**: flask, d3.js (frontend)
- **Database**: sqlite3 (built-in)
- **Reports**: Various visualization and reporting modules

---

## 🧠 AI Context Layer (Git-Native)
| Component | Implementation | Responsibility |
|-----------|----------------|----------------|
| **Memory Store** | `context-llemur` | Stores logic/rules in `context/` as plain text |
| **Tooling** | **MCP** | Exposes `ctx_read/write` to Kilo, Continue, and OpenCode |
| **Version Sync** | **Git** | Synchronizes AI "memory" across local and remote clones |

---

## 👥 User Accounts & Connections System

### Overview
This system enables task sharing between users through account tags and invitations.

### Key Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **User ID Generator** | `gtasks_cli/src/gtasks_cli/utils/user_id_generator.py` | Generates unique user IDs from emails (abc@gmail.com → abc12345) |
| **Auth Service** | `gtasks_cli/src/gtasks_cli/services/auth_service.py` | User authentication with QERDS API key |
| **Account Tag Service** | `gtasks_cli/src/gtasks_cli/services/account_tag_service.py` | Detects and manages [@account] tags in tasks |
| **Invitation Service** | `gtasks_cli/src/gtasks_cli/services/invitation_service.py` | Manages invitation lifecycle |
| **Invitation Workflow Manager** | `gtasks_cli/src/gtasks_cli/services/invitation_workflow_manager.py` | Orchestrates invitation creation, email sending, acceptance |
| **Task Sharing Service** | `gtasks_cli/src/gtasks_cli/services/task_sharing_service.py` | Tracks shared tasks and completion status |
| **Shared Task Access Service** | `gtasks_cli/src/gtasks_cli/services/shared_task_access_service.py` | Manages task visibility and per-user completion tracking |
| **QERDS API** | `gtasks_cli/src/gtasks_cli/services/qerds_api.py` | External API for email and data storage |
| **User Model** | `gtasks_cli/src/gtasks_cli/models/user.py` | User data structure |

### CLI Commands

| Command | File | Description |
|---------|------|-------------|
| `gtasks connections list` | `commands/connections.py` | List all connections |
| `gtasks connections pending` | `commands/connections.py` | List pending invitations |
| `gtasks connections accept <id>` | `commands/connections.py` | Accept an invitation |
| `gtasks connections reject <id>` | `commands/connections.py` | Reject an invitation |
| `gtasks connections sent` | `commands/connections.py` | List sent invitations |
| `gtasks shared list` | `commands/shared.py` | List tasks shared with you |
| `gtasks shared by-me` | `commands/shared.py` | List tasks you've shared |
| `gtasks shared complete <id>` | `commands/shared.py` | Mark shared task as complete |
| `gtasks shared stats` | `commands/shared.py` | Show shared tasks statistics |

### API Endpoints

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/shared/tasks` | GET | Get shared tasks for current user |
| `/api/shared/tasks/<id>/complete` | POST | Mark shared task as complete |
| `/api/shared/stats` | GET | Get shared tasks statistics |
| `/api/invitations/create` | POST | Create and send invitation |
| `/api/invitations/accept/<id>` | POST | Accept invitation via workflow |
| `/api/invitations/sent` | GET | Get sent invitations |
| `/api/invitations/pending` | GET | Get pending invitations |
| `/api/account-tags/detect` | POST | Detect account tags in text |
| `/api/account-tags/validate` | POST | Validate account tag against email |
| `/api/user/id` | GET | Get current user ID info |

### Database Schema

**Users Table** (`users.db`):
- `id`: User ID (e.g., abc12345)
- `email`: User email
- `api_key`: QERDS API key
- `created_at`: Account creation timestamp
- `last_login`: Last login timestamp

**Connections Table** (`connections.db`):
- `id`: Connection ID
- `user_id1`: First user ID
- `user_id2`: Second user ID
- `status`: Connection status (active, inactive)
- `created_at`: Connection creation timestamp

**Invitations Table** (`invitations.db`):
- `id`: Invitation ID
- `from_user_id`: Sender's user ID
- `from_user_email`: Sender's email
- `to_email`: Recipient's email
- `to_account_name`: Recipient's account name
- `task_id`: Optional shared task ID
- `task_title`: Optional task title
- `message`: Optional message
- `status`: Invitation status (pending, accepted, rejected, cancelled)
- `created_at`: Invitation creation timestamp
- `expires_at`: Expiration timestamp
- `responded_at`: Response timestamp

**Task Completions Table** (`task_completions.db`):
- `user_id`: User who completed the task
- `task_id`: Task ID
- `original_account_id`: Account where task was created
- `completion_status`: Status (pending, in_progress, completed)
- `completed_at`: Completion timestamp
- `shared_at`: Sharing timestamp

### User ID Generation

**Format**: `{account_name}{hash}`

**Examples**:
- `abc@gmail.com` → `abc12345`
- `john.doe@company.com` → `johndoe67890`

**Hash Generation**:
```python
def generate_user_id(email: str) -> str:
    account_name = email.split('@')[0].lower()
    hash_suffix = hashlib.md5(email.encode()).hexdigest()[:5]
    return f"{account_name}{hash_suffix}"
```

### Account Tags

**Format**: `[@account_name]` or `@account_name`

**Detection**:
- Regular expressions extract tags from task descriptions
- Tags are stored with @ prefix in task data
- Account name is matched against user IDs

**Workflow**:
1. User creates task with `[@other_account]` tag
2. System detects the tag and creates invitation
3. Invitation email sent to the other user
4. User accepts invitation via login
5. Connection established between users
6. Both users can see shared tasks
7. Each user marks completion independently

### Invitation Flow

```
1. Task Creation with [@account] tag
         ↓
2. Detect new account tag
         ↓
3. Create invitation record
         ↓
4. Send email via QERDS API
         ↓
5. User receives email and logs in
         ↓
6. User views pending invitations
         ↓
7. User accepts invitation
         ↓
8. Create bidirectional connection
         ↓
9. Both users can access shared tasks
```

### Task Sharing & Completion

**Shared Task Access**:
- Tasks shared with a user appear in their "Shared with Me" view
- Tasks shared by a user appear in their "Shared by Me" view
- Completion is tracked per-user
- Task owner sees completion status of all shared users

**Completion Tracking**:
```
Task: "Review document"
├─ Shared with: @john, @jane
├─ John: ✅ completed (2024-01-15)
└─ Jane: ⏳ pending
```

---

## 🌐 Browser Debugging Tools (MCP)
| Tool | Purpose | Key Functions |
|------|---------|---------------|
| **Playwright** | Interactive browser automation and testing | `browser_fill_form`, `browser_click`, `browser_take_screenshot`, `browser_snapshot`, `browser_console_messages`, `browser_network_requests` |

### Playwright Usage Guidelines
- **Navigation**: Use `browser_navigate` to navigate to URLs
- **DOM Inspection**: Use `browser_snapshot` to inspect DOM structure
- **Form Interactions**: Use `browser_fill_form`, `browser_click` for form filling and clicking
- **Screenshots**: Use `browser_take_screenshot` to capture page screenshots
- **Console Errors**: Use `browser_console_messages` to retrieve error logs
- **Network Monitoring**: Use `browser_network_requests` to monitor API calls

### Browser Debugging Workflow
1. **For UI Issues**: Use `browser_snapshot` to inspect DOM structure
2. **For Console Errors**: Use `browser_console_messages` to retrieve error logs
3. **For Network Issues**: Use `browser_network_requests` to monitor API calls
4. **For Automation**: Use `browser_fill_form`, `browser_click` for form interactions and user flows

---

## 🏗 Core Components

### 1. gtasks_cli (Command Line)
- **Location**: `gtasks_cli/src/gtasks_cli/`
- **Logic**: Uses `click` for command routing.
- **Key Modules**: 
    - `commands/`: Individual logic for `add`, `list`, `sync`, etc.
    - `models/`: Schema for `Task` and `Account`.
    - `reports/`: Logic for generating pending/completion summaries.

### 2. gtasks_dashboard (Web UI)
- **Location**: `gtasks_dashboard/`
- **Stack**: Flask (Backend) + D3.js (Frontend Visualization).
- **Logic**: Handles hierarchical task views and priority management.

---

## 🔄 Data & Sync Flow


1. **Input**: User triggers action via CLI Command or Flask Route.
2. **Context Check**: AI verifies rules in `context/rules.md`.
3. **Service**: `data_manager` or `sync_service` processes logic.
4. **Storage**: SQLite/JSON updated; Google Tasks API synced via OAuth2.
5. **Context Update**: AI updates `architecture.md` if structure changed.

---

## 🚀 Entry Points
- **CLI**: `python -m gtasks_cli`
- **Web**: `python gtasks_dashboard/main_dashboard.py`
- **AI Sync**: `ctx save` (Run this before `git push`)

---

## 🐛 Route Prefix Bug Fix (2024-01-18)

### Problem
API routes were returning 404 errors with double `/api/api/` in the path:
```
Expected: /gtasks/gtasks-terminal/gtasks_dashboard/api/data
Actual:   /gtasks/gtasks-terminal/gtasks_dashboard/api/api/data
```

### Root Cause
- Routes in `routes/api.py` are defined with `@api.route('/api/data')` (already include `/api`)
- `main_dashboard.py` set `api.url_prefix = f'{BASE_PATH}/api'`
- Combined: `BASE_PATH` + `/api` + `/api/data` = double `/api/api/`

### Solution
Changed line 40 in `main_dashboard.py`:
```python
# Before (buggy):
api.url_prefix = f'{BASE_PATH}/api'

# After (fixed):
api.url_prefix = BASE_PATH
```

### URL Path Structure After Fix
| Environment | BASE_PATH | API Endpoint | Full URL |
|-------------|-----------|--------------|----------|
| Production | `/gtasks/gtasks-terminal/gtasks_dashboard` | `/api/data` | `/gtasks/gtasks-terminal/gtasks_dashboard/api/data` |
| Local Dev | `/api` | `/api/data` | `/api/data` |

### Key Files
- `gtasks_dashboard/main_dashboard.py`: Flask app initialization, BASE_PATH configuration
- `gtasks_dashboard/routes/api.py`: API route definitions (already include `/api` prefix)
- `gtasks_dashboard/nginx.conf`: Reverse proxy configuration for subpath deployment