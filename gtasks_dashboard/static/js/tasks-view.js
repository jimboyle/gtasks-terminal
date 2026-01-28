/**
 * TasksView Component
 * Renders a reusable tasks view with filters, sorting, and grid layout.
 */
import { createTaskCard } from './task-card.js';
import { getListsWithCounts, getTagsWithCounts, initMultiselectFilter } from './multiselect.js';

export class TasksView {
    constructor(containerId, options = {}) {
        // ... (constructor remains same) ...
        this.containerId = containerId;
        this.options = {
            idPrefix: options.idPrefix || 'tasks',
            data: options.data || [],
            onTaskClick: options.onTaskClick || null,
            hideFilters: options.hideFilters || false,
            initialView: options.initialView || 'grid',
            title: options.title || 'Tasks',
            showCount: options.showCount !== false
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

        this.init();
    }

    init() {
        this.renderTemplate();
        this.setupEventListeners();
        // Apply initial filters and sorting
        this.filterTasks();
    }

    /**
     * Render the basic layout
     */
    renderTemplate() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const p = this.options.idPrefix;

        let filterHtml = `
            <div class="task-filters-container collapsed" id="${p}-filters-container">
            <!-- Header: Search + Primary Actions (Sticky) -->
            <div class="task-filters-header sticky-header">
                <div class="search-wrapper">
                    <input type="text" id="${p}-search-filter" class="filter-input" placeholder="Search tasks..." autocomplete="off">
                </div>

                <!-- Primary Status Filter -->
                <select id="${p}-status-filter" class="header-select">
                    <option value="">All Status</option>
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                </select>

                <button id="${p}-filter-toggle" class="btn-icon-only" title="Show Advanced Filters">
                    <i class="fas fa-filter"></i>
                </button>

                <button id="${p}-clear-filters-header" class="btn-icon-only" title="Clear All Filters" style="display:none;">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <!-- Clean Grid Content -->
            <div class="task-filters-content" id="${p}-filters-content">

                <!-- Column 1: Priority & Lists -->
                <div class="filter-group">
                    <div class="filter-section-title">Properties</div>
                    <select id="${p}-priority-filter" class="filter-select">
                        <option value="">All Priorities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    <div class="multiselect-container" id="${p}-list-filter"></div>
                </div>

                <!-- Column 2: Tags -->
                <div class="filter-group">
                    <div class="filter-section-title">Tags</div>
                    <div class="multiselect-container" id="${p}-tags-filter"></div>
                </div>

                <!-- Column 3: Date Filtering -->
                <div class="filter-group">
                    <div class="filter-section-title">Date Range</div>
                    <select id="${p}-date-field" class="filter-select">
                        <option value="due">Due Date</option>
                        <option value="created_at">Created</option>
                        <option value="modified_at">Modified</option>
                    </select>
                    <div class="date-range-group">
                        <input type="date" id="${p}-date-start" class="filter-input" placeholder="Start">
                            <span style="color:var(--text-light)">-</span>
                            <input type="date" id="${p}-date-end" class="filter-input" placeholder="End">
                            </div>
                    </div>

                    <!-- Column 4: Sorting & Reset -->
                    <div class="filter-group">
                        <div class="filter-section-title">Sort & Actions</div>
                        <div class="date-range-group">
                            <select id="${p}-sort-field" class="filter-select" style="flex:2">
                                <option value="due">Sort: Due Date</option>
                                <option value="created_at">Sort: Created</option>
                                <option value="modified_at">Sort: Modified</option>
                                <option value="priority">Sort: Priority</option>
                                <option value="title">Sort: Title</option>
                            </select>
                            <select id="${p}-sort-order" class="filter-select" style="flex:1">
                                <option value="desc">Desc</option>
                                <option value="asc">Asc</option>
                            </select>
                        </div>
                        <button id="${p}-clear-filters" class="btn btn-secondary" style="width:100%; margin-top: auto;">
                            <i class="fas fa-times"></i> Reset Filters
                        </button>
                    </div>
                </div>
            </div>`;

            const countHtml = this.options.showCount ?
            `<div class="tasks-count-display">
                <span id="${p}-count-text">Loading...</span>
            </div>` : '';

            container.innerHTML = `
            ${filterHtml}
            ${countHtml}
            <div class="tasks-grid" id="${p}-grid"></div>
            `;

            // Initialize Multiselects
            if (!this.options.hideFilters) {
                this.initMultiselects();
            }
        }

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

        setupEventListeners() {
            if (this.options.hideFilters) return;

            const p = this.options.idPrefix;

            // Helper to add listener safely
            const addListener = (suffix, event, handler) => {
                const el = document.getElementById(`${p}-${suffix}`);
                if (el) el.addEventListener(event, handler);
            };

            addListener('filter-toggle', 'click', () => {
                const container = document.getElementById(`${p}-filters-container`);
                const btn = document.getElementById(`${p}-filter-toggle`);
                // We might have changed the icon element, so re-query
                const icon = btn.querySelector('i') || btn.querySelector('svg');

                if (container && btn) {
                    container.classList.toggle('collapsed');
                    if (container.classList.contains('collapsed')) {
                        // Collapsed state: Show filter icon or chevron down
                        // For now using filter icon as "Show Advanced" indicator
                        if (icon) {
                            icon.className = 'fas fa-filter';
                        }
                        btn.title = "Show Advanced Filters";
                        btn.classList.remove('active');
                    } else {
                        // Expanded state: Show chevron up
                        if (icon) {
                            icon.className = 'fas fa-chevron-up';
                        }
                        btn.title = "Hide Advanced Filters";
                        btn.classList.add('active');
                    }
                }
            });

            addListener('search-filter', 'input', (e) => {
                this.state.filters.search = e.target.value;
                this.filterTasks();
            });

            addListener('status-filter', 'change', (e) => {
                this.state.filters.status = e.target.value;
                this.filterTasks();
            });

            addListener('priority-filter', 'change', (e) => {
                this.state.filters.priority = e.target.value;
                this.filterTasks();
            });

            addListener('date-field', 'change', (e) => {
                this.state.filters.dateField = e.target.value;
                this.filterTasks();
            });

            addListener('date-start', 'change', (e) => {
                this.state.filters.dateStart = e.target.value;
                this.filterTasks();
            });

            addListener('date-end', 'change', (e) => {
                this.state.filters.dateEnd = e.target.value;
                this.filterTasks();
            });

            addListener('sort-field', 'change', (e) => {
                this.state.filters.sortField = e.target.value;
                this.filterTasks();
            });

            addListener('sort-order', 'change', (e) => {
                this.state.filters.sortOrder = e.target.value;
                this.filterTasks();
            });

            addListener('clear-filters', 'click', () => {
                this.clearFilters();
            });
        }

        loadTasks(newTasks) {
            this.state.tasks = [...newTasks];

            // Update multiselect options if filters exist
            if (this.listMultiselect) {
                this.listMultiselect.setOptions(getListsWithCounts(this.state.tasks));
            }
            if (this.tagsMultiselect) {
                this.tagsMultiselect.setOptions(getTagsWithCounts(this.state.tasks));
            }

            this.filterTasks();
        }

        clearFilters() {
            const p = this.options.idPrefix;

            // Reset Inputs
            const resetInput = (id, val) => {
                const el = document.getElementById(`${p}-${id}`);
                if (el) el.value = val;
            };

            resetInput('search-filter', '');
            resetInput('status-filter', '');
            resetInput('priority-filter', '');
            resetInput('date-field', 'due');
            resetInput('date-start', '');
            resetInput('date-end', '');
            resetInput('sort-field', 'due');
            resetInput('sort-order', 'desc'); // Default to desc usually

            if (this.listMultiselect) this.listMultiselect.clear();
            if (this.tagsMultiselect) this.tagsMultiselect.clear();

            // Reset State
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

        filterTasks() {
            const {tasks, filters} = this.state;

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
                    // Collect all tags from hybrid_tags and regular tags
                    const taskTags = new Set();
                    if (task.hybrid_tags) {
                        task.hybrid_tags.bracket?.forEach(t => taskTags.add(t));
                        task.hybrid_tags.hash?.forEach(t => taskTags.add(t));
                        task.hybrid_tags.user?.forEach(t => taskTags.add(t));
                    }
                    // Also check regular tags
                    task.tags?.forEach(t => taskTags.add(t));
                    task.account_tags?.forEach(t => taskTags.add(t));
                    
                    // Check if task has AT LEAST one of the selected tags (OR logic)
                    const hasTag = filters.tags.some(selectedTag => {
                        return [...taskTags].some(taskTag => {
                            // Normalize both to compare without prefixes
                            const cleanSelected = selectedTag.replace(/^#|^@/, '');
                            const cleanTask = taskTag.replace(/^#|^@/, '');
                            return cleanSelected === cleanTask;
                        });
                    });
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
                        // set end of day
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

                // Specific handling for priority text to number if needed,
                // but for now assuming string comparison or server pre-calc
                // If date
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

        updateView() {
            const p = this.options.idPrefix;
            const grid = document.getElementById(`${p}-grid`);
            const countText = document.getElementById(`${p}-count-text`);

            if (!grid) return;

            // Update Count
            if (countText) {
                countText.textContent = `Showing ${this.state.filteredTasks.length} of ${this.state.tasks.length} tasks`;
            }

            if (this.state.filteredTasks.length === 0) {
                grid.innerHTML = '<div class="empty-state"><p>No tasks found.</p></div>';
                return;
            }

            grid.innerHTML = '';
            this.state.filteredTasks.forEach(task => {
                const card = createTaskCard(task);
                if (this.options.onTaskClick) {
                    // Determine if we want to override default behavior or attach to card
                    // standard task-card.js might handle clicks internally (e.g. view details)
                }
                grid.appendChild(card);
            });
        }
    }
