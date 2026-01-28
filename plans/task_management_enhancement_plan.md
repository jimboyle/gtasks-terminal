# Task Management Enhancement Plan

## Overview
This plan outlines the implementation of two key features for the gTasks dashboard:

1. **edit_file Task Details** - Allow users to edit task fields with instant save and remote sync
2. **Mark as Incomplete** - Toggle completed tasks back to incomplete status with sync

## Architecture

### Current Pattern (Mark as Complete)
The existing `api_complete_task` endpoint follows this pattern:
```
Frontend → API Endpoint → Update In-Memory → Save to SQLite → Background Sync Threads
                                    ↓                                    ↓
                            Return Success                      Google Tasks + Turso DB
```

### New Features Pattern
```
edit_file Task:
Frontend → edit_file Modal → API Endpoint → Update Fields → Save → Background Sync

Mark as Incomplete:
Frontend → Toggle Button → API Endpoint → Reset Status → Background Sync
```

---

## Implementation Plan

### Phase 1: Backend API Endpoints

#### 1.1 Mark as Incomplete Endpoint
**File:** `gtasks_dashboard/routes/api.py`

Add new endpoint:
```python
POST /tasks/<task_id>/incomplete
```

**Logic:**
1. Find task in memory
2. Reset status from 'completed' to 'pending'
3. Clear `completed_at` field
4. Update `modified_at` timestamp
5. Save to local SQLite database
6. Trigger background sync to Google Tasks (inverse of complete)
7. Trigger background sync to Turso Remote DB

**Response:**
```json
{
    "success": true,
    "message": "Task marked as incomplete",
    "syncing": true
}
```

#### 1.2 Update Task Endpoint
**File:** `gtasks_dashboard/routes/api.py`

Add new endpoint:
```python
POST /tasks/<task_id>/update
```

**Request Body:**
```json
{
    "title": "Updated title",
    "description": "Updated description",
    "due": "2024-12-31",
    "priority": "high",
    "status": "in_progress",
    "tags": ["#tag1", "@account2"]
}
```

**Logic:**
1. Find and validate task exists
2. Update only provided fields
3. Update `modified_at` timestamp
4. Save to local SQLite
5. Trigger background sync to Google Tasks
6. Trigger background sync to Turso Remote DB

**Response:**
```json
{
    "success": true,
    "message": "Task updated successfully",
    "task": { /* updated task object */ }
}
```

#### 1.3 Background Sync Functions
**File:** `gtasks_dashboard/routes/api.py`

Add new background sync function similar to `_sync_task_to_google_background`:

```python
def _sync_task_update_to_google_background(task_id: str, account_id: str, updates: dict):
    """Background task to sync task updates to Google Tasks"""
    # Similar pattern to _sync_task_to_google_background
    # But updates all modified fields instead of just status
```

---

### Phase 2: Frontend UI Changes

#### 2.1 Mark as Incomplete Button
**File:** `gtasks_dashboard/static/js/task-card.js`

Modify the complete button HTML:
```javascript
// Current (line 52-60):
const completeBtnHtml = `
    <div class="task-complete-btn ${isCompleted ? 'completed' : ''}" 
         onclick="${isCompleted ? '' : `completeTask('${task.id}')`}"
         title="${isCompleted ? 'Completed' : 'Mark as complete'}">
        ${isCompleted ? '✅' : '⭕'}
    </div>
`;

// New:
const incompleteBtnHtml = isCompleted ? `
    <div class="task-incomplete-btn" 
         onclick="incompleteTask('${task.id}')"
         title="Mark as incomplete">
        ↩️
    </div>
` : '';

const completeBtnHtml = `
    <div class="task-complete-btn ${isCompleted ? 'completed' : ''}" 
         onclick="${isCompleted ? '' : `completeTask('${task.id}')`}"
         title="${isCompleted ? 'Completed' : 'Mark as complete'}">
        ${isCompleted ? '✅' : '⭕'}
    </div>
    ${incompleteBtnHtml}
`;
```

#### 2.2 edit_file Modal Component
**File:** `gtasks_dashboard/static/js/task-edit-modal.js` (new file)

Create new modal component with:
- Title input field
- Description textarea
- Due date picker
- Priority dropdown (none, low, medium, high, critical)
- Status dropdown (pending, in_progress, completed)
- Tags input with autocomplete
- Save/Cancel buttons

**Key Functions:**
```javascript
function openEditModal(task) {
    // Populate form with task data
    // Show modal
}

function saveTask(taskId) {
    // Collect form data
    // Call API endpoint
    // Refresh task view on success
}
```

#### 2.3 JavaScript API Functions
**File:** `gtasks_dashboard/static/js/api-client.js`

Add new functions:

```javascript
// Mark task as incomplete
async function incompleteTask(taskId) {
    const response = await fetch(`/tasks/${taskId}/incomplete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
}

// Update task
async function updateTask(taskId, updates) {
    const response = await fetch(`/tasks/${taskId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    });
    return response.json();
}
```

#### 2.4 CSS Styling
**File:** `gtasks_dashboard/static/css/task-card.css`

Add styles for:
```css
.task-incomplete-btn {
    cursor: pointer;
    font-size: 1.2rem;
    transition: transform 0.2s;
}

.task-incomplete-btn:hover {
    transform: scale(1.1);
}

/* edit_file Modal Styles */
.edit-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.edit-modal {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    width: 500px;
    max-width: 90%;
}
```

---

### Phase 3: Integration with Existing Code

#### 3.1 Update TaskViewManager
**File:** `gtasks_dashboard/static/js/task-view-manager.js`

Add edit handler to `onTaskClick` callback:
```javascript
const manager = new TaskViewManager('tasks-container', {
    onTaskClick: (task) => {
        openEditModal(task);
    }
});
```

#### 3.2 Update Main Dashboard
**File:** `gtasks_dashboard/main_dashboard.py`

Ensure new endpoints are registered:
```python
from routes.api import api

app.register_blueprint(api)

# Ensure the new endpoints are available
# POST /tasks/<task_id>/incomplete
# POST /tasks/<task_id>/update
```

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `gtasks_dashboard/routes/api.py` | Modify | Add incomplete and update endpoints |
| `gtasks_dashboard/static/js/task-card.js` | Modify | Add edit_file button, update complete button |
| `gtasks_dashboard/static/js/task-edit-modal.js` | Create | New edit modal component |
| `gtasks_dashboard/static/js/api-client.js` | Modify | Add incompleteTask and updateTask functions |
| `gtasks_dashboard/static/css/task-card.css` | Modify | Add modal and button styles |

---

## Testing Plan

### Unit Tests
1. Test API endpoint returns correct response for valid/invalid task IDs
2. Test database save operations
3. Test background sync function calls

### Integration Tests
1. Test complete → incomplete → complete flow
2. Test edit saves and syncs correctly
3. Test error handling for network failures

### UI Tests
1. Test modal opens with correct task data
2. Test form validation
3. Test button click handlers

---

## Error Handling

### API Level Errors
- Invalid task ID → 404
- Missing required fields → 400
- Database errors → 500
- Sync failures → Return success but log error

### UI Level Errors
- Show toast notification on API errors
- Revert optimistic UI updates on failure
- Retry sync on connection failure

---

## Security Considerations

1. **Input Validation**: Validate all incoming task data
2. **Authorization**: Ensure user can only edit their own tasks
3. **SQL Injection**: Use parameterized queries (already in place)
4. **XSS Prevention**: Sanitize task content before rendering

---

## Performance Considerations

1. **Background Sync**: All sync operations run in background threads
2. **Optimistic UI**: Update UI immediately, sync in background
3. **Debounce**: Debounce rapid edit operations
4. **Cache**: Use existing dashboard cache mechanism

---

## Migration Strategy

1. **Database**: No schema changes needed (all fields already exist)
2. **API**: New endpoints don't affect existing functionality
3. **UI**: New features are additive, no breaking changes
4. **Rollback**: Simply remove new endpoints if issues arise

---

## Timeline

- **Phase 1 (Backend)**: 2-3 hours
- **Phase 2 (Frontend)**: 3-4 hours  
- **Phase 3 (Integration)**: 1-2 hours
- **Testing**: 2-3 hours

**Total Estimated Time**: 8-12 hours
