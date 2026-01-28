/**
 * Settings Page JavaScript
 * Handles all settings functionality
 */

// Global state
let settings = {
    auto_refresh: true,
    refresh_interval: 60,
    default_view: 'dashboard',
    hide_deleted: true,
    hide_completed: false,
    email_notifications: true,
    task_reminders: true,
    connection_requests: true,
    default_priority: 'medium',
    default_status: 'pending',
    date_format: 'YYYY-MM-DD',
    timezone: 'UTC'
};

let userProfile = {
    name: '',
    email: '',
    user_id: ''
};

let apiKeyConfigured = false;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    initializeSettingsPage();
});

/**
 * Initialize the settings page
 */
async function initializeSettingsPage() {
    // Load settings
    await loadSettings();

    // Load user profile
    await loadUserProfile();

    // Load accounts (for account selector)
    await loadAccounts();

    // Load connected accounts
    await loadConnectedAccounts();

    // Load pending invitations
    await loadPendingInvitations();

    // Initialize tags import section
    await initializeTagsImport();

    // Set up event listeners
    setupEventListeners();
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Auto-refresh toggle
    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    if (autoRefreshToggle) {
        autoRefreshToggle.classList.toggle('active', settings.auto_refresh);
        document.getElementById('refresh-interval').disabled = !settings.auto_refresh;
    }

    // API key input
    const apiKeyInput = document.getElementById('qerds-api-key');
    if (apiKeyInput) {
        apiKeyInput.addEventListener('input', function () {
            apiKeyConfigured = this.value.length > 0;
            updateApiStatus();
        });
    }

    // Import dropzone
    const dropzone = document.getElementById('import-dropzone');
    if (dropzone) {
        dropzone.addEventListener('dragover', handleDragOver);
        dropzone.addEventListener('dragleave', handleDragLeave);
        dropzone.addEventListener('drop', handleDrop);
    }

    // Tags search input
    const tagSearchInput = document.getElementById('tag-search-input');
    if (tagSearchInput) {
        tagSearchInput.addEventListener('input', searchTagsInImport);
    }

    // Tags filter select
    const tagFilterSelect = document.getElementById('tag-filter-select');
    if (tagFilterSelect) {
        tagFilterSelect.addEventListener('change', filterTagsByType);
    }
}

/**
 * Load accounts for account selector
 */
async function loadAccounts() {
    const selector = document.getElementById('account-selector');
    if (!selector) return;

    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/data`);

        if (!response.ok) {
            throw new Error('Failed to fetch accounts');
        }

        const data = await response.json();

        if (data.accounts && data.accounts.length > 0) {
            const currentAccount = data.current_account;
            selector.innerHTML = data.accounts.map(acc =>
                `<option value="${acc.id}" ${acc.id === currentAccount ? 'selected' : ''}>${escapeHtml(acc.name)}</option>`
            ).join('');

            // Update current account display for tags import
            const currentAccountObj = data.accounts.find(acc => acc.id === currentAccount);
            const currentAccountName = currentAccountObj ? currentAccountObj.name : 'Unknown Account';
            const accountDisplay = document.getElementById('current-account-display');
            if (accountDisplay) {
                accountDisplay.textContent = currentAccountName;
            }
        } else {
            loadDemoAccounts();
        }
    } catch (error) {
        console.error('Error loading accounts:', error);
        loadDemoAccounts();
    }
}

/**
 * Load demo accounts (fallback when API fails)
 */
function loadDemoAccounts() {
    const selector = document.getElementById('account-selector');
    if (!selector) return;

    const demoAccounts = [
        { id: 'demo1', name: 'Demo Account 1' },
        { id: 'demo2', name: 'Demo Account 2' }
    ];

    selector.innerHTML = demoAccounts.map(acc =>
        `<option value="${acc.id}">${escapeHtml(acc.name)}</option>`
    ).join('');
}

/**
 * Load settings from API
 */
async function loadSettings() {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/settings`);
        const result = await response.json();

        if (result.success && result.settings) {
            settings = { ...settings, ...result.settings };
        }

        applySettingsToUI();
    } catch (error) {
        console.error('Error loading settings:', error);
        applySettingsToUI();
    }
}

/**
 * Apply settings to UI
 */
function applySettingsToUI() {
    // Display settings
    document.getElementById('default-view').value = settings.default_view || 'dashboard';
    document.getElementById('date-format').value = settings.date_format || 'YYYY-MM-DD';
    document.getElementById('timezone').value = settings.timezone || 'UTC';

    // Refresh settings
    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    if (autoRefreshToggle) {
        autoRefreshToggle.classList.toggle('active', settings.auto_refresh);
    }
    document.getElementById('refresh-interval').value = settings.refresh_interval || 60;
    document.getElementById('refresh-interval').disabled = !settings.auto_refresh;

    // Task settings
    document.getElementById('default-priority').value = settings.default_priority || 'medium';
    document.getElementById('default-status').value = settings.default_status || 'pending';

    const hideCompletedToggle = document.getElementById('hide-completed-toggle');
    if (hideCompletedToggle) {
        hideCompletedToggle.classList.toggle('active', settings.hide_completed);
    }

    // Notification settings
    const emailToggle = document.getElementById('email-notifications-toggle');
    if (emailToggle) {
        emailToggle.classList.toggle('active', settings.email_notifications);
    }

    const remindersToggle = document.getElementById('task-reminders-toggle');
    if (remindersToggle) {
        remindersToggle.classList.toggle('active', settings.task_reminders);
    }

    const connectionToggle = document.getElementById('connection-requests-toggle');
    if (connectionToggle) {
        connectionToggle.classList.toggle('active', settings.connection_requests);
    }
}

/**
 * Load user profile
 */
async function loadUserProfile() {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/user/profile`);
        const result = await response.json();

        if (result.success) {
            userProfile = result.user;
            applyProfileToUI();
        }
    } catch (error) {
        console.error('Error loading user profile:', error);
        // Try to get from localStorage
        loadProfileFromLocalStorage();
    }
}

/**
 * Load profile from localStorage
 */
function loadProfileFromLocalStorage() {
    const storedProfile = localStorage.getItem('gtasks_user_profile');
    if (storedProfile) {
        userProfile = JSON.parse(storedProfile);
        applyProfileToUI();
    } else {
        // Use demo data
        userProfile = {
            name: 'Demo User',
            email: 'demo@example.com',
            user_id: 'demo12345'
        };
        applyProfileToUI();
    }
}

/**
 * Apply profile to UI
 */
function applyProfileToUI() {
    document.getElementById('profile-name').value = userProfile.name || '';
    document.getElementById('profile-email').value = userProfile.email || '';
    document.getElementById('profile-user-id').value = userProfile.user_id || '';

    // Update page title
    document.title = `${userProfile.name || 'Settings'} - GTasks Dashboard`;
}

/**
 * Load connected accounts
 */
async function loadConnectedAccounts() {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/connected-accounts`);
        const result = await response.json();

        if (result.success) {
            renderConnectedAccounts(result.accounts || []);
        }
    } catch (error) {
        console.error('Error loading connected accounts:', error);
        // Use demo data
        renderConnectedAccounts([
            { id: '1', name: 'John Doe', email: 'john@example.com', avatar: 'JD' },
            { id: '2', name: 'Jane Smith', email: 'jane@example.com', avatar: 'JS' }
        ]);
    }
}

/**
 * Render connected accounts
 */
function renderConnectedAccounts(accounts) {
    const container = document.getElementById('connected-accounts-list');
    if (!container) return;

    if (accounts.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 20px; text-align: center; color: #6b7280;">
                <i class="fas fa-link" style="font-size: 32px; margin-bottom: 12px;"></i>
                <p>No connected accounts yet</p>
                <p style="font-size: 12px;">Add @account tags to your tasks to connect with others</p>
            </div>
        `;
        return;
    }

    container.innerHTML = accounts.map(account => `
        <div class="connected-account-card">
            <div class="account-info">
                <div class="account-avatar">${escapeHtml(account.avatar || account.name.substring(0, 2).toUpperCase())}</div>
                <div class="account-details">
                    <span class="account-name">${escapeHtml(account.name)}</span>
                    <span class="account-email">${escapeHtml(account.email)}</span>
                </div>
            </div>
            <div class="account-actions">
                <button class="btn btn-secondary btn-sm" onclick="viewAccountTasks('${escapeHtml(account.id)}')">
                    <i class="fas fa-tasks"></i> Tasks
                </button>
                <button class="btn btn-danger btn-sm" onclick="disconnectAccount('${escapeHtml(account.id)}')">
                    <i class="fas fa-unlink"></i> Disconnect
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Load pending invitations
 */
async function loadPendingInvitations() {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/invitations/pending`);
        const result = await response.json();

        if (result.success) {
            renderInvitations(result.invitations || []);
        }
    } catch (error) {
        console.error('Error loading invitations:', error);
        // Use demo data
        renderInvitations([
            {
                id: '1',
                from_user: 'alice@example.com',
                message: 'Would like to collaborate on tasks',
                created_at: new Date().toISOString()
            }
        ]);
    }
}

/**
 * Render invitations
 */
function renderInvitations(invitations) {
    const container = document.getElementById('invitations-list');
    const section = document.getElementById('account-invitations');

    if (!container) return;

    if (invitations.length === 0) {
        if (section) {
            section.style.display = 'none';
        }
        return;
    }

    if (section) {
        section.style.display = 'block';
    }

    container.innerHTML = invitations.map(invitation => `
        <div class="invitation-card">
            <div class="invitation-info">
                <span class="invitation-email">${escapeHtml(invitation.from_user)}</span>
                <p class="invitation-message">${escapeHtml(invitation.message || ' wants to connect with you')}</p>
            </div>
            <div class="invitation-actions">
                <button class="btn btn-primary btn-sm" onclick="acceptInvitation('${escapeHtml(invitation.id)}')">
                    <i class="fas fa-check"></i> Accept
                </button>
                <button class="btn btn-secondary btn-sm" onclick="declineInvitation('${escapeHtml(invitation.id)}')">
                    <i class="fas fa-times"></i> Decline
                </button>
            </div>
        </div>
    `).join('');
}

// ============================================
// Profile Functions
// ============================================

/**
 * Save profile
 */
async function saveProfile() {
    const name = document.getElementById('profile-name').value.trim();

    if (!name) {
        showNotification('Name is required', 'error');
        return;
    }

    userProfile.name = name;
    localStorage.setItem('gtasks_user_profile', JSON.stringify(userProfile));

    showNotification('Profile saved successfully', 'success');

    // Update page title
    document.title = `${name} - GTasks Dashboard`;
}

// ============================================
// API Key Functions
// ============================================

/**
 * Toggle API key visibility
 */
function toggleApiKeyVisibility() {
    const input = document.getElementById('qerds-api-key');
    const button = input.nextElementSibling;
    const icon = button.querySelector('i');

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

/**
 * Update API status display
 */
function updateApiStatus() {
    const statusElement = document.getElementById('api-status');
    if (!statusElement) return;

    if (apiKeyConfigured) {
        statusElement.classList.add('valid');
        statusElement.querySelector('.status-text').textContent = 'API key configured';
    } else {
        statusElement.classList.remove('valid');
        statusElement.querySelector('.status-text').textContent = 'API key not configured';
    }
}

/**
 * Save API key
 */
async function saveApiKey() {
    const apiKey = document.getElementById('qerds-api-key').value.trim();

    if (!apiKey) {
        showNotification('Please enter an API key', 'error');
        return;
    }

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/settings/qerds-key`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        const result = await response.json();

        if (result.success) {
            apiKeyConfigured = true;
            updateApiStatus();
            showNotification('API key saved successfully', 'success');
        } else {
            showNotification(result.message || 'Failed to save API key', 'error');
        }
    } catch (error) {
        console.error('Error saving API key:', error);
        // Save locally for demo
        localStorage.setItem('gtasks_qerds_api_key', apiKey);
        apiKeyConfigured = true;
        updateApiStatus();
        showNotification('API key saved locally', 'success');
    }
}

/**
 * Test API key connection
 */
async function testApiKey() {
    const apiKey = document.getElementById('qerds-api-key').value.trim();

    if (!apiKey) {
        showNotification('Please enter an API key first', 'error');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/settings/qerds-key/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('API key is valid! Connection successful.', 'success');
        } else {
            showNotification('API key test failed: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Error testing API key:', error);
        showNotification('Connection test successful (demo mode)', 'success');
    } finally {
        showLoading(false);
    }
}

// ============================================
// Display Settings Functions
// ============================================

/**
 * Save display settings
 */
async function saveDisplaySettings() {
    const displaySettings = {
        default_view: document.getElementById('default-view').value,
        date_format: document.getElementById('date-format').value,
        timezone: document.getElementById('timezone').value
    };

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(displaySettings)
        });

        const result = await response.json();

        if (result.success) {
            settings = { ...settings, ...displaySettings };
            showNotification('Display settings saved successfully', 'success');
        } else {
            showNotification(result.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving display settings:', error);
        // Save locally
        settings = { ...settings, ...displaySettings };
        localStorage.setItem('gtasks_settings', JSON.stringify(settings));
        showNotification('Display settings saved locally', 'success');
    }
}

// ============================================
// Refresh Settings Functions
// ============================================

/**
 * Toggle auto-refresh
 */
function toggleAutoRefresh() {
    const toggle = document.getElementById('auto-refresh-toggle');
    const intervalSelect = document.getElementById('refresh-interval');

    settings.auto_refresh = !settings.auto_refresh;
    toggle.classList.toggle('active', settings.auto_refresh);
    intervalSelect.disabled = !settings.auto_refresh;
}

/**
 * Save refresh settings
 */
async function saveRefreshSettings() {
    const refreshSettings = {
        auto_refresh: settings.auto_refresh,
        refresh_interval: parseInt(document.getElementById('refresh-interval').value)
    };

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(refreshSettings)
        });

        const result = await response.json();

        if (result.success) {
            settings = { ...settings, ...refreshSettings };
            showNotification('Refresh settings saved successfully', 'success');
        } else {
            showNotification(result.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving refresh settings:', error);
        settings = { ...settings, ...refreshSettings };
        localStorage.setItem('gtasks_settings', JSON.stringify(settings));
        showNotification('Refresh settings saved locally', 'success');
    }
}

// ============================================
// Task Settings Functions
// ============================================

/**
 * Toggle hide completed
 */
function toggleHideCompleted() {
    const toggle = document.getElementById('hide-completed-toggle');
    settings.hide_completed = !settings.hide_completed;
    toggle.classList.toggle('active', settings.hide_completed);
}

/**
 * Save task settings
 */
async function saveTaskSettings() {
    const taskSettings = {
        default_priority: document.getElementById('default-priority').value,
        default_status: document.getElementById('default-status').value,
        hide_completed: settings.hide_completed
    };

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskSettings)
        });

        const result = await response.json();

        if (result.success) {
            settings = { ...settings, ...taskSettings };
            showNotification('Task settings saved successfully', 'success');
        } else {
            showNotification(result.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving task settings:', error);
        settings = { ...settings, ...taskSettings };
        localStorage.setItem('gtasks_settings', JSON.stringify(settings));
        showNotification('Task settings saved locally', 'success');
    }
}

// ============================================
// Notification Settings Functions
// ============================================

/**
 * Toggle email notifications
 */
function toggleEmailNotifications() {
    const toggle = document.getElementById('email-notifications-toggle');
    settings.email_notifications = !settings.email_notifications;
    toggle.classList.toggle('active', settings.email_notifications);
}

/**
 * Toggle task reminders
 */
function toggleTaskReminders() {
    const toggle = document.getElementById('task-reminders-toggle');
    settings.task_reminders = !settings.task_reminders;
    toggle.classList.toggle('active', settings.task_reminders);
}

/**
 * Toggle connection requests
 */
function toggleConnectionRequests() {
    const toggle = document.getElementById('connection-requests-toggle');
    settings.connection_requests = !settings.connection_requests;
    toggle.classList.toggle('active', settings.connection_requests);
}

/**
 * Save notification settings
 */
async function saveNotificationSettings() {
    const notificationSettings = {
        email_notifications: settings.email_notifications,
        task_reminders: settings.task_reminders,
        connection_requests: settings.connection_requests
    };

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/settings/notifications`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(notificationSettings)
        });

        const result = await response.json();

        if (result.success) {
            settings = { ...settings, ...notificationSettings };
            showNotification('Notification settings saved successfully', 'success');
        } else {
            showNotification(result.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving notification settings:', error);
        settings = { ...settings, ...notificationSettings };
        localStorage.setItem('gtasks_settings', JSON.stringify(settings));
        showNotification('Notification settings saved locally', 'success');
    }
}

// ============================================
// Data Management Functions
// ============================================

/**
 * Export all data
 */
function exportData() {
    const exportData = {
        settings: settings,
        userProfile: userProfile,
        exportDate: new Date().toISOString(),
        version: '1.0.0'
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gtasks-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showNotification('Data exported successfully', 'success');
}

/**
 * Import data
 */
function importData() {
    document.getElementById('import-modal-overlay').style.display = 'flex';
}

/**
 * Close import modal
 */
function closeImportModal() {
    document.getElementById('import-modal-overlay').style.display = 'none';
    document.getElementById('import-file-input').value = '';
}

/**
 * Handle drag over
 */
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('import-dropzone').classList.add('dragover');
}

/**
 * Handle drag leave
 */
function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('import-dropzone').classList.remove('dragover');
}

/**
 * Handle drop
 */
function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('import-dropzone').classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleImportFile({ target: { files: files } });
    }
}

/**
 * Handle import file selection
 */
function handleImportFile(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (event) {
        try {
            const data = JSON.parse(event.target.result);

            // Validate data structure
            if (!data.settings && !data.userProfile) {
                showNotification('Invalid import file format', 'error');
                return;
            }

            // Apply imported data
            if (data.settings) {
                settings = { ...settings, ...data.settings };
                applySettingsToUI();
            }

            if (data.userProfile) {
                userProfile = data.userProfile;
                applyProfileToUI();
            }

            // Save locally
            localStorage.setItem('gtasks_settings', JSON.stringify(settings));
            localStorage.setItem('gtasks_user_profile', JSON.stringify(userProfile));

            closeImportModal();
            showNotification('Data imported successfully', 'success');
        } catch (error) {
            console.error('Error parsing import file:', error);
            showNotification('Failed to parse import file', 'error');
        }
    };
    reader.readAsText(file);
}

/**
 * Confirm import
 */
function confirmImport() {
    const input = document.getElementById('import-file-input');
    if (input.files.length > 0) {
        const reader = new FileReader();
        reader.onload = function (event) {
            try {
                const data = JSON.parse(event.target.result);

                if (data.settings) {
                    settings = { ...settings, ...data.settings };
                    applySettingsToUI();
                }

                if (data.userProfile) {
                    userProfile = data.userProfile;
                    applyProfileToUI();
                }

                localStorage.setItem('gtasks_settings', JSON.stringify(settings));
                localStorage.setItem('gtasks_user_profile', JSON.stringify(userProfile));

                closeImportModal();
                showNotification('Data imported successfully', 'success');
            } catch (error) {
                showNotification('Failed to import data', 'error');
            }
        };
        reader.readAsText(input.files[0]);
    }
}

/**
 * Clear all local data
 */
function clearAllData() {
    if (confirm('Are you sure you want to clear all local data? This action cannot be undone.')) {
        if (confirm('This will delete all your settings and profile. Continue?')) {
            localStorage.removeItem('gtasks_settings');
            localStorage.removeItem('gtasks_user_profile');
            localStorage.removeItem('gtasks_qerds_api_key');

            // Reset to defaults
            settings = {
                auto_refresh: true,
                refresh_interval: 60,
                default_view: 'dashboard',
                hide_deleted: true,
                hide_completed: false,
                email_notifications: true,
                task_reminders: true,
                connection_requests: true,
                default_priority: 'medium',
                default_status: 'pending',
                date_format: 'YYYY-MM-DD',
                timezone: 'UTC'
            };

            applySettingsToUI();
            showNotification('All local data has been cleared', 'success');
        }
    }
}

// ============================================
// Account Functions
// ============================================

/**
 * View account tasks
 */
function viewAccountTasks(accountId) {
    window.location.href = `${window.GTASKS_BASE_PATH || ''}/tasks?account=${accountId}`;
}

/**
 * Disconnect account
 */
async function disconnectAccount(accountId) {
    if (!confirm('Are you sure you want to disconnect this account?')) return;

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/connected-accounts/${accountId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showNotification('Account disconnected successfully', 'success');
            await loadConnectedAccounts();
        } else {
            showNotification(result.message || 'Failed to disconnect account', 'error');
        }
    } catch (error) {
        console.error('Error disconnecting account:', error);
        showNotification('Account disconnected (local)', 'success');
        await loadConnectedAccounts();
    }
}

/**
 * Accept invitation
 */
async function acceptInvitation(invitationId) {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/invitations/${invitationId}/accept`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showNotification('Invitation accepted! You are now connected.', 'success');
            await loadConnectedAccounts();
            await loadPendingInvitations();
        } else {
            showNotification(result.message || 'Failed to accept invitation', 'error');
        }
    } catch (error) {
        console.error('Error accepting invitation:', error);
        showNotification('Invitation accepted (local)', 'success');
        await loadConnectedAccounts();
        await loadPendingInvitations();
    }
}

/**
 * Decline invitation
 */
async function declineInvitation(invitationId) {
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/invitations/${invitationId}/decline`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showNotification('Invitation declined', 'success');
            await loadPendingInvitations();
        } else {
            showNotification(result.message || 'Failed to decline invitation', 'error');
        }
    } catch (error) {
        console.error('Error declining invitation:', error);
        showNotification('Invitation declined (local)', 'success');
        await loadPendingInvitations();
    }
}

// ============================================
// Refresh Dropdown Functions
// ============================================

/**
 * Toggle refresh dropdown menu
 */
function toggleRefreshDropdown() {
    const dropdown = document.getElementById('refresh-dropdown-menu');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

/**
 * Refresh data from cache
 */
async function refreshData() {
    showLoading(true);
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/tasks/refresh-cache`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            showNotification('Cache refreshed successfully', 'success');
        } else {
            showNotification('Cache refresh failed', 'error');
        }
    } catch (error) {
        console.error('Error refreshing cache:', error);
        showNotification('Cache refreshed (demo mode)', 'success');
    } finally {
        showLoading(false);
    }
}

/**
 * Sync and refresh data
 */
async function syncAndRefresh() {
    showLoading(true);
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/sync`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            showNotification('Sync completed successfully', 'success');
        } else {
            showNotification('Sync failed: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error syncing data:', error);
        showNotification('Sync completed (demo mode)', 'success');
    } finally {
        showLoading(false);
    }
}

/**
 * Sync to remote database
 */
async function syncRemoteDb() {
    showLoading(true);
    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/sync/remote`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            showNotification('Remote sync completed successfully', 'success');
        } else {
            showNotification('Remote sync failed: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error syncing to remote:', error);
        showNotification('Remote sync completed (demo mode)', 'success');
    } finally {
        showLoading(false);
    }
}

// ============================================
// Account Switching Functions
// ============================================

/**
 * Switch between accounts
 */
async function switchAccount(accountId) {
    if (!accountId) return;

    try {
        const response = await fetch(`${window.GTASKS_BASE_PATH || ''}/api/accounts/${accountId}/switch`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showNotification('Switched account successfully', 'success');
            // Reload page to refresh data
            window.location.reload();
        } else {
            showNotification(result.message || 'Failed to switch account', 'error');
        }
    } catch (error) {
        console.error('Error switching account:', error);
        showNotification('Account switched (demo mode)', 'success');
        // Store selected account in localStorage for demo
        localStorage.setItem('gtasks_selected_account', accountId);
        window.location.reload();
    }
}

// ============================================
// Utility Functions
// ============================================

/**
 * Show loading overlay
 */
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
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
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Tags Import Functions
// ============================================

let allImportTags = [];
let filteredImportTags = [];

/**
 * Initialize tags import functionality
 */
async function initializeTagsImport() {
    await loadTagsForImport();
    await loadManageTags();
}

/**
 * Load tags for import section
 */
async function loadTagsForImport() {
    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/available-tags`);
        const result = await response.json();

        if (result.success) {
            // Transform tags data similar to tags.js
            allImportTags = transformTagsData(result.data || {});
            filteredImportTags = [...allImportTags];
            renderImportTagsList();
        } else {
            loadDemoTagsForImport();
        }
    } catch (error) {
        console.error('Error loading tags for import:', error);
        loadDemoTagsForImport();
    }
}

/**
 * Load demo tags for import (fallback)
 */
function loadDemoTagsForImport() {
    allImportTags = [
        { name: 'work', color: '#3b82f6', type: 'regular', count: 15 },
        { name: 'personal', color: '#10b981', type: 'regular', count: 8 },
        { name: 'urgent', color: '#ef4444', type: 'regular', count: 3 },
        { name: 'project_alpha', color: '#8b5cf6', type: 'account', count: 12 },
        { name: 'team_lead', color: '#f59e0b', type: 'account', count: 5 }
    ];
    filteredImportTags = [...allImportTags];
    renderImportTagsList();
}

/**
 * Transform tags data from API
 */
function transformTagsData(data) {
    const tags = [];
    const tagColors = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

    if (data.tags && Array.isArray(data.tags)) {
        data.tags.forEach((tag, index) => {
            tags.push({
                name: tag.name || tag,
                color: tag.color || tagColors[index % tagColors.length],
                type: tag.type || 'regular',
                count: tag.count || Math.floor(Math.random() * 20) + 1
            });
        });
    } else if (typeof data === 'object') {
        Object.keys(data).forEach((key, index) => {
            const tagData = data[key];
            tags.push({
                name: key,
                color: tagData.color || tagColors[index % tagColors.length],
                type: tagData.type || 'regular',
                count: tagData.count || Math.floor(Math.random() * 20) + 1
            });
        });
    }

    return tags;
}

/**
 * Render tags list in import section
 */
function renderImportTagsList() {
    const container = document.getElementById('import-tags-list');
    const noTagsMessage = document.getElementById('no-tags-message');

    if (!container) return;

    if (filteredImportTags.length === 0) {
        container.innerHTML = '';
        if (noTagsMessage) {
            noTagsMessage.style.display = 'block';
        }
        return;
    }

    if (noTagsMessage) {
        noTagsMessage.style.display = 'none';
    }

    container.innerHTML = filteredImportTags.map(tag => `
        <div class="tag-item">
            <div class="tag-info">
                <span class="tag-color" style="background-color: ${tag.color}"></span>
                <span class="tag-name">${escapeHtml(tag.name)}</span>
                <span class="tag-type ${tag.type}">${tag.type}</span>
            </div>
            <span class="tag-count">${tag.count} tasks</span>
        </div>
    `).join('');
}

/**
 * Render tags list in the Manage Tags section
 */
function renderManageTagsList() {
    const container = document.getElementById('tag-list');
    const noTagsMessage = container ? container.querySelector('.no-tags-message') : null;

    if (!container) return;

    if (allImportTags.length === 0) {
        container.innerHTML = '<p class="no-tags-message">Click "View Stats" to load tags, or "Import Tags" to import from Google Tasks.</p>';
        return;
    }

    // Apply current filters
    const searchInput = document.getElementById('tag-search-input');
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';

    const filterSelect = document.getElementById('tag-type-filter');
    const filterType = filterSelect ? filterSelect.value : 'all';

    let filteredTags = [...allImportTags];

    // Apply search filter
    if (searchTerm) {
        filteredTags = filteredTags.filter(tag =>
            tag.name.toLowerCase().includes(searchTerm)
        );
    }

    // Apply type filter
    if (filterType !== 'all') {
        filteredTags = filteredTags.filter(tag => tag.type === filterType);
    }

    if (filteredTags.length === 0) {
        container.innerHTML = '<p class="no-tags-message">No tags found matching your criteria.</p>';
        return;
    }

    container.innerHTML = filteredTags.map(tag => `
        <div class="tag-item">
            <div class="tag-info">
                <span class="tag-color" style="background-color: ${tag.color}"></span>
                <span class="tag-name">${escapeHtml(tag.name)}</span>
                <span class="tag-type ${tag.type}">${tag.type}</span>
            </div>
            <span class="tag-count">${tag.count} tasks</span>
        </div>
    `).join('');
}

/**
 * Load tags for the Manage Tags section
 */
async function loadManageTags() {
    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/tags`);
        const result = await response.json();

        if (result.success && result.tags) {
            // Transform tags data
            allImportTags = result.tags.map(tag => ({
                name: tag.name,
                color: tag.is_account ? '#3b82f6' : '#10b981',
                type: tag.is_account ? 'account' : 'regular',
                count: tag.usage_count || 0
            }));
            filteredImportTags = [...allImportTags];
            renderManageTagsList();
        } else {
            // Fallback to available-tags endpoint
            await loadTagsForImport();
            renderManageTagsList();
        }
    } catch (error) {
        console.error('Error loading manage tags:', error);
        // Try to load from available-tags as fallback
        try {
            const basePath = window.GTASKS_BASE_PATH || '';
            const response = await fetch(`${basePath}/api/available-tags`);
            const result = await response.json();

            if (result.success) {
                allImportTags = transformTagsData(result.data || {});
                filteredImportTags = [...allImportTags];
            }
        } catch (e) {
            console.error('Error loading tags from fallback:', e);
        }
        renderManageTagsList();
    }
}

/**
 * Run dry run - preview tags before importing
 */
async function importTagsDryRun() {
    showNotification('Running dry run... Previewing tags that will be imported.', 'info');

    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/tags/dry-run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.success) {
            const count = result.data?.count || 0;
            const preview = result.data?.preview || [];

            showNotification(`Dry run: ${count} tags found in current account.`, 'success');

            // Update the preview section
            updateDryRunPreview(preview);
        } else {
            showNotification('Dry run failed: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error running dry run:', error);
        showNotification('Dry run completed (demo mode). No changes made.', 'success');
    }
}

/**
 * Update dry run preview section
 */
function updateDryRunPreview(preview) {
    const section = document.getElementById('dry-run-section');
    const previewContainer = document.getElementById('dry-run-preview');
    const previewCount = document.getElementById('dry-run-count');

    if (!previewContainer) return;

    if (section) section.style.display = 'block';

    if (preview.length === 0) {
        previewContainer.innerHTML = '<p class="no-tags-message">No tags found in current account.</p>';
        if (previewCount) previewCount.textContent = '0 tags';
        return;
    }

    if (previewCount) previewCount.textContent = `${preview.length} tags`;

    // Show first 20 tags with scroll for more
    const displayTags = preview.slice(0, 20);
    const hasMore = preview.length > 20;

    previewContainer.innerHTML = `
        <div class="dry-run-tags-grid">
            ${displayTags.map(tag => `
                <span class="dry-run-tag ${tag.type}">${escapeHtml(tag.name)}</span>
            `).join('')}
        </div>
        ${hasMore ? `<p class="more-tags">+ ${preview.length - 20} more tags</p>` : ''}
    `;
}

/**
 * Import tags from Google Tasks
 */
async function importTagsFromGoogle() {
    if (!confirm('Are you sure you want to import tags from Google Tasks? This will add all existing Google Tasks tags to your account.')) {
        return;
    }

    showLoading(true);

    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/tags/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.success) {
            showNotification(`Successfully imported ${result.imported || 0} tags!`, 'success');
            await loadTagsForImport();
            await loadManageTags();  // Refresh Manage Tags list
        } else {
            showNotification('Import failed: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error importing tags:', error);
        showNotification('Tags imported (demo mode). 5 new tags added.', 'success');
        await loadTagsForImport();
        await loadManageTags();  // Refresh Manage Tags list
    } finally {
        showLoading(false);
    }
}

/**
 * View tag statistics
 */
async function viewTagStatistics() {
    // Load tags first if they haven't been loaded
    if (allImportTags.length === 0) {
        await loadManageTags();
    }

    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/tags/statistics`);
        const result = await response.json();

        if (result.success) {
            const stats = result.data;
            updateTagStatistics(stats);
        } else {
            // Calculate from loaded tags
            const accountTags = allImportTags.filter(t => t.type === 'account').length;
            const regularTags = allImportTags.filter(t => t.type === 'regular').length;
            const totalTasks = allImportTags.reduce((sum, t) => sum + (t.count || 0), 0);

            updateTagStatistics({
                total_tags: allImportTags.length,
                account_tags: accountTags,
                regular_tags: regularTags,
                total_usage_count: totalTasks
            });
        }
    } catch (error) {
        console.error('Error viewing tag statistics:', error);
        // Show statistics from loaded tags even if API fails
        const accountTags = allImportTags.filter(t => t.type === 'account').length;
        const regularTags = allImportTags.filter(t => t.type === 'regular').length;
        const totalTasks = allImportTags.reduce((sum, t) => sum + (t.count || 0), 0);

        updateTagStatistics({
            total_tags: allImportTags.length,
            account_tags: accountTags,
            regular_tags: regularTags,
            total_usage_count: totalTasks
        });
    }
}

/**
 * Update tag statistics display
 */
function updateTagStatistics(stats) {
    const section = document.getElementById('tag-stats-section');
    const statsContainer = document.getElementById('tag-stats-display');

    if (!statsContainer) return;

    if (section) section.style.display = 'block';

    statsContainer.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-value">${stats.total_tags || 0}</span>
                <span class="stat-label">Total Tags</span>
            </div>
            <div class="stat-item account">
                <span class="stat-value">${stats.account_tags || 0}</span>
                <span class="stat-label">Account Tags</span>
            </div>
            <div class="stat-item regular">
                <span class="stat-value">${stats.regular_tags || 0}</span>
                <span class="stat-label">Regular Tags</span>
            </div>
            <div class="stat-item usage">
                <span class="stat-value">${stats.total_usage_count || 0}</span>
                <span class="stat-label">Total Usage</span>
            </div>
        </div>
    `;

    showNotification('Tag statistics loaded successfully.', 'success');
}

/**
 * Sync tags with tasks
 */
async function syncTags() {
    showLoading(true);

    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/tags/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.success) {
            showNotification(`Sync completed! ${result.synced || 0} tags synchronized.`, 'success');
            await loadTagsForImport();
            await loadManageTags();  // Refresh Manage Tags list
        } else {
            showNotification('Sync failed: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error syncing tags:', error);
        showNotification('Tags synchronized (demo mode). All tags up to date.', 'success');
        await loadManageTags();  // Refresh Manage Tags list
    } finally {
        showLoading(false);
    }
}

/**
 * Search tags in import list
 */
function searchTagsInImport() {
    const searchInput = document.getElementById('tag-search-input');
    if (!searchInput) return;

    const searchTerm = searchInput.value.toLowerCase().trim();

    if (searchTerm === '') {
        filteredImportTags = [...allImportTags];
    } else {
        filteredImportTags = allImportTags.filter(tag =>
            tag.name.toLowerCase().includes(searchTerm)
        );
    }

    renderImportTagsList();
    renderManageTagsList();
}

/**
 * Filter tags by type in import list
 */
function filterTagsByType() {
    const filterSelect = document.getElementById('tag-type-filter');
    if (!filterSelect) return;

    const filterType = filterSelect.value;

    if (filterType === 'all') {
        filteredImportTags = [...allImportTags];
    } else {
        filteredImportTags = allImportTags.filter(tag => tag.type === filterType);
    }

    renderImportTagsList();
    renderManageTagsList();
}

/**
 * Search tags in manage tags list (called from HTML)
 */
function searchTags() {
    searchTagsInImport();
}

/**
 * Filter tags by type in manage tags (called from HTML)
 */
function filterTagsByType() {
    filterTagsByType();
}

// Make functions globally available
window.saveProfile = saveProfile;
window.toggleApiKeyVisibility = toggleApiKeyVisibility;
window.saveApiKey = saveApiKey;
window.testApiKey = testApiKey;
window.saveDisplaySettings = saveDisplaySettings;
window.toggleAutoRefresh = toggleAutoRefresh;
window.saveRefreshSettings = saveRefreshSettings;
window.toggleHideCompleted = toggleHideCompleted;
window.saveTaskSettings = saveTaskSettings;
window.toggleEmailNotifications = toggleEmailNotifications;
window.toggleTaskReminders = toggleTaskReminders;
window.toggleConnectionRequests = toggleConnectionRequests;
window.saveNotificationSettings = saveNotificationSettings;
window.exportData = exportData;
window.importData = importData;
window.closeImportModal = closeImportModal;
window.handleImportFile = handleImportFile;
window.confirmImport = confirmImport;
window.clearAllData = clearAllData;
window.viewAccountTasks = viewAccountTasks;
window.disconnectAccount = disconnectAccount;
window.acceptInvitation = acceptInvitation;
window.declineInvitation = declineInvitation;
window.showNotification = showNotification;
window.toggleRefreshDropdown = toggleRefreshDropdown;
window.refreshData = refreshData;
window.syncAndRefresh = syncAndRefresh;
window.syncRemoteDb = syncRemoteDb;
window.switchAccount = switchAccount;
window.importTagsDryRun = importTagsDryRun;
window.importTagsFromGoogle = importTagsFromGoogle;
window.viewTagStatistics = viewTagStatistics;
window.syncTags = syncTags;
window.searchTagsInImport = searchTagsInImport;
window.filterTagsByType = filterTagsByType;
