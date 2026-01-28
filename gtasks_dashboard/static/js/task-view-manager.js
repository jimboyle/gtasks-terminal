/**
 * TaskViewManager
 * Centralized, reusable task view component that can be used across pages
 * Supports full-page views, modals, and inline panels
 * Can work with built-in filters OR integrate with external filter elements
 */

import { createTaskCard, renderTasks } from './task-card.js';
import { getListsWithCounts, getTagsWithCounts, initMultiselectFilter } from './multiselect.js';

export class TaskViewManager {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.options = {
            // View mode: 'full', 'modal', 'inline'
            mode: options.mode || 'full',
            
            // ID prefix for unique element IDs (important for multiple instances)
            idPrefix: options.idPrefix || 'taskview',
            
            // Initial data
            data: options.data || [],
            
            // Callback when a task is clicked
            onTaskClick: options.onTaskClick || null,
            
            // Callback when a task is completed
            onTaskComplete: options.onTaskComplete || null,
            
            // Whether to show built-in filters
            showBuiltInFilters: options.showBuiltInFilters !== false,
            
            // Whether to show the task count
            showCount: options.showCount !== false,
            
            // Custom title for the view
            title: options.title || 'Tasks',
            
            // Whether filters should be initially visible
            filtersInitiallyVisible: options.filtersInitiallyVisible !== false,
            
            // Maximum height for modal/inline views (CSS value)
            maxHeight: options.maxHeight || '500px',
            
            // Whether to show completion checkbox
            showCompleteButton: options.showCompleteButton !== false,
            
            // External filter element IDs (optional - for integration with existing HTML filters)
            externalFilters: options.externalFilters || null
        };

        this.state = {
            tasks: [...this.options.data],
            filteredTasks: [...this.options.data],
            filters: {
                search: '',
                status: '',
                priority: '',
                list: [],
                tags: [],
                dateField: 'due',
                dateStart: '',
                dateEnd: '',
                sortField: 'due',
                sortOrder: 'desc'
            }
        };

        this.listMultiselect = null;
        this.tagsMultiselect = null;
        this.isInitialized = false;

        // Bind methods for event handlers
        this.handleFilterChange = this.handleFilterChange.bind(this);
        this.handleSearchInput = this.handleSearchInput.bind(this);
        this.handleClearFilters = this.handleClearFilters.bind(this);
        
        // Store reference for external access
        window.taskViewManagers = window.taskViewManagers || {};
        window.taskViewManagers[containerId] = this;
    }

    /**
     * Initialize the task view
     */
    init() {
        if (this.isInitialized) {
            console.warn('TaskViewManager already initialized');
            return this;
        }

        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`Container with ID "${this.containerId}" not found`);
            return this;
        }

        this.renderTemplate();
        this.setupEventListeners();
        
        // Apply initial filters and sorting
        this.filterTasks();
        
        this.isInitialized = true;
        console.log(`TaskViewManager initialized for ${this.containerId}`);
        return this;
    }

    /**
     * Render the basic layout based on mode
     */
    renderTemplate() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const p = this.options.idPrefix;
        const mode = this.options.mode;
        
        // Container styles based on mode
        const containerStyle = mode === 'modal' 
            ? `max-height: ${this.options.maxHeight}; overflow-y: auto;` 
            : '';

        // Build filter HTML based on mode (only if not using external filters)
        let filterHtml = '';
        if (this.options.showBuiltInFilters && !this.options.externalFilters) {
            filterHtml = this.buildFilterHtml(p);
        }

        // Build count HTML
        let countHtml = '';
        if (this.options.showCount) {
            countHtml = `
                <div class="${p}-count-display" style="margin-bottom: 1rem;">
                    <span class="${p}-count-text" style="color: #6b7280; font-size: 0.875rem;">
                        Loading...
                    </span>
                </div>
            `;
        }

        // Build the main HTML structure
        container.innerHTML = `
            <div class="taskview-container" style="${containerStyle}">
                ${mode === 'modal' ? `<h3 style="margin-bottom: 1rem;">${this.options.title}</h3>` : ''}
                ${filterHtml}
                ${countHtml}
                <div class="${p}-grid taskview-grid" id="${p}-grid" style="
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 1rem;
                    margin-top: ${this.options.showBuiltInFilters ? '1rem' : '0'};
                "></div>
            </div>
        `;

        // Initialize multiselects (only in full mode, not modal)
        if (this.options.showBuiltInFilters && this.options.mode !== 'modal' && !this.options.externalFilters) {
            this.initMultiselects();
        }
    }

    /**
     * Build filter HTML based on configuration
     */
    buildFilterHtml(prefix) {
        // In modal mode, use simplified filters
        if (this.options.mode === 'modal') {
            return `
                <div class="taskview-filters" style="
                    display: flex;
                    gap: 0.75rem;
                    flex-wrap: wrap;
                    padding: 1rem;
                    background: #f9fafb;
                    border-radius: 8px;
                    margin-bottom: 1rem;
                ">
                    <input type="text" 
                           id="${prefix}-search-filter" 
                           class="filter-input" 
                           placeholder="Search tasks..."
                           style="
                                flex: 1;
                                min-width: 200px;
                                padding: 0.5rem 0.75rem;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 0.875rem;
                           "
                    >
                    <select id="${prefix}-status-filter" class="filter-select" style="
                        padding: 0.5rem 0.75rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        font-size: 0.875rem;
                        background: white;
                    ">
                        <option value="">All Status</option>
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                    </select>
                    <select id="${prefix}-priority-filter" class="filter-select" style="
                        padding: 0.5rem 0.75rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        font-size: 0.875rem;
                        background: white;
                    ">
                        <option value="">All Priorities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    <button id="${prefix}-clear-filters" class="btn btn-secondary" style="
                        padding: 0.5rem 1rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        background: white;
                        cursor: pointer;
                        font-size: 0.875rem;
                    ">
                        Clear
                    </button>
                </div>
            `;
        }

        // Full mode - use the full filter bar
        return `
            <div class="taskview-filters" style="
                padding: 1rem;
                background: #f9fafb;
                border-radius: 8px;
                margin-bottom: 1rem;
            ">
                <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.75rem;">
                    <input type="text" id="${prefix}-search-filter" class="filter-input" 
                           placeholder="Search tasks..." style="
                                flex: 1;
                                min-width: 200px;
                                padding: 0.5rem 0.75rem;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                           ">
                    <select id="${prefix}-status-filter" class="filter-select" style="
                        padding: 0.5rem 0.75rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        background: white;
                    ">
                        <option value="">All Status</option>
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                    </select>
                    <select id="${prefix}-priority-filter" class="filter-select" style="
                        padding: 0.5rem 0.75rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        background: white;
                    ">
                        <option value="">All Priorities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    <select id="${prefix}-sort-field" class="filter-select" style="
                        padding: 0.5rem 0.75rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        background: white;
                    ">
                        <option value="due">Due Date</option>
                        <option value="created_at">Created Date</option>
                        <option value="priority">Priority</option>
                        <option value="title">Title</option>
                    </select>
                    <select id="${prefix}-sort-order" class="filter-select" style="
                        padding: 0.5rem 0.75rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        background: white;
                    ">
                        <option value="desc">Descending</option>
                        <option value="asc">Ascending</option>
                    </select>
                    <button id="${prefix}-clear-filters" class="btn btn-secondary" style="
                        padding: 0.5rem 1rem;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        background: white;
                        cursor: pointer;
                    ">
                        Clear Filters
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Initialize multiselect filters
     */
    initMultiselects() {
        const p = this.options.idPrefix;
        const allLists = getListsWithCounts(this.state.tasks);
        const allTags = getTagsWithCounts(this.state.tasks);

        this.listMultiselect = initMultiselectFilter({
            id: `${p}-list-filter`,
            options: allLists,
            placeholder: 'Select Lists',
            showCounts: true,
            onChange: (selected) => {
                this.state.filters.list = selected;
                this.filterTasks();
            }
        });

        this.tagsMultiselect = initMultiselectFilter({
            id: `${p}-tags-filter`,
            options: allTags,
            placeholder: 'Select Tags',
            showCounts: true,
            onChange: (selected) => {
                this.state.filters.tags = selected;
                this.filterTasks();
            }
        });
    }

    /**
     * Set up event listeners for filters (built-in or external)
     */
    setupEventListeners() {
        const p = this.options.idPrefix;

        // If using external filters, set up listeners on those
        if (this.options.externalFilters) {
            this.setupExternalFilterListeners();
            return;
        }

        // Built-in filters
        if (!this.options.showBuiltInFilters) return;

        // Helper to add listener safely
        const addListener = (suffix, event, handler) => {
            const el = document.getElementById(`${p}-${suffix}`);
            if (el) el.addEventListener(event, handler);
        };

        addListener('search-filter', 'input', this.handleSearchInput);
        addListener('status-filter', 'change', this.handleFilterChange);
        addListener('priority-filter', 'change', this.handleFilterChange);
        addListener('clear-filters', 'click', this.handleClearFilters);

        // Add sort listeners only in full mode
        if (this.options.mode !== 'modal') {
            addListener('sort-field', 'change', this.handleFilterChange);
            addListener('sort-order', 'change', this.handleFilterChange);
        }
    }

    /**
     * Set up event listeners for external filter elements
     */
    setupExternalFilterListeners() {
        const ext = this.options.externalFilters;
        
        if (ext.search) {
            const el = document.getElementById(ext.search);
            if (el) el.addEventListener('input', this.handleSearchInput);
        }
        
        if (ext.status) {
            const el = document.getElementById(ext.status);
            if (el) el.addEventListener('change', this.handleFilterChange);
        }
        
        if (ext.priority) {
            const el = document.getElementById(ext.priority);
            if (el) el.addEventListener('change', this.handleFilterChange);
        }
        
        if (ext.dateField) {
            const el = document.getElementById(ext.dateField);
            if (el) el.addEventListener('change', this.handleFilterChange);
        }
        
        if (ext.dateStart) {
            const el = document.getElementById(ext.dateStart);
            if (el) el.addEventListener('change', this.handleFilterChange);
        }
        
        if (ext.dateEnd) {
            const el = document.getElementById(ext.dateEnd);
            if (el) el.addEventListener('change', this.handleFilterChange);
        }
        
        if (ext.sortField) {
            const el = document.getElementById(ext.sortField);
            if (el) el.addEventListener('change', this.handleFilterChange);
        }
        
        if (ext.sortOrder) {
            const el = document.getElementById(ext.sortOrder);
            if (el) el.addEventListener('change', this.handleFilterChange);
        }
        
        if (ext.clear) {
            const el = document.getElementById(ext.clear);
            if (el) el.addEventListener('click', this.handleClearFilters);
        }
    }

    /**
     * Handle search input
     */
    handleSearchInput(e) {
        this.state.filters.search = e.target.value;
        this.filterTasks();
    }

    /**
     * Handle filter changes
     */
    handleFilterChange(e) {
        const id = e.target.id;
        const value = e.target.value;

        if (id.includes('status-filter') || (this.options.externalFilters?.status && id === this.options.externalFilters.status)) {
            this.state.filters.status = value;
        } else if (id.includes('priority-filter') || (this.options.externalFilters?.priority && id === this.options.externalFilters.priority)) {
            this.state.filters.priority = value;
        } else if (id.includes('date-field') || (this.options.externalFilters?.dateField && id === this.options.externalFilters.dateField)) {
            this.state.filters.dateField = value;
        } else if (id.includes('date-start') || (this.options.externalFilters?.dateStart && id === this.options.externalFilters.dateStart)) {
            this.state.filters.dateStart = value;
        } else if (id.includes('date-end') || (this.options.externalFilters?.dateEnd && id === this.options.externalFilters.dateEnd)) {
            this.state.filters.dateEnd = value;
        } else if (id.includes('sort-field') || (this.options.externalFilters?.sortField && id === this.options.externalFilters.sortField)) {
            this.state.filters.sortField = value;
        } else if (id.includes('sort-order') || (this.options.externalFilters?.sortOrder && id === this.options.externalFilters.sortOrder)) {
            this.state.filters.sortOrder = value;
        }

        this.filterTasks();
    }

    /**
     * Handle clear filters
     */
    handleClearFilters() {
        const p = this.options.idPrefix;

        // Reset inputs (built-in)
        const resetInput = (id, val) => {
            const el = document.getElementById(`${p}-${id}`);
            if (el) el.value = val;
        };

        resetInput('search-filter', '');
        resetInput('status-filter', '');
        resetInput('priority-filter', '');
        resetInput('sort-field', 'due');
        resetInput('sort-order', 'desc');

        // Reset external filters if they exist
        if (this.options.externalFilters) {
            const ext = this.options.externalFilters;
            if (ext.search && document.getElementById(ext.search)) document.getElementById(ext.search).value = '';
            if (ext.status && document.getElementById(ext.status)) document.getElementById(ext.status).value = '';
            if (ext.priority && document.getElementById(ext.priority)) document.getElementById(ext.priority).value = '';
            if (ext.dateField && document.getElementById(ext.dateField)) document.getElementById(ext.dateField).value = 'due';
            if (ext.dateStart && document.getElementById(ext.dateStart)) document.getElementById(ext.dateStart).value = '';
            if (ext.dateEnd && document.getElementById(ext.dateEnd)) document.getElementById(ext.dateEnd).value = '';
            if (ext.sortField && document.getElementById(ext.sortField)) document.getElementById(ext.sortField).value = 'due';
            if (ext.sortOrder && document.getElementById(ext.sortOrder)) document.getElementById(ext.sortOrder).value = 'desc';
        }

        if (this.listMultiselect) this.listMultiselect.clear();
        if (this.tagsMultiselect) this.tagsMultiselect.clear();

        // Reset state
        this.state.filters = {
            search: '',
            status: '',
            priority: '',
            list: [],
            tags: [],
            dateField: 'due',
            dateStart: '',
            dateEnd: '',
            sortField: 'due',
            sortOrder: 'desc'
        };

        this.filterTasks();
    }

    /**
     * Load new tasks data
     */
    loadTasks(newTasks) {
        this.state.tasks = [...newTasks];

        // Update multiselect options if they exist
        if (this.listMultiselect) {
            this.listMultiselect.setOptions(getListsWithCounts(this.state.tasks));
        }
        if (this.tagsMultiselect) {
            this.tagsMultiselect.setOptions(getTagsWithCounts(this.state.tasks));
        }

        this.filterTasks();
    }

    /**
     * Add a single task
     */
    addTask(task) {
        this.state.tasks.push(task);
        this.filterTasks();
    }

    /**
     * Update a task
     */
    updateTask(taskId, updates) {
        const index = this.state.tasks.findIndex(t => t.id === taskId);
        if (index !== -1) {
            this.state.tasks[index] = { ...this.state.tasks[index], ...updates };
            this.filterTasks();
        }
    }

    /**
     * Remove a task
     */
    removeTask(taskId) {
        this.state.tasks = this.state.tasks.filter(t => t.id !== taskId);
        this.filterTasks();
    }

    /**
     * Filter tasks based on current filters
     */
    filterTasks() {
        const { tasks, filters } = this.state;

        let result = tasks.filter(task => {
            // Search
            if (filters.search) {
                const term = filters.search.toLowerCase();
                const title = (task.title || '').toLowerCase();
                const desc = (task.description || '').toLowerCase();
                const notes = (task.notes || '').toLowerCase();
                if (!title.includes(term) && !desc.includes(term) && !notes.includes(term)) return false;
            }

            // Status
            if (filters.status && task.status !== filters.status) return false;

            // Priority
            if (filters.priority) {
                const p = (task.calculated_priority || task.priority || 'medium').toLowerCase();
                if (p !== filters.priority) return false;
            }

            // List
            if (filters.list.length > 0) {
                const listName = task.list_title || task.parent_title || 'Unknown List';
                if (!filters.list.includes(listName)) return false;
            }

            // Tags
            if (filters.tags.length > 0) {
                const taskTags = [
                    ...(task.tags || []),
                    ...(task.account_tags || [])
                ];
                const hasTag = filters.tags.some(t => 
                    taskTags.some(tt => {
                        const cleanTag = tt.startsWith('#') || tt.startsWith('@') ? tt : 
                            (tt.includes('@') ? '@' + tt : '#' + tt);
                        return cleanTag === t;
                    })
                );
                if (!hasTag) return false;
            }

            // Date Range
            if (filters.dateStart || filters.dateEnd) {
                const dateVal = task[filters.dateField]; // 'due', 'created_at', etc.
                if (!dateVal) return false;

                const taskDate = new Date(dateVal);
                if (filters.dateStart) {
                    const start = new Date(filters.dateStart);
                    if (taskDate < start) return false;
                }
                if (filters.dateEnd) {
                    const end = new Date(filters.dateEnd);
                    end.setHours(23, 59, 59, 999);
                    if (taskDate > end) return false;
                }
            }

            return true;
        });

        // Sorting
        result.sort((a, b) => {
            let valA = a[filters.sortField];
            let valB = b[filters.sortField];

            if (filters.sortField === 'due' || filters.sortField.includes('at')) {
                valA = valA ? new Date(valA).getTime() : 0;
                valB = valB ? new Date(valB).getTime() : 0;
            }

            if (valA < valB) return filters.sortOrder === 'asc' ? -1 : 1;
            if (valA > valB) return filters.sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        this.state.filteredTasks = result;
        this.updateView();
    }

    /**
     * Update the view with filtered tasks
     */
    updateView() {
        const p = this.options.idPrefix;
        const grid = document.getElementById(`${p}-grid`);
        const countText = document.getElementById(`${p}-count-text`);

        if (!grid) return;

        // Update count
        if (countText && this.options.showCount) {
            countText.textContent = `Showing ${this.state.filteredTasks.length} of ${this.state.tasks.length} tasks`;
        }

        // Render empty state
        if (this.state.filteredTasks.length === 0) {
            grid.innerHTML = `
                <div style="
                    grid-column: 1 / -1;
                    text-align: center;
                    padding: 3rem;
                    color: #6b7280;
                ">
                    <i class="fas fa-tasks" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <p style="font-size: 1.125rem;">No tasks found</p>
                    <p style="font-size: 0.875rem;">Try adjusting your filters or create a new task</p>
                </div>
            `;
            return;
        }

        // Render task cards
        grid.innerHTML = '';
        this.state.filteredTasks.forEach(task => {
            const card = createTaskCard(task, { 
                isNodeTask: this.options.mode === 'modal' 
            });
            
            // Add click handler for task details
            if (this.options.onTaskClick) {
                card.style.cursor = 'pointer';
                card.addEventListener('click', () => {
                    this.options.onTaskClick(task);
                });
            }

            grid.appendChild(card);
        });
    }

    /**
     * Get the current filtered tasks
     */
    getFilteredTasks() {
        return this.state.filteredTasks;
    }

    /**
     * Get all tasks
     */
    getAllTasks() {
        return this.state.tasks;
    }

    /**
     * Get current filter state
     */
    getFilterState() {
        return { ...this.state.filters };
    }

    /**
     * Set custom filters programmatically
     */
    setFilters(filters) {
        this.state.filters = { ...this.state.filters, ...filters };
        
        // Update UI to reflect filter changes
        if (this.options.showBuiltInFilters) {
            const p = this.options.idPrefix;
            
            if (filters.search !== undefined) {
                const searchInput = document.getElementById(`${p}-search-filter`);
                if (searchInput) searchInput.value = filters.search;
            }
            if (filters.status !== undefined) {
                const statusSelect = document.getElementById(`${p}-status-filter`);
                if (statusSelect) statusSelect.value = filters.status;
            }
            if (filters.priority !== undefined) {
                const prioritySelect = document.getElementById(`${p}-priority-filter`);
                if (prioritySelect) prioritySelect.value = filters.priority;
            }
        }
        
        // Also update external filters if they exist
        if (this.options.externalFilters) {
            const ext = this.options.externalFilters;
            if (filters.search !== undefined && ext.search) {
                const el = document.getElementById(ext.search);
                if (el) el.value = filters.search;
            }
            if (filters.status !== undefined && ext.status) {
                const el = document.getElementById(ext.status);
                if (el) el.value = filters.status;
            }
            if (filters.priority !== undefined && ext.priority) {
                const el = document.getElementById(ext.priority);
                if (el) el.value = filters.priority;
            }
            if (filters.dateField !== undefined && ext.dateField) {
                const el = document.getElementById(ext.dateField);
                if (el) el.value = filters.dateField;
            }
            if (filters.dateStart !== undefined && ext.dateStart) {
                const el = document.getElementById(ext.dateStart);
                if (el) el.value = filters.dateStart;
            }
            if (filters.dateEnd !== undefined && ext.dateEnd) {
                const el = document.getElementById(ext.dateEnd);
                if (el) el.value = filters.dateEnd;
            }
            if (filters.sortField !== undefined && ext.sortField) {
                const el = document.getElementById(ext.sortField);
                if (el) el.value = filters.sortField;
            }
            if (filters.sortOrder !== undefined && ext.sortOrder) {
                const el = document.getElementById(ext.sortOrder);
                if (el) el.value = filters.sortOrder;
            }
        }
        
        this.filterTasks();
    }

    /**
     * Refresh the view (useful after external data changes)
     */
    refresh() {
        this.filterTasks();
    }

    /**
     * Destroy the instance (cleanup)
     */
    destroy() {
        const container = document.getElementById(this.containerId);
        if (container) {
            container.innerHTML = '';
        }
        this.isInitialized = false;
        this.listMultiselect = null;
        this.tagsMultiselect = null;
        
        // Remove from global registry
        if (window.taskViewManagers && window.taskViewManagers[this.containerId]) {
            delete window.taskViewManagers[this.containerId];
        }
    }
}

/**
 * Factory function to create a task view quickly
 * @param {string} containerId - Container element ID
 * @param {Array} tasks - Initial tasks data
 * @param {Object} options - Additional options
 * @returns {TaskViewManager} - The initialized manager
 */
export function createTaskView(containerId, tasks = [], options = {}) {
    const manager = new TaskViewManager(containerId, {
        data: tasks,
        ...options
    });
    manager.init();
    return manager;
}

/**
 * Create a task view optimized for modals
 * @param {string} containerId - Container element ID  
 * @param {Array} tasks - Tasks data
 * @param {Object} callbacks - Callback functions
 * @returns {TaskViewManager}
 */
export function createModalTaskView(containerId, tasks, callbacks = {}) {
    return createTaskView(containerId, tasks, {
        mode: 'modal',
        showBuiltInFilters: true,
        showCount: true,
        title: callbacks.title || 'Tasks',
        onTaskClick: callbacks.onTaskClick || null,
        onTaskComplete: callbacks.onTaskComplete || null,
        maxHeight: callbacks.maxHeight || '400px'
    });
}

/**
 * Create a task view that integrates with external filter elements
 * @param {string} containerId - Container element ID
 * @param {Array} tasks - Tasks data
 * @param {Object} externalFilters - Object containing IDs of external filter elements
 * @returns {TaskViewManager}
 */
export function createIntegratedTaskView(containerId, tasks, externalFilters = {}) {
    return createTaskView(containerId, tasks, {
        mode: 'modal',
        showBuiltInFilters: false, // Use external filters instead
        showCount: true,
        externalFilters: externalFilters
    });
}

/**
 * Create an inline task view (for sidebars, panels)
 * @param {string} containerId - Container element ID
 * @param {Array} tasks - Tasks data
 * @param {Object} callbacks - Callback functions
 * @returns {TaskViewManager}
 */
export function createInlineTaskView(containerId, tasks, callbacks = {}) {
    return createTaskView(containerId, tasks, {
        mode: 'inline',
        showBuiltInFilters: false,
        showCount: true,
        title: callbacks.title || '',
        onTaskClick: callbacks.onTaskClick || null
    });
}

/**
 * Get a TaskViewManager instance by container ID
 * @param {string} containerId - Container element ID
 * @returns {TaskViewManager|null}
 */
export function getTaskViewManager(containerId) {
    return window.taskViewManagers?.[containerId] || null;
}

/**
 * Mark a task as incomplete (completed -> pending)
 * @param {string} taskId - Task ID
 * @param {Object} options - Options
 * @returns {Promise} - API response
 */
export async function incompleteTask(taskId, options = {}) {
    const { accountId = null, syncToGoogle = true, onSuccess, onError } = options;
    
    try {
        const response = await fetch('/api/tasks/' + taskId + '/incomplete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                account_id: accountId,
                sync_to_google: syncToGoogle
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('[incompleteTask] ✅ Task marked as incomplete:', taskId);
            if (onSuccess) onSuccess(data);
            return data;
        } else {
            console.error('[incompleteTask] ❌ Failed to mark task as incomplete:', data.message);
            if (onError) onError(data.message);
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('[incompleteTask] ❌ Error marking task as incomplete:', error);
        if (onError) onError(error.message);
        throw error;
    }
}

/**
 * Update task details
 * @param {string} taskId - Task ID
 * @param {Object} updates - Fields to update
 * @param {Object} options - Options
 * @returns {Promise} - API response
 */
export async function updateTask(taskId, updates, options = {}) {
    const { 
        accountId = null, 
        syncToGoogle = true, 
        title, 
        description, 
        due, 
        priority, 
        status,
        notes,
        dueDate,
        onSuccess, 
        onError 
    } = options;
    
    // Build update payload
    const payload = {
        account_id: accountId,
        sync_to_google: syncToGoogle
    };
    
    // Add fields if provided
    if (title !== undefined) payload.title = title;
    if (description !== undefined) payload.description = description;
    if (due !== undefined) payload.due = due;
    if (priority !== undefined) payload.priority = priority;
    if (status !== undefined) payload.status = status;
    if (notes !== undefined) payload.notes = notes;
    if (dueDate !== undefined) payload.due_date = dueDate;
    
    // Also include updates object if provided
    if (updates && typeof updates === 'object') {
        Object.assign(payload, updates);
    }
    
    try {
        const response = await fetch('/api/tasks/' + taskId + '/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('[updateTask] ✅ Task updated:', taskId, data.updated_fields);
            if (onSuccess) onSuccess(data);
            return data;
        } else {
            console.error('[updateTask] ❌ Failed to update task:', data.message);
            if (onError) onError(data.message);
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('[updateTask] ❌ Error updating task:', error);
        if (onError) onError(error.message);
        throw error;
    }
}

// Export for global access
window.TaskViewManager = TaskViewManager;
window.createTaskView = createTaskView;
window.createModalTaskView = createModalTaskView;
window.createIntegratedTaskView = createIntegratedTaskView;
window.createInlineTaskView = createInlineTaskView;
window.getTaskViewManager = getTaskViewManager;
window.incompleteTask = incompleteTask;
window.updateTask = updateTask;
