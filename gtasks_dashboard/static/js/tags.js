/**
 * Tags Management JavaScript
 * Handles tag CRUD operations, filtering, and task management
 */

// Import TaskViewManager for enhanced task display
import { TaskViewManager, createIntegratedTaskView } from './task-view-manager.js';

// Global state
let allTags = [];
let filteredTags = [];
let currentTagId = null;
let currentTagTasks = []; // Store tasks for filtering
let tagTasksViewManager = null; // TaskViewManager instance for tag tasks modal

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    initializeTagsPage();
});

/**
 * Initialize the tags page
 */
async function initializeTagsPage() {
    // Set up event listeners
    setupEventListeners();

    // Load accounts first (needed for account selector)
    await loadAccounts();

    // Load tags
    await loadTags();

    // Load statistics
    updateStats();
}

/**
 * Load accounts from API
 */
async function loadAccounts() {
    const selector = document.getElementById('account-selector');
    if (!selector) return;

    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/data`);
        const data = await response.json();

        if (data.accounts && data.accounts.length > 0) {
            const currentAccount = data.current_account;
            selector.innerHTML = data.accounts.map(acc =>
                `<option value="${acc.id}" ${acc.id === currentAccount ? 'selected' : ''}>${acc.name}</option>`
            ).join('');
        } else {
            // Fallback to demo accounts
            loadDemoAccounts();
        }
    } catch (error) {
        console.error('Error loading accounts:', error);
        // Fallback to demo accounts if API fails
        loadDemoAccounts();
    }
}

/**
 * Load demo accounts for testing
 */
function loadDemoAccounts() {
    const selector = document.getElementById('account-selector');
    if (!selector) return;

    const demoAccounts = [
        { id: 'default', name: 'Default Account' },
        { id: 'work', name: 'Work Account' },
        { id: 'personal', name: 'Personal Account' }
    ];

    selector.innerHTML = demoAccounts.map(acc =>
        `<option value="${acc.id}" ${acc.id === 'default' ? 'selected' : ''}>${acc.name}</option>`
    ).join('');
}

/**
 * Switch account
 */
async function switchAccount(accountId) {
    if (!accountId) return;

    const basePath = window.GTASKS_BASE_PATH || '';
    try {
        const response = await fetch(`${basePath}/api/accounts/${accountId}/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            // Reload tags for the new account
            await loadTags();
            showNotification('Account switched successfully', 'success');
        } else {
            showNotification('Failed to switch account', 'error');
        }
    } catch (error) {
        console.error('Error switching account:', error);
        showNotification('Error switching account', 'error');
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Color picker
    const colorPicker = document.getElementById('color-picker');
    if (colorPicker) {
        colorPicker.addEventListener('click', function (e) {
            const colorOption = e.target.closest('.color-option');
            if (colorOption) {
                // Remove active class from all
                colorPicker.querySelectorAll('.color-option').forEach(opt => {
                    opt.classList.remove('active');
                });
                // Add active class to clicked
                colorOption.classList.add('active');
                // Update hidden input
                document.getElementById('tag-color').value = colorOption.dataset.color;
            }
        });
    }

    // Form submission
    const tagForm = document.getElementById('tag-form');
    if (tagForm) {
        tagForm.addEventListener('submit', handleTagSubmit);
    }

    // Delete confirmation
    const deleteBtn = document.getElementById('confirm-delete-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', handleDeleteConfirm);
    }
}

/**
 * Load all tags from the API
 */
async function loadTags() {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/tags`);
        const result = await response.json();

        if (result.success) {
            // Transform tags data
            allTags = transformTagsData(result.tags || []);
            filteredTags = [...allTags];
            renderTags();
            updateStats();
        } else {
            showNotification('Failed to load tags', 'error');
        }
    } catch (error) {
        console.error('Error loading tags:', error);
        // Use demo data if API fails
        loadDemoTags();
    }
}

/**
 * Transform tags data from API format to internal format
 */
function transformTagsData(tagsList) {
    if (!Array.isArray(tagsList)) return [];

    return tagsList.map(tag => {
        const name = tag.name || '';
        const isAccount = tag.is_account || (tag.type === 'account') || name.startsWith('@');

        // Ensure name has correct prefix for display if not present
        let displayName = name;
        if (name.startsWith('@') || name.startsWith('#')) {
            displayName = name.substring(1);
        }

        const formattedName = isAccount ?
            (name.startsWith('@') ? name : `@${name}`) :
            (name.startsWith('#') ? name : `#${name}`);

        return {
            id: tag.id || name,
            name: formattedName,
            displayName: displayName,
            type: isAccount ? 'account' : 'regular',
            color: tag.color || (isAccount ? 'blue' : 'green'),
            description: tag.description || '',
            usage: tag.usage_count || tag.task_count || 0,
            email: tag.email || ''
        };
    });
}

/**
 * Load demo tags for testing
 */
function loadDemoTags() {
    allTags = [
        { id: '1', name: '@john', displayName: 'john', type: 'account', color: 'blue', description: 'John\'s account', usage: 5, email: 'john@example.com' },
        { id: '2', name: '@jane', displayName: 'jane', type: 'account', color: 'blue', description: 'Jane\'s account', usage: 3, email: 'jane@example.com' },
        { id: '3', name: '#work', displayName: 'work', type: 'regular', color: 'blue', description: 'Work-related tasks', usage: 12 },
        { id: '4', name: '#personal', displayName: 'personal', type: 'regular', color: 'green', description: 'Personal tasks', usage: 8 },
        { id: '5', name: '#urgent', displayName: 'urgent', type: 'regular', color: 'red', description: 'Urgent tasks', usage: 4 },
        { id: '6', name: '#important', displayName: 'important', type: 'regular', color: 'yellow', description: 'Important tasks', usage: 6 },
        { id: '7', name: '#later', displayName: 'later', type: 'regular', color: 'purple', description: 'Tasks for later', usage: 2 }
    ];
    filteredTags = [...allTags];
    renderTags();
    updateStats();
}

/**
 * Render tags to the grid
 */
function renderTags() {
    const grid = document.getElementById('tags-grid');
    const emptyState = document.getElementById('empty-state');

    if (!grid) return;

    if (filteredTags.length === 0) {
        grid.style.display = 'none';
        if (emptyState) {
            emptyState.style.display = 'block';
        }
        return;
    }

    grid.style.display = 'grid';
    if (emptyState) {
        emptyState.style.display = 'none';
    }

    grid.innerHTML = filteredTags.map(tag => createTagCard(tag)).join('');
}

/**
 * Create tag card HTML
 */
/**
 * Create tag card HTML
 */
function createTagCard(tag) {
    const colorClass = tag.color || 'blue';
    const colorHex = getColorHex(colorClass);
    // Use data attributes to avoid quoting issues in inline onclick handlers
    const safeTagId = escapeHtml(tag.id);

    return `
        <div class="tag-card" data-tag-id="${safeTagId}">
            <div class="tag-card-header">
                <div class="tag-icon ${tag.type === 'account' ? 'account-tag' : 'regular-tag'}" style="background: ${colorHex}20; color: ${colorHex};">
                    <i class="fas ${tag.type === 'account' ? 'fa-user-tag' : 'fa-tag'}"></i>
                </div>
                <div class="tag-info">
                    <h3 class="tag-name">${escapeHtml(tag.name)}</h3>
                    ${tag.description ? `<p class="tag-description">${escapeHtml(tag.description)}</p>` : ''}
                </div>
            </div>
            <div class="tag-meta">
                <div class="tag-usage">
                    <i class="fas fa-tasks"></i>
                    <span>${tag.usage || 0} tasks</span>
                </div>
                <div class="tag-actions">
                    <button class="btn-view" onclick="viewTagTasks(this.getAttribute('data-id'))" data-id="${safeTagId}" title="View Tasks">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-edit" onclick="openEditTagModal(this.getAttribute('data-id'))" data-id="${safeTagId}" title="Edit Tag">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-delete" onclick="openDeleteModal(this.getAttribute('data-id'))" data-id="${safeTagId}" title="Delete Tag">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}


/**
 * Get color hex value
 */
function getColorHex(colorName) {
    const colors = {
        blue: '#3b82f6',
        green: '#10b981',
        yellow: '#f59e0b',
        red: '#ef4444',
        purple: '#8b5cf6',
        pink: '#ec4899',
        gray: '#6b7280'
    };
    return colors[colorName] || colors.blue;
}

/**
 * Update statistics
 */
function updateStats() {
    const totalTags = allTags.length;
    const accountTags = allTags.filter(t => t.type === 'account').length;
    const regularTags = allTags.filter(t => t.type === 'regular').length;

    // Update stats only if elements exist (they exist in tags.html but not dashboard.html)
    const totalTagsEl = document.getElementById('total-tags');
    const accountTagsEl = document.getElementById('account-tags');
    const regularTagsEl = document.getElementById('regular-tags');

    if (totalTagsEl) totalTagsEl.textContent = totalTags;
    if (accountTagsEl) accountTagsEl.textContent = accountTags;
    if (regularTagsEl) regularTagsEl.textContent = regularTags;
}

/**
 * Filter tags by search term and type
 */
function filterTags() {
    const searchTerm = document.getElementById('tag-search').value.toLowerCase().trim();
    const typeFilter = document.getElementById('tag-type-filter').value;

    filteredTags = allTags.filter(tag => {
        // Search filter
        const matchesSearch = !searchTerm ||
            tag.name.toLowerCase().includes(searchTerm) ||
            (tag.description && tag.description.toLowerCase().includes(searchTerm));

        // Type filter
        const matchesType = typeFilter === 'all' || tag.type === typeFilter;

        return matchesSearch && matchesType;
    });

    sortTags();
    renderTags();
}

/**
 * Sort tags
 */
function sortTags() {
    const sortBy = document.getElementById('tag-sort').value;

    filteredTags.sort((a, b) => {
        switch (sortBy) {
            case 'name':
                return a.name.localeCompare(b.name);
            case 'usage':
                return (b.usage || 0) - (a.usage || 0);
            case 'recent':
                return 0; // Would need timestamp for this
            default:
                return 0;
        }
    });

    renderTags();
}

/**
 * Open add tag modal
 */
function openAddTagModal() {
    currentTagId = null;

    // Reset form
    document.getElementById('tag-form').reset();
    document.getElementById('tag-modal-title').innerHTML = '<i class="fas fa-plus-circle"></i> Add New Tag';
    document.getElementById('tag-submit-btn').innerHTML = '<i class="fas fa-plus"></i> Create Tag';

    // Reset color picker
    document.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('active'));
    document.querySelector('.color-option[data-color="blue"]').classList.add('active');
    document.getElementById('tag-color').value = 'blue';

    // Show modal
    const overlay = document.getElementById('tag-modal-overlay');
    overlay.style.display = 'flex';
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

/**
 * Open edit tag modal
 */
async function openEditTagModal(tagId) {
    const tag = allTags.find(t => t.id === tagId);
    if (!tag) return;

    currentTagId = tagId;

    // Populate form
    document.getElementById('tag-id').value = tagId;
    document.getElementById('tag-name').value = tag.displayName;
    document.getElementById('tag-description').value = tag.description || '';

    // Set tag type
    const typeRadios = document.getElementsByName('tag_type');
    typeRadios.forEach(radio => {
        radio.checked = radio.value === tag.type;
    });

    // Set color
    document.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('active'));
    const colorOption = document.querySelector(`.color-option[data-color="${tag.color}"]`);
    if (colorOption) {
        colorOption.classList.add('active');
    }
    document.getElementById('tag-color').value = tag.color || 'blue';

    // Update modal title and button
    document.getElementById('tag-modal-title').innerHTML = '<i class="fas fa-edit"></i> Edit Tag';
    document.getElementById('tag-submit-btn').innerHTML = '<i class="fas fa-save"></i> Save Changes';

    // Show modal
    const overlay = document.getElementById('tag-modal-overlay');
    overlay.style.display = 'flex';
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

/**
 * Close tag modal
 */
function closeTagModal() {
    const overlay = document.getElementById('tag-modal-overlay');
    overlay.classList.remove('active');
    // Wait for transition to finish before hiding
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300);
    currentTagId = null;
}

/**
 * Handle tag form submission
 */
async function handleTagSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const tagData = {
        name: formData.get('name').trim(),
        type: formData.get('tag_type'),
        color: formData.get('color') || 'blue',
        description: formData.get('description').trim()
    };

    if (!tagData.name) {
        showNotification('Tag name is required', 'error');
        return;
    }

    // Add prefix based on type
    const fullName = tagData.type === 'account' ? `@${tagData.name}` : `#${tagData.name}`;

    try {
        if (currentTagId) {
            // Update existing tag
            await updateTag(currentTagId, tagData);
        } else {
            // Create new tag
            await createTag(tagData, fullName);
        }

        closeTagModal();
        await loadTags();
        showNotification(currentTagId ? 'Tag updated successfully' : 'Tag created successfully', 'success');
    } catch (error) {
        console.error('Error saving tag:', error);
        showNotification('Failed to save tag', 'error');
    }
}

/**
 * Create a new tag
 */
async function createTag(tagData, fullName) {
    // In a real app, this would call the API
    // For demo, we just add to local state
    const newTag = {
        id: `tag_${Date.now()}`,
        name: fullName,
        displayName: tagData.name,
        type: tagData.type,
        color: tagData.color,
        description: tagData.description,
        usage: 0
    };

    allTags.push(newTag);
    filteredTags = [...allTags];

    // Simulate API call
    return new Promise(resolve => setTimeout(resolve, 300));
}

/**
 * Update an existing tag
 */
async function updateTag(tagId, tagData) {
    const tagIndex = allTags.findIndex(t => t.id === tagId);
    if (tagIndex === -1) throw new Error('Tag not found');

    const fullName = tagData.type === 'account' ? `@${tagData.name}` : `#${tagData.name}`;

    allTags[tagIndex] = {
        ...allTags[tagIndex],
        name: fullName,
        displayName: tagData.name,
        type: tagData.type,
        color: tagData.color,
        description: tagData.description
    };

    filteredTags = [...allTags];

    // Simulate API call
    return new Promise(resolve => setTimeout(resolve, 300));
}

/**
 * Open delete confirmation modal
 */
async function openDeleteModal(tagId) {
    const tag = allTags.find(t => t.id === tagId);
    if (!tag) return;

    currentTagId = tagId;

    // Show tag preview
    const preview = document.getElementById('delete-tag-preview');
    preview.innerHTML = `
        <div class="tag-card" style="margin: 0;">
            <div class="tag-card-header">
                <div class="tag-icon ${tag.type === 'account' ? 'account-tag' : 'regular-tag'}">
                    <i class="fas ${tag.type === 'account' ? 'fa-user-tag' : 'fa-tag'}"></i>
                </div>
                <div class="tag-info">
                    <h3 class="tag-name">${escapeHtml(tag.name)}</h3>
                    ${tag.description ? `<p class="tag-description">${escapeHtml(tag.description)}</p>` : ''}
                </div>
            </div>
        </div>
    `;

    // Update usage count
    document.getElementById('tag-usage-count').textContent = tag.usage || 0;

    // Show modal
    // Show modal
    const overlay = document.getElementById('delete-modal-overlay');
    overlay.style.display = 'flex';
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

/**
 * Close delete modal
 */
function closeDeleteModal() {
    const overlay = document.getElementById('delete-modal-overlay');
    overlay.classList.remove('active');
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300);
    currentTagId = null;
}

/**
 * Handle delete confirmation
 */
async function handleDeleteConfirm() {
    if (!currentTagId) return;

    try {
        // Remove tag from local state
        allTags = allTags.filter(t => t.id !== currentTagId);
        filteredTags = [...allTags];

        closeDeleteModal();
        renderTags();
        updateStats();
        showNotification('Tag deleted successfully', 'success');
    } catch (error) {
        console.error('Error deleting tag:', error);
        showNotification('Failed to delete tag', 'error');
    }
}

/**
 * View tasks with a specific tag
 */
async function viewTagTasks(tagId) {
    const tag = allTags.find(t => t.id === tagId);
    if (!tag) return;

    // Update modal title
    document.getElementById('view-tag-name').textContent = tag.name;

    // Get the tasks container
    const tasksContainer = document.getElementById('tag-tasks-list');
    
    // Show loading state
    tasksContainer.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #6b7280;">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
            <p>Loading tasks...</p>
        </div>
    `;

    try {
        // Get tasks from API or use demo data
        currentTagTasks = await loadTasksForTag(tag.name);
        
        // Destroy existing view manager if any
        if (tagTasksViewManager) {
            tagTasksViewManager.destroy();
        }
        
        // Create new TaskViewManager using integrated mode (with external filters)
        tagTasksViewManager = createIntegratedTaskView('tag-tasks-list', currentTagTasks, {
            search: 'tag-task-search-filter',
            status: 'tag-task-status-filter',
            priority: 'tag-task-priority-filter',
            dateField: 'tag-task-date-field',
            dateStart: 'tag-task-date-start',
            dateEnd: 'tag-task-date-end',
            sortField: 'tag-task-sort-field',
            sortOrder: 'tag-task-sort-order',
            clear: 'tag-task-clear-filters'
        });
        
        // Set initial filters
        tagTasksViewManager.setFilters({
            sortField: 'due',
            sortOrder: 'desc',
            dateField: 'due'
        });
        
        // Store reference globally for external access
        window.currentTagTasksViewManager = tagTasksViewManager;
        
    } catch (error) {
        console.error('Error loading tasks:', error);
        tasksContainer.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: #ef4444;">
                <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                <p>Failed to load tasks</p>
                <p style="font-size: 0.875rem; color: #6b7280;">${error.message}</p>
            </div>
        `;
    }

    const overlay = document.getElementById('tasks-modal-overlay');
    overlay.style.display = 'flex';
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

/**
 * Refresh the tag tasks view (useful after task updates)
 */
function refreshTagTasks() {
    if (tagTasksViewManager) {
        tagTasksViewManager.refresh();
    }
}

/**
 * Filter tasks in the modal (now delegates to TaskViewManager)
 */
function filterTagTasks() {
    // Get all filter values
    const searchTerm = document.getElementById('tag-task-search-filter').value.toLowerCase().trim();
    const statusFilter = document.getElementById('tag-task-status-filter').value;
    const priorityFilter = document.getElementById('tag-task-priority-filter').value;
    const dateField = document.getElementById('tag-task-date-field').value;
    const dateStart = document.getElementById('tag-task-date-start').value;
    const dateEnd = document.getElementById('tag-task-date-end').value;
    const sortField = document.getElementById('tag-task-sort-field').value;
    const sortOrder = document.getElementById('tag-task-sort-order').value;

    // Build filter object
    const filters = {
        search: searchTerm,
        status: statusFilter,
        priority: priorityFilter,
        dateField: dateField,
        dateStart: dateStart,
        dateEnd: dateEnd,
        sortField: sortField,
        sortOrder: sortOrder
    };

    // Use TaskViewManager if available, otherwise fallback to basic filtering
    if (tagTasksViewManager) {
        tagTasksViewManager.setFilters(filters);
    } else {
        // Fallback to basic filtering
        const filteredTasks = currentTagTasks.filter(task => {
            // Search filter
            const matchesSearch = !searchTerm ||
                (task.title && task.title.toLowerCase().includes(searchTerm)) ||
                (task.description && task.description.toLowerCase().includes(searchTerm));

            // Status filter
            const matchesStatus = !statusFilter ||
                (statusFilter === 'completed' && task.completed) ||
                (statusFilter === 'pending' && !task.completed && !task.in_progress) ||
                (statusFilter === 'in_progress' && task.in_progress);

            // Priority filter
            const matchesPriority = !priorityFilter ||
                (task.priority && task.priority.toLowerCase() === priorityFilter);

            return matchesSearch && matchesStatus && matchesPriority;
        });

        // Sort tasks
        filteredTasks.sort((a, b) => {
            let aVal, bVal;
            switch (sortField) {
                case 'due':
                    aVal = a.due ? new Date(a.due).getTime() : 0;
                    bVal = b.due ? new Date(b.due).getTime() : 0;
                    break;
                case 'created_at':
                    aVal = a.created_at ? new Date(a.created_at).getTime() : 0;
                    bVal = b.created_at ? new Date(b.created_at).getTime() : 0;
                    break;
                case 'modified_at':
                    aVal = a.modified_at ? new Date(a.modified_at).getTime() : 0;
                    bVal = b.modified_at ? new Date(b.modified_at).getTime() : 0;
                    break;
                case 'priority':
                    const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
                    aVal = priorityOrder[a.priority?.toLowerCase()] || 0;
                    bVal = priorityOrder[b.priority?.toLowerCase()] || 0;
                    break;
                case 'title':
                    aVal = a.title || '';
                    bVal = b.title || '';
                    break;
                default:
                    aVal = 0;
                    bVal = 0;
            }

            if (sortOrder === 'desc') {
                return aVal > bVal ? -1 : (aVal < bVal ? 1 : 0);
            } else {
                return aVal < bVal ? -1 : (aVal > bVal ? 1 : 0);
            }
        });

        renderTagTasksBasic(filteredTasks);
    }
}

/**
 * Clear all filters in the tag tasks modal
 */
function clearTagTasksFilters() {
    // Clear input fields
    document.getElementById('tag-task-search-filter').value = '';
    document.getElementById('tag-task-status-filter').value = '';
    document.getElementById('tag-task-priority-filter').value = '';
    document.getElementById('tag-task-date-start').value = '';
    document.getElementById('tag-task-date-end').value = '';

    // Reset sort fields
    document.getElementById('tag-task-sort-field').value = 'due';
    document.getElementById('tag-task-sort-order').value = 'desc';

    // Re-apply filters (which will show all tasks)
    filterTagTasks();
}

/**
 * Basic task rendering (fallback when TaskViewManager is not available)
 */
function renderTagTasksBasic(tasks) {
    const tasksList = document.getElementById('tag-tasks-list');
    if (!tasksList) return;

    if (tasks.length === 0) {
        tasksList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-tasks"></i>
                <h3>No tasks found</h3>
            </div>
        `;
    } else {
        tasksList.innerHTML = tasks.map(task => `
            <div class="task-item ${task.completed ? 'completed' : ''}">
                <div class="task-checkbox">
                    <input type="checkbox" ${task.completed ? 'checked' : ''} disabled>
                </div>
                <div class="task-content">
                    <span class="task-title">${escapeHtml(task.title)}</span>
                    ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
                    <div class="task-meta">
                         ${task.due ? `<span class="task-date"><i class="far fa-calendar"></i> ${new Date(task.due).toLocaleDateString()}</span>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }
}

/**
 * Legacy function for backward compatibility
 */
function renderTagTasks(tasks) {
    renderTagTasksBasic(tasks);
}

/**
 * Close tasks modal
 */
function closeTasksModal() {
    const overlay = document.getElementById('tasks-modal-overlay');
    overlay.classList.remove('active');
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300);
    
    // Clean up TaskViewManager instance
    if (tagTasksViewManager) {
        tagTasksViewManager.destroy();
        tagTasksViewManager = null;
    }
}

/**
 * Load tasks for a specific tag
 */
async function loadTasksForTag(tagName) {
    // Strip the # prefix for regular tags before making API call
    // API expects just the tag name without prefix
    const apiTagName = tagName.startsWith('#') ? tagName.substring(1) : tagName;

    // Try to load from API
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/tasks?tag=${encodeURIComponent(apiTagName)}`);
        const result = await response.json();

        if (result.tasks) {
            return result.tasks;
        }
    } catch (error) {
        console.error('Error loading tasks from API:', error);
    }

    // Return demo tasks
    return [
        { id: '1', title: 'Sample task 1', completed: false },
        { id: '2', title: 'Sample task 2', completed: true },
        { id: '3', title: 'Another task', completed: false }
    ];
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) {
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

// Refresh tags from the API
async function refreshTags() {
    try {
        showNotification('Refreshing tags...', 'info');
        const basePath = window.GTASKS_BASE_PATH || '';

        // Use the same endpoint as loadTags() for consistency
        const response = await fetch(`${basePath}/api/tags`);
        const result = await response.json();

        if (result.success) {
            // Transform tags data using the same logic as loadTags()
            allTags = transformTagsData(result.tags || []);
            filteredTags = [...allTags];
            renderTags();
            updateStats();

            // Show message if no tags found
            if (allTags.length === 0) {
                showNotification('No tags found. Import tags from Google Tasks or create new tags.', 'info');
            } else {
                showNotification(`Tags refreshed successfully! Found ${allTags.length} tags.`, 'success');
            }
        } else {
            showNotification('Failed to refresh tags', 'error');
        }
    } catch (error) {
        console.error('Error refreshing tags:', error);
        // Use demo data if API fails
        loadDemoTags();
        showNotification('Using demo tags. No tags found from API.', 'info');
    }
}

// Sync tags with tasks
async function syncTagsWithTasks() {
    try {
        showNotification('Syncing tags with tasks...', 'info');
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/tags/sync`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            showNotification(data.message || 'Tags synced with tasks!', 'success');
            // Refresh tags after sync
            await refreshTags();
        } else {
            showNotification('Failed to sync tags', 'error');
        }
    } catch (error) {
        console.error('Error syncing tags:', error);
        showNotification('Error syncing tags', 'error');
    }
}

// Toggle refresh dropdown menu
function toggleRefreshDropdown() {
    const dropdown = document.getElementById('refresh-dropdown-menu');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

// Click outside listener to close refresh dropdown
document.addEventListener('click', function (event) {
    const refreshDropdown = document.querySelector('.refresh-dropdown');
    const dropdown = document.getElementById('refresh-dropdown-menu');

    if (refreshDropdown && dropdown && !refreshDropdown.contains(event.target)) {
        dropdown.classList.remove('active');
    }
});
window.refreshTags = refreshTags;
window.syncTagsWithTasks = syncTagsWithTasks;
window.toggleRefreshDropdown = toggleRefreshDropdown;

window.filterTagTasks = filterTagTasks;
window.clearTagTasksFilters = clearTagTasksFilters;
window.renderTagTasks = renderTagTasks;

// Export functions to global scope for HTML event handlers
window.viewTagTasks = viewTagTasks;
window.openEditTagModal = openEditTagModal;
window.openDeleteModal = openDeleteModal;
window.openAddTagModal = openAddTagModal;
window.closeTagModal = closeTagModal;
window.closeDeleteModal = closeDeleteModal;
window.closeTasksModal = closeTasksModal;
window.handleTagSubmit = handleTagSubmit;
window.handleDeleteConfirm = handleDeleteConfirm;
window.switchAccount = switchAccount;
window.filterTags = filterTags;
window.sortTags = sortTags;
