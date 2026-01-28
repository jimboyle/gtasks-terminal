/**
 * edit_file Task Modal Component
 * Handles opening and managing the edit task modal
 */

// Store reference to the current task being edited
let currentEditTask = null;

/**
 * Get the task from the dashboard state
 * @param {string} taskId - Task ID
 * @returns {Object|null} - Task object or null if not found
 */
function getTaskById(taskId) {
    // Try to get from window.dashboardTasks if available
    if (window.dashboardTasks) {
        const task = window.dashboardTasks.find(t => t.id === taskId);
        if (task) return task;
    }
    
    // Try to get from dashboard_state via API
    // This is a fallback that will require fetching
    return null;
}

/**
 * Open the edit task modal
 * @param {string} taskId - Task ID to edit
 */
export async function openEditTaskModal(taskId) {
    console.log('[edit_file Modal] Opening edit modal for task:', taskId);
    
    // Get the task
    const task = getTaskById(taskId);
    
    if (!task) {
        console.error('[edit_file Modal] Task not found:', taskId);
        alert('Task not found. Please refresh the page and try again.');
        return;
    }
    
    currentEditTask = task;
    
    // Create modal HTML
    const modalHtml = createEditModalHtml(task);
    
    // Remove any existing modal
    const existingModal = document.querySelector('.edit-modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Add event listeners
    setupEditModalListeners(task);
}

/**
 * Create the edit modal HTML
 * @param {Object} task - Task object
 * @returns {string} - HTML string
 */
function createEditModalHtml(task) {
    const isDarkMode = document.documentElement.classList.contains('dark-mode') || 
                       document.body.classList.contains('dark-mode');
    
    // Format due date for input (YYYY-MM-DD)
    let dueDateValue = '';
    if (task.due) {
        try {
            const dueDate = new Date(task.due);
            dueDateValue = dueDate.toISOString().split('T')[0];
        } catch (e) {
            // Invalid date, leave empty
        }
    }
    
    // Priority options
    const priorityOptions = ['none', 'low', 'medium', 'high', 'critical'];
    const currentPriority = task.calculated_priority || task.priority || 'none';
    
    // Status options
    const statusOptions = ['pending', 'in_progress', 'completed'];
    const currentStatus = task.status || 'pending';
    
    return `
        <div class="edit-modal-overlay" id="edit-modal-overlay">
            <div class="edit-modal">
                <div class="edit-modal-header">
                    <h3 class="edit-modal-title">Edit Task</h3>
                    <button class="edit-modal-close" onclick="closeEditModal()">&times;</button>
                </div>
                <div class="edit-modal-body">
                    <form id="edit-task-form">
                        <input type="hidden" name="task_id" value="${task.id}">
                        
                        <div class="edit-form-group">
                            <label class="edit-form-label" for="edit-title">Title *</label>
                            <input type="text" 
                                   id="edit-title" 
                                   name="title" 
                                   class="edit-form-input" 
                                   value="${escapeHtml(task.title || '')}" 
                                   required
                                   maxlength="200">
                        </div>
                        
                        <div class="edit-form-group">
                            <label class="edit-form-label" for="edit-description">Description</label>
                            <textarea id="edit-description" 
                                      name="description" 
                                      class="edit-form-textarea"
                                      placeholder="Add a description...">${escapeHtml(task.description || task.notes || '')}</textarea>
                        </div>
                        
                        <div class="edit-form-group">
                            <label class="edit-form-label" for="edit-due">Due Date</label>
                            <input type="date" 
                                   id="edit-due" 
                                   name="due" 
                                   class="edit-form-input"
                                   value="${dueDateValue}">
                        </div>
                        
                        <div class="edit-form-group">
                            <label class="edit-form-label" for="edit-priority">Priority</label>
                            <select id="edit-priority" name="priority" class="edit-form-select">
                                ${priorityOptions.map(p => 
                                    `<option value="${p}" ${p === currentPriority ? 'selected' : ''}>${p.charAt(0).toUpperCase() + p.slice(1)}</option>`
                                ).join('')}
                            </select>
                        </div>
                        
                        <div class="edit-form-group">
                            <label class="edit-form-label" for="edit-status">Status</label>
                            <select id="edit-status" name="status" class="edit-form-select">
                                ${statusOptions.map(s => 
                                    `<option value="${s}" ${s === currentStatus ? 'selected' : ''}>${formatStatus(s)}</option>`
                                ).join('')}
                            </select>
                        </div>
                    </form>
                </div>
                <div class="edit-modal-footer">
                    <button class="edit-btn-cancel" onclick="closeEditModal()">Cancel</button>
                    <button class="edit-btn-save" id="edit-btn-save">Save Changes</button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Setup event listeners for the edit modal
 * @param {Object} task - Original task object
 */
function setupEditModalListeners(task) {
    const overlay = document.getElementById('edit-modal-overlay');
    const saveBtn = document.getElementById('edit-btn-save');
    const form = document.getElementById('edit-task-form');
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeEditModal();
        }
    });
    
    // Close on Escape key
    document.addEventListener('keydown', handleEscapeKey);
    
    // Save button click
    saveBtn.addEventListener('click', () => handleSaveTask(task));
    
    // Form submit (Enter key in input fields)
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        handleSaveTask(task);
    });
}

/**
 * Handle escape key press to close modal
 * @param {KeyboardEvent} e
 */
function handleEscapeKey(e) {
    if (e.key === 'Escape') {
        closeEditModal();
    }
}

/**
 * Close the edit modal
 */
export function closeEditModal() {
    const overlay = document.querySelector('.edit-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
    
    // Remove escape key listener
    document.removeEventListener('keydown', handleEscapeKey);
    
    currentEditTask = null;
}

/**
 * Handle saving the task
 * @param {Object} originalTask - Original task object
 */
async function handleSaveTask(originalTask) {
    const saveBtn = document.getElementById('edit-btn-save');
    const form = document.getElementById('edit-task-form');
    
    // Get form data
    const formData = new FormData(form);
    const updates = {
        title: formData.get('title').trim(),
        description: formData.get('description').trim(),
        due: formData.get('due') || null,
        priority: formData.get('priority'),
        status: formData.get('status')
    };
    
    // Validate
    if (!updates.title) {
        alert('Title is required');
        return;
    }
    
    // Check if there are any changes
    const hasChanges = (
        updates.title !== (originalTask.title || '') ||
        updates.description !== (originalTask.description || originalTask.notes || '') ||
        updates.due !== (originalTask.due || '') ||
        updates.priority !== (originalTask.calculated_priority || originalTask.priority || 'none') ||
        updates.status !== (originalTask.status || 'pending')
    );
    
    if (!hasChanges) {
        console.log('[edit_file Modal] No changes detected');
        closeEditModal();
        return;
    }
    
    // Show loading state
    saveBtn.textContent = 'Saving...';
    saveBtn.disabled = true;
    
    try {
        // Call the updateTask function
        if (window.updateTask) {
            await window.updateTask(originalTask.id, updates, {
                onSuccess: (data) => {
                    console.log('[edit_file Modal] ✅ Task updated successfully');
                    closeEditModal();
                    
                    // Refresh the task list if available
                    if (window.refreshTasks) {
                        window.refreshTasks();
                    } else if (window.loadDashboardData) {
                        window.loadDashboardData();
                    }
                    
                    // Show success notification
                    showNotification('Task updated successfully', 'success');
                },
                onError: (error) => {
                    console.error('[edit_file Modal] ❌ Failed to update task:', error);
                    showNotification('Failed to update task: ' + error, 'error');
                    
                    // Reset button
                    saveBtn.textContent = 'Save Changes';
                    saveBtn.disabled = false;
                }
            });
        } else {
            // Fallback to direct API call
            const response = await fetch(`/api/tasks/${originalTask.id}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updates)
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[edit_file Modal] ✅ Task updated successfully');
                closeEditModal();
                
                // Refresh the task list if available
                if (window.refreshTasks) {
                    window.refreshTasks();
                } else if (window.loadDashboardData) {
                    window.loadDashboardData();
                }
                
                showNotification('Task updated successfully', 'success');
            } else {
                throw new Error(data.message);
            }
        }
    } catch (error) {
        console.error('[edit_file Modal] ❌ Error saving task:', error);
        showNotification('Error saving task: ' + error.message, 'error');
        
        // Reset button
        saveBtn.textContent = 'Save Changes';
        saveBtn.disabled = false;
    }
}

/**
 * Show a notification
 * @param {string} message - Message to display
 * @param {string} type - Notification type ('success' or 'error')
 */
function showNotification(message, type = 'success') {
    // Check if there's an existing notification system
    if (window.showNotification) {
        window.showNotification(message, type);
        return;
    }
    
    // Simple alert fallback
    console.log(`[Notification] ${type}: ${message}`);
    
    // Create a temporary notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-size: 14px;
        font-weight: 500;
        z-index: 2000;
        animation: slideUp 0.3s ease;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(10px)';
        notification.style.transition = 'all 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format status for display
 * @param {string} status - Status value
 * @returns {string} - Formatted status
 */
function formatStatus(status) {
    const statusMap = {
        'pending': 'Pending',
        'in_progress': 'In Progress',
        'completed': 'Completed'
    };
    return statusMap[status] || status;
}

// Export for global access
window.openEditTaskModal = openEditTaskModal;
window.closeEditModal = closeEditModal;
