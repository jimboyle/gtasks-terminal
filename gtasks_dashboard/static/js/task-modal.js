/**
 * Task Modal JavaScript
 * Handles task creation and editing with tag autocomplete for @account tags
 */

// Global state
let currentTags = [];
let connectedAccounts = [];
let pendingInvitations = [];
let isEditMode = false;
let editTaskId = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeTaskModal();
});

/**
 * Initialize the task modal
 */
function initializeTaskModal() {
    // Check if we're in edit mode
    const taskIdElement = document.getElementById('task-id');
    if (taskIdElement && taskIdElement.value) {
        isEditMode = true;
        editTaskId = taskIdElement.value;
        loadTaskData(editTaskId);
    }

    // Load connected accounts for autocomplete
    loadConnectedAccounts();

    // Load pending invitations
    loadPendingInvitations();

    // Set up event listeners
    setupEventListeners();

    // Set up form submission
    setupFormSubmission();

    // Set up tag input handling
    setupTagInput();

    // Check for task_id in URL for sharing scenarios
    checkUrlForTaskId();

    // Check for invitation acceptance
    checkInvitationAcceptance();
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Close modal button
    const closeBtn = document.getElementById('task-modal-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeTaskModal);
    }

    // Cancel button
    const cancelBtn = document.getElementById('task-modal-cancel');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeTaskModal);
    }

    // Close modal on overlay click
    const overlay = document.getElementById('task-modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeTaskModal();
            }
        });
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeTaskModal();
        }
    });

    // Priority buttons
    const priorityButtons = document.querySelectorAll('.priority-btn');
    priorityButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all priority buttons
            priorityButtons.forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            // Update hidden input
            const priorityInput = document.getElementById('task-priority');
            if (priorityInput) {
                priorityInput.value = this.dataset.priority;
            }
        });
    });

    // Status dropdown
    const statusSelect = document.getElementById('task-status');
    if (statusSelect) {
        statusSelect.addEventListener('change', function() {
            // Status change handling if needed
        });
    }

    // Due date input
    const dueDateInput = document.getElementById('task-due-date');
    if (dueDateInput) {
        // Set default to today
        const today = new Date().toISOString().split('T')[0];
        dueDateInput.value = today;
    }
}

/**
 * Set up tag input with autocomplete
 */
function setupTagInput() {
    const tagsInput = document.getElementById('task-tags-input');
    const autocompleteDropdown = document.getElementById('tags-autocomplete');
    const tagsDisplay = document.getElementById('tags-display');

    if (!tagsInput || !autocompleteDropdown || !tagsDisplay) {
        console.error('Tag input elements not found');
        return;
    }

    // Focus handler
    tagsInput.addEventListener('focus', function() {
        const value = this.value.trim();
        if (value.length === 0 || value === '@') {
            showAutocomplete('@');
        }
    });

    // Input handler
    tagsInput.addEventListener('input', function() {
        const value = this.value.trim();
        handleTagsInput(value);
    });

    // Keydown handler
    tagsInput.addEventListener('keydown', function(e) {
        handleTagsKeydown(e);
    });

    // Blur handler - hide autocomplete after a delay
    tagsInput.addEventListener('blur', function() {
        setTimeout(() => {
            autocompleteDropdown.style.display = 'none';
        }, 200);
    });

    // Click on autocomplete item
    autocompleteDropdown.addEventListener('click', function(e) {
        const item = e.target.closest('.autocomplete-item');
        if (item) {
            selectTag(item.dataset.tag, item.dataset.type);
        }
    });

    // Click on tag in display (to remove)
    tagsDisplay.addEventListener('click', function(e) {
        const tagChip = e.target.closest('.tag-chip');
        if (tagChip) {
            removeTag(tagChip.dataset.tag);
        }
    });
}

/**
 * Handle tag input changes
 */
function handleTagsInput(value) {
    if (value.startsWith('@')) {
        showAutocomplete(value);
    } else if (value.startsWith('#')) {
        showHashtagAutocomplete(value);
    } else {
        document.getElementById('tags-autocomplete').style.display = 'none';
    }
}

/**
 * Handle keyboard events in tag input
 */
function handleTagsKeydown(e) {
    const autocompleteDropdown = document.getElementById('tags-autocomplete');
    const items = autocompleteDropdown.querySelectorAll('.autocomplete-item:not([style*="display: none"])');

    if (e.key === 'ArrowDown' && autocompleteDropdown.style.display !== 'none') {
        e.preventDefault();
        if (items.length > 0) {
            items[0].focus();
        }
    } else if (e.key === 'Enter') {
        const focusedItem = autocompleteDropdown.querySelector('.autocomplete-item:focus');
        if (focusedItem) {
            e.preventDefault();
            selectTag(focusedItem.dataset.tag, focusedItem.dataset.type);
        } else if (autocompleteDropdown.style.display !== 'none' && items.length > 0) {
            e.preventDefault();
            selectTag(items[0].dataset.tag, items[0].dataset.type);
        }
    } else if (e.key === 'Backspace' && e.target.value === '' && currentTags.length > 0) {
        removeTag(currentTags[currentTags.length - 1]);
    }
}

/**
 * Show autocomplete dropdown for @account tags
 */
function showAutocomplete(query) {
    const dropdown = document.getElementById('tags-autocomplete');
    if (!dropdown) return;

    const items = [];
    const queryLower = query.toLowerCase();

    // Add connected accounts that match the query
    connectedAccounts.forEach(account => {
        const tag = account.tag.toLowerCase();
        if (tag.includes(queryLower) || query === '@') {
            items.push({
                tag: account.tag,
                type: 'account',
                label: account.tag,
                description: account.email,
                isNew: false
            });
        }
    });

    // Add "Invite new" option
    if (query.startsWith('@') && query.length > 1) {
        const potentialName = query.substring(1);
        items.push({
            tag: query,
            type: 'invite',
            label: `Invite ${potentialName}`,
            description: 'Send invitation to connect',
            isNew: true
        });
    }

    // Render dropdown
    if (items.length > 0) {
        dropdown.innerHTML = items.map(item => `
            <div class="autocomplete-item ${item.isNew ? 'new-account' : 'existing-account'}" 
                 data-tag="${item.tag}" 
                 data-type="${item.type}" 
                 tabindex="0">
                <div class="item-label">${item.label}</div>
                <div class="item-description">${item.description}</div>
            </div>
        `).join('');
        dropdown.style.display = 'block';
    } else {
        dropdown.style.display = 'none';
    }
}

/**
 * Show autocomplete dropdown for #hashtag tags
 */
function showHashtagAutocomplete(query) {
    const dropdown = document.getElementById('tags-autocomplete');
    if (!dropdown) return;

    // Get existing hashtags from the system
    const hashtags = getExistingHashtags();
    const queryLower = query.toLowerCase();
    const items = [];

    hashtags.forEach(tag => {
        if (tag.toLowerCase().includes(queryLower)) {
            items.push({
                tag: tag,
                type: 'hashtag',
                label: tag,
                isExisting: true
            });
        }
    });

    // Add current input as option
    if (query.length > 1) {
        items.unshift({
            tag: query,
            type: 'hashtag',
            label: `Create "${query}"`,
            isNew: true
        });
    }

    // Render dropdown
    if (items.length > 0) {
        dropdown.innerHTML = items.map(item => `
            <div class="autocomplete-item ${item.isNew ? 'new-hashtag' : 'existing-hashtag'}" 
                 data-tag="${item.tag}" 
                 data-type="${item.type}" 
                 tabindex="0">
                <div class="item-label">${item.label}</div>
            </div>
        `).join('');
        dropdown.style.display = 'block';
    } else {
        dropdown.style.display = 'none';
    }
}

/**
 * Select a tag from autocomplete
 */
function selectTag(tag, type) {
    const tagsInput = document.getElementById('task-tags-input');
    const autocompleteDropdown = document.getElementById('tags-autocomplete');

    if (type === 'invite') {
        // Show invitation modal
        const email = tag.substring(1) + '@example.com'; // Placeholder
        showInvitationModal(tag, email);
        tagsInput.value = '';
        autocompleteDropdown.style.display = 'none';
        return;
    }

    // Add tag to current tags if not already present
    if (!currentTags.includes(tag)) {
        currentTags.push(tag);
        renderTags();
    }

    tagsInput.value = '';
    autocompleteDropdown.style.display = 'none';
    tagsInput.focus();
}

/**
 * Remove a tag
 */
function removeTag(tag) {
    currentTags = currentTags.filter(t => t !== tag);
    renderTags();
}

/**
 * Render tags in the display area
 */
function renderTags() {
    const tagsDisplay = document.getElementById('tags-display');
    if (!tagsDisplay) return;

    tagsDisplay.innerHTML = currentTags.map(tag => {
        const isAccountTag = tag.startsWith('@');
        const tagClass = isAccountTag ? 'account-tag' : 'regular-tag';
        return `
            <span class="tag-chip ${tagClass}" data-tag="${tag}">
                ${escapeHtml(tag)}
                <span class="remove-tag" onclick="removeTag('${escapeHtml(tag)}')">×</span>
            </span>
        `;
    }).join('');
}

/**
 * Show invitation modal
 */
function showInvitationModal(tag, email) {
    const modal = document.getElementById('invitation-modal-overlay');
    const tagDisplay = document.getElementById('invitation-tag-display');
    const emailInput = document.getElementById('invitation-email');

    if (!modal || !tagDisplay || !emailInput) {
        console.error('Invitation modal elements not found');
        return;
    }

    tagDisplay.textContent = tag;
    emailInput.value = email;
    emailInput.focus();

    modal.style.display = 'flex';
}

/**
 * Close invitation modal
 */
function closeInvitationModal() {
    const modal = document.getElementById('invitation-modal-overlay');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Send invitation to connect
 */
async function sendInvitation() {
    const modal = document.getElementById('invitation-modal-overlay');
    const emailInput = document.getElementById('invitation-email');
    const tagDisplay = document.getElementById('invitation-tag-display');

    if (!modal || !emailInput || !tagDisplay) {
        console.error('Invitation modal elements not found');
        return;
    }

    const email = emailInput.value.trim();
    const tag = tagDisplay.textContent;

    if (!email) {
        showNotification('Please enter an email address', 'error');
        return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/invitations/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                tag: tag,
                task_id: editTaskId,
                message: `You've been invited to collaborate on tasks`
            })
        });

        const result = await response.json();

        if (result.success) {
            // Add the tag to current tags (as pending)
            if (!currentTags.includes(tag)) {
                currentTags.push(tag);
                renderTags();
            }
            closeInvitationModal();
            showNotification(`Invitation sent to ${email}. They'll need to accept to connect.`, 'success');
        } else {
            showNotification(result.message || 'Failed to send invitation', 'error');
        }
    } catch (error) {
        console.error('Error sending invitation:', error);
        // For demo mode, simulate success
        if (!currentTags.includes(tag)) {
            currentTags.push(tag);
            renderTags();
        }
        closeInvitationModal();
        showNotification(`Invitation sent to ${email} (demo mode)`, 'success');
    }
}

/**
 * Load connected accounts for autocomplete
 */
async function loadConnectedAccounts() {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/connected-accounts`);
        const result = await response.json();

        if (result.success) {
            // Transform account data to tag format
            connectedAccounts = (result.accounts || []).map(account => ({
                tag: `@${account.tag_name || account.name}`,
                email: account.email,
                name: account.name,
                avatar: account.avatar || account.name.substring(0, 2).toUpperCase(),
                id: account.id
            }));
        }
    } catch (error) {
        console.error('Error loading connected accounts:', error);
        // Use demo data for testing
        connectedAccounts = [
            { tag: '@john', email: 'john@example.com', name: 'John Doe', avatar: 'JD', id: '1' },
            { tag: '@jane', email: 'jane@example.com', name: 'Jane Smith', avatar: 'JS', id: '2' },
            { tag: '@bob', email: 'bob@example.com', name: 'Bob Wilson', avatar: 'BW', id: '3' }
        ];
    }
}

/**
 * Load pending invitations
 */
async function loadPendingInvitations() {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/invitations/pending`);
        const result = await response.json();

        if (result.success) {
            pendingInvitations = result.invitations || [];
        }
    } catch (error) {
        console.error('Error loading pending invitations:', error);
        pendingInvitations = [];
    }
}

/**
 * Check for invitation acceptance in URL
 */
function checkInvitationAcceptance() {
    const urlParams = new URLSearchParams(window.location.search);
    const invitationToken = urlParams.get('invitation');
    const accepted = urlParams.get('accepted');
    const fromUser = urlParams.get('from');

    if (invitationToken && accepted === 'true' && fromUser) {
        // Invitation was accepted
        const tag = `@${fromUser.split('@')[0]}`;
        
        // Show success notification
        showNotification(`You're now connected with ${tag}!`, 'success');
        
        // Add the tag to current tags if not already present
        if (!currentTags.includes(tag)) {
            currentTags.push(tag);
            renderTags();
        }
        
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

/**
 * Get existing hashtags from the system
 */
function getExistingHashtags() {
    // This could be loaded from the server
    // For now, return some common hashtags
    return [
        '#work', '#personal', '#urgent', '#important', '#later',
        '#someday', '#delegate', '#waiting', '#reference'
    ];
}

/**
 * Load task data for edit mode
 */
async function loadTaskData(taskId) {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/tasks/${taskId}`);
        const result = await response.json();

        if (result.id) {
            // Populate form fields
            document.getElementById('task-title').value = result.title || '';
            document.getElementById('task-notes').value = result.description || '';
            document.getElementById('task-due-date').value = result.due || '';
            document.getElementById('task-priority').value = result.priority || 'none';
            document.getElementById('task-status').value = result.status || 'pending';

            // Set priority button
            const priorityButtons = document.querySelectorAll('.priority-btn');
            priorityButtons.forEach(btn => {
                if (btn.dataset.priority === result.priority) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // Load tags
            if (result.tags && Array.isArray(result.tags)) {
                currentTags = result.tags;
                renderTags();
            }

            // Load completion status
            if (result.completion && Object.keys(result.completion).length > 0) {
                renderCompletionStatus(result.completion);
            } else if (result.account_tags && result.account_tags.length > 0) {
                // Load completion status from API
                const completionStatus = await getTaskCompletionStatus(taskId);
                renderCompletionStatus(completionStatus);
            }

            // Update form title
            document.getElementById('task-modal-title').innerHTML = '<i class="fas fa-edit"></i> Edit Task';
            document.getElementById('task-submit-btn').innerHTML = '<i class="fas fa-save"></i> Save Changes';
        }
    } catch (error) {
        console.error('Error loading task data:', error);
    }
}

/**
 * Set up form submission
 */
function setupFormSubmission() {
    const form = document.getElementById('task-form');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Gather form data
        const formData = {
            title: document.getElementById('task-title').value.trim(),
            notes: document.getElementById('task-notes').value.trim(),
            due_date: document.getElementById('task-due-date').value || null,
            priority: document.getElementById('task-priority').value,
            status: document.getElementById('task-status').value,
            tags: currentTags,
            account_id: document.getElementById('task-account-id')?.value || 'Work',
            task_list_id: document.getElementById('task-list-id')?.value || ''
        };

        // Validate required fields
        if (!formData.title) {
            showNotification('Task title is required', 'error');
            return;
        }

        if (!formData.task_list_id) {
            showNotification('Please select a task list', 'error');
            return;
        }

        try {
            const url = isEditMode ? `/api/tasks/${editTaskId}` : '/api/tasks/create';
            const method = isEditMode ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                showNotification(isEditMode ? 'Task updated successfully' : 'Task created successfully', 'success');
                closeTaskModal();

                // Refresh dashboard if needed
                if (typeof refreshDashboard === 'function') {
                    refreshDashboard();
                }
            } else {
                showNotification(result.message || 'Failed to save task', 'error');
            }
        } catch (error) {
            console.error('Error saving task:', error);
            showNotification('Error saving task', 'error');
        }
    });
}

/**
 * Close task modal
 */
function closeTaskModal() {
    const modal = document.getElementById('task-modal-overlay');
    if (modal) {
        modal.style.display = 'none';
    }

    // Reset form
    const form = document.getElementById('task-form');
    if (form) {
        form.reset();
    }

    // Reset state
    currentTags = [];
    renderTags();

    // Reset edit mode
    isEditMode = false;
    editTaskId = null;

    // Close invitation modal if open
    closeInvitationModal();

    // Redirect to dashboard or close window
    if (window.opener) {
        window.close();
    } else {
        window.location.href = '/dashboard';
    }
}

/**
 * Check URL for task_id parameter (for sharing scenarios)
 */
function checkUrlForTaskId() {
    const urlParams = new URLSearchParams(window.location.search);
    const taskId = urlParams.get('task_id');

    if (taskId) {
        // Load shared task data
        loadTaskData(taskId);
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) {
        // Create container if it doesn't exist
        const newContainer = document.createElement('div');
        newContainer.id = 'notification-container';
        newContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10000; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(newContainer);
    }

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = 'padding: 12px 20px; border-radius: 8px; color: white; font-size: 14px; animation: slideIn 0.3s ease;';
    notification.style.backgroundColor = type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6';
    notification.textContent = message;

    document.getElementById('notification-container').appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Task Completion Tracking
// ============================================

/**
 * Mark task as complete for current user
 */
async function markTaskComplete(taskId) {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/tasks/${taskId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: getCurrentUserId()
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('Task marked as complete', 'success');
            return true;
        } else {
            showNotification(result.message || 'Failed to mark task complete', 'error');
            return false;
        }
    } catch (error) {
        console.error('Error marking task complete:', error);
        // Demo mode: simulate success
        showNotification('Task marked as complete (demo mode)', 'success');
        return true;
    }
}

/**
 * Get completion status for all users on a task
 */
async function getTaskCompletionStatus(taskId) {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/tasks/${taskId}/completion`);
        const result = await response.json();

        if (result.success) {
            return result.completion || {};
        }
        return {};
    } catch (error) {
        console.error('Error getting completion status:', error);
        // Demo mode: return mock data
        return {
            '@john': { completed: true, at: new Date().toISOString() },
            '@jane': { completed: false, at: null }
        };
    }
}

/**
 * Get current user ID
 */
function getCurrentUserId() {
    // Try to get from localStorage
    const profile = localStorage.getItem('gtasks_user_profile');
    if (profile) {
        const user = JSON.parse(profile);
        return user.user_id || user.email;
    }
    
    // Try to get from page data
    const userIdElement = document.getElementById('current-user-id');
    if (userIdElement) {
        return userIdElement.value;
    }
    
    // Generate demo user ID
    return 'demo12345';
}

/**
 * Render completion status for task
 */
function renderCompletionStatus(completionStatus) {
    const container = document.getElementById('task-completion-status');
    const group = document.getElementById('completion-status-group');
    if (!container) return;

    const entries = Object.entries(completionStatus);
    
    if (entries.length === 0) {
        group.style.display = 'none';
        return;
    }

    group.style.display = 'block';
    container.innerHTML = `
        <div class="completion-status-list">
            ${entries.map(([tag, status]) => `
                <div class="completion-item ${status.completed ? 'completed' : 'pending'}">
                    <span class="completion-tag">${escapeHtml(tag)}</span>
                    <span class="completion-icon">
                        ${status.completed ? '<i class="fas fa-check-circle" style="color: #10b981;"></i>' : '<i class="fas fa-clock" style="color: #f59e0b;"></i>'}
                    </span>
                    <span class="completion-time">
                        ${status.completed ? `Completed ${formatDate(status.at)}` : 'Pending'}
                    </span>
                </div>
            `).join('')}
        </div>
    `;
}

/**
 * Mark current user as complete
 */
async function markCurrentUserComplete() {
    if (!editTaskId) {
        showNotification('Please save the task first', 'error');
        return;
    }
    
    const success = await markTaskComplete(editTaskId);
    if (success) {
        // Refresh completion status
        const completionStatus = await getTaskCompletionStatus(editTaskId);
        renderCompletionStatus(completionStatus);
    }
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Make functions globally available
window.removeTag = removeTag;
window.closeTaskModal = closeTaskModal;
window.closeInvitationModal = closeInvitationModal;
window.sendInvitation = sendInvitation;
window.showNotification = showNotification;
window.markTaskComplete = markTaskComplete;
window.getTaskCompletionStatus = getTaskCompletionStatus;
window.markCurrentUserComplete = markCurrentUserComplete;
