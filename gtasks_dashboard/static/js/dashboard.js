/**
 * Dashboard Module
 * Main dashboard functionality and initialization
 */

import { stateManager } from './state.js';

// Initialize state from storage (restores dark mode, etc.)
stateManager.initFromStorage();

import { apiEndpoints, refreshIntervalOptions, storageKeys } from './constants.js';
import {
    filterOutDeletedTasks,
    sortTasksByField,
    filterTasksByCriteria,
    debounce
} from './utils.js';
import { createTaskCard, renderTasksGrid } from './task-card.js';
import { createMultiselect, getUniqueLists, getUniqueTags, getListsWithCounts, getTagsWithCounts, getFilteredTagsByLists, getFilteredListsByTags, getFilteredTasksBySearchAndDate, getFilteredListsByTagsAndCriteria, getFilteredTagsByListsAndCriteria } from './multiselect.js';
import {
    renderHierarchy,
    initHierarchy,
    updateHierarchyVisualization as updateHierarchyViz,
    initHierarchyFilters,
    refreshHierarchyVisualization
} from './hierarchy.js';
import { TasksView } from './tasks-view.js';

// Force load hierarchy-renderer.js module directly
import * as HierarchyRenderer from './hierarchy-renderer.js';

console.log('[Dashboard] HierarchyRenderer module loaded:', Object.keys(HierarchyRenderer));
console.log('[Dashboard] renderHierarchy function:', typeof HierarchyRenderer.renderHierarchy);
console.log('[Dashboard] updateHierarchyVisualization function:', typeof HierarchyRenderer.updateHierarchyVisualization);
console.log('[Dashboard] initHierarchy function:', typeof HierarchyRenderer.initHierarchy);

// Global references for backward compatibility
let dashboardData = {};
let selectedAccount = null;
let isFullscreen = false;
let hierarchyData = {};
let selectedNode = null;
let autoRefreshInterval = null;

// Sync state variables
let isSyncing = false;
let syncProgress = { percentage: 0, message: '', status: 'idle' };
let syncPollInterval = null;

// Authentication state
let currentUser = null;
let pendingInvitationsCount = 0;
let mainTasksView = null;

// Export for backward compatibility
export function getDashboardData() {
    return dashboardData;
}

export function setDashboardData(data) {
    dashboardData = data;
    window.dashboardData = data;  // Also set on window for other modules to access
    stateManager.setDashboardData(data);
}

export function getHierarchyData() {
    return hierarchyData;
}

export function setHierarchyData(data) {
    hierarchyData = data;
    stateManager.setHierarchyData(data);
}

export function getSelectedNode() {
    return selectedNode;
}

export function setSelectedNode(node) {
    selectedNode = node;
    stateManager.setSelectedNode(node);
}

// ========== UI Functions ==========

/**
 * Show/hide loading overlay
 */
export function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

/**
 * Get current section from URL path
 * @returns {string} - The section name ('dashboard', 'hierarchy', 'tasks')
 */
export function getCurrentSectionFromPath() {
    const basePath = window.GTASKS_BASE_PATH || '';
    const path = window.location.pathname;

    // Remove base path from path for comparison
    const relativePath = path.replace(basePath, '') || '/';

    if (relativePath === '/hierarchy' || relativePath.startsWith('/hierarchy')) {
        return 'hierarchy';
    } else if (relativePath === '/tasks' || relativePath.startsWith('/tasks')) {
        return 'tasks';
    } else if (relativePath === '/tags' || relativePath.startsWith('/tags')) {
        return 'tags';
    } else if (relativePath === '/dashboard' || relativePath === '/') {
        return 'dashboard';
    }
    return 'dashboard'; // Default to dashboard
}

/**
 * Update navigation active state based on current section
 * @param {string} section - The current section name
 */
export function updateNavActiveState(section) {
    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    // Add active class to current section's nav item
    const navItem = document.getElementById(`nav-${section}`);
    if (navItem) {
        navItem.classList.add('active');
    }
}

/**
 * Show section
 * @param {string} section - The section name to show
 * @param {boolean} updateUrl - Whether to update the URL (default: true)
 */
export function showSection(section, updateUrl = true) {
    document.querySelectorAll('.section').forEach(s => s.style.display = 'none');

    const sectionEl = document.getElementById(`${section}-section`);
    if (sectionEl) {
        sectionEl.style.display = 'block';
    }

    // Update navigation active state
    updateNavActiveState(section);

    // Update URL without full page reload (only if updateUrl is true)
    if (updateUrl) {
        const basePath = window.GTASKS_BASE_PATH || '';
        const newUrl = `${basePath}/${section === 'dashboard' ? '' : section}`;
        window.history.replaceState({}, '', newUrl);
    }

    stateManager.setCurrentSection(section);

    if (section === 'hierarchy') {
        // Add a small delay to allow the browser to calculate layout dimensions
        setTimeout(() => {
            loadHierarchy();
        }, 50);
    }
}

/**
 * Toggle sidebar
 */
export function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');
}

/**
 * Toggle fullscreen
 */
export function toggleFullscreen() {
    isFullscreen = stateManager.toggleFullscreen();

    setTimeout(() => {
        if (typeof updateHierarchyViz === 'function') {
            updateHierarchyViz(hierarchyData);
        }
    }, 300);
}

// ========== Data Loading ==========

/**
 * Load dashboard data
 */
export async function loadDashboard() {
    showLoading(true);
    try {
        const response = await fetch(apiEndpoints.data);
        const data = await response.json();
        setDashboardData(data);

        updateStats();
        updateAccountSelectors();
        loadTasks();

        // Load hierarchy data
        await loadHierarchy();

        console.log('Dashboard loaded successfully');
    } catch (error) {
        console.error('Error loading dashboard:', error);
    } finally {
        showLoading(false);
    }
}

// ========== Advanced Sync ==========

/**
 * Start an advanced sync operation
 */
export async function startAdvancedSync() {
    // Prevent multiple simultaneous sync operations
    if (isSyncing) {
        console.log('[Sync] Sync already in progress, ignoring duplicate request');
        showNotification('Sync already in progress...', 'warning');
        return;
    }

    isSyncing = true;
    syncProgress = { percentage: 0, message: 'Starting sync...', status: 'running' };

    // Disable refresh button
    const refreshBtn = document.querySelector('.header-refresh-btn');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.classList.add('disabled');
    }

    // Show progress UI
    updateSyncProgressUI();

    try {
        console.log('[Sync] Starting advanced sync...');

        // Start the advanced sync
        const startResponse = await fetch(apiEndpoints.sync.advanced, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ sync_type: 'both' })
        });

        if (!startResponse.ok) {
            throw new Error(`Failed to start sync: ${startResponse.status}`);
        }

        const startData = await startResponse.json();
        console.log('[Sync] Advanced sync started:', startData);

        const syncId = startData.sync_id;

        // Start polling for progress
        syncPollInterval = setInterval(async () => {
            await pollSyncProgress(syncId);
        }, 500);

    } catch (error) {
        console.error('[Sync] Error starting advanced sync:', error);
        syncProgress = { percentage: 0, message: error.message, status: 'error' };
        updateSyncProgressUI();

        // Re-enable refresh button after a delay
        setTimeout(() => {
            stopSyncProgressUI();
        }, 3000);
    }
}

/**
 * Poll sync progress
 * @param {string} syncId - The sync operation ID
 */
async function pollSyncProgress(syncId) {
    try {
        const response = await fetch(`${apiEndpoints.sync.progress}?sync_id=${syncId}`);
        if (!response.ok) {
            throw new Error(`Failed to get sync progress: ${response.status}`);
        }

        const progressData = await response.json();
        console.log('[Sync] Progress update:', progressData);

        // Extract progress from data object (API returns data nested in 'data' property)
        const progress = progressData.data || progressData;

        // Update progress state
        syncProgress = {
            percentage: progress.percentage || 0,
            message: progress.message || 'Processing...',
            status: progress.status || 'running'
        };

        // Update UI
        updateSyncProgressUI();

        // Check if sync is complete or error
        if (progress.status === 'completed') {
            clearInterval(syncPollInterval);
            syncPollInterval = null;

            // Show completion message
            syncProgress.message = 'Sync completed successfully!';
            syncProgress.status = 'completed';
            updateSyncProgressUI();

            console.log('[Sync] Sync completed successfully');

            // Wait a moment then refresh cache and dashboard
            setTimeout(async () => {
                // First refresh the cache on the server
                try {
                    await fetch(apiEndpoints.refresh, { method: 'POST' });
                } catch (e) {
                    console.warn('[Sync] Cache refresh failed, continuing with loadDashboard:', e);
                }

                // Then reload the dashboard data
                await loadDashboard();
                stopSyncProgressUI();
                showNotification('Data refreshed successfully! ✅', 'success');
            }, 1000);
        } else if (progressData.status === 'error') {
            clearInterval(syncPollInterval);
            syncPollInterval = null;

            syncProgress.message = progressData.message || 'Sync failed';
            syncProgress.status = 'error';
            updateSyncProgressUI();

            console.error('[Sync] Sync error:', progressData.message);

            // Re-enable refresh button after showing error
            setTimeout(() => {
                stopSyncProgressUI();
                showNotification(`Sync failed: ${progressData.message}`, 'error');
            }, 3000);
        }
    } catch (error) {
        console.error('[Sync] Error polling sync progress:', error);
        syncProgress.message = error.message;
        syncProgress.status = 'error';
        updateSyncProgressUI();
    }
}

/**
 * Update the sync progress UI
 */
export function updateSyncProgressUI() {
    let overlay = document.getElementById('sync-progress-overlay');

    // Create overlay if it doesn't exist
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'sync-progress-overlay';
        overlay.className = 'sync-progress-overlay';
        document.body.appendChild(overlay);

        overlay.innerHTML = `
            <div class="sync-progress-modal">
                <div class="sync-progress-header">
                    <i class="fas fa-sync-alt fa-spin"></i>
                    <span>Syncing Data</span>
                </div>
                <div class="sync-progress-content">
                    <div class="sync-progress-bar-container">
                        <div class="sync-progress-bar" id="sync-progress-bar" style="width: 0%"></div>
                    </div>
                    <div class="sync-progress-info">
                        <span id="sync-progress-percentage">0%</span>
                        <span id="sync-progress-message">Starting sync...</span>
                    </div>
                    <div class="sync-progress-status" id="sync-progress-status">Running</div>
                </div>
            </div>
        `;
    }

    // Update progress bar
    const progressBar = document.getElementById('sync-progress-bar');
    const percentageText = document.getElementById('sync-progress-percentage');
    const messageText = document.getElementById('sync-progress-message');
    const statusText = document.getElementById('sync-progress-status');
    const headerIcon = overlay.querySelector('.sync-progress-header i');

    if (progressBar) {
        progressBar.style.width = `${syncProgress.percentage}%`;
    }

    if (percentageText) {
        percentageText.textContent = `${syncProgress.percentage}%`;
    }

    if (messageText) {
        messageText.textContent = syncProgress.message;
    }

    if (statusText) {
        statusText.textContent = syncProgress.status.charAt(0).toUpperCase() + syncProgress.status.slice(1);
        statusText.className = `sync-progress-status status-${syncProgress.status}`;
    }

    // Update header icon based on status
    if (headerIcon) {
        if (syncProgress.status === 'completed') {
            headerIcon.className = 'fas fa-check-circle';
            headerIcon.style.color = 'var(--success-color)';
        } else if (syncProgress.status === 'error') {
            headerIcon.className = 'fas fa-exclamation-circle';
            headerIcon.style.color = 'var(--danger-color)';
        } else {
            headerIcon.className = 'fas fa-sync-alt fa-spin';
            headerIcon.style.color = 'var(--primary-color)';
        }
    }

    // Show overlay
    overlay.classList.add('active');
}

/**
 * Stop sync progress UI and reset state
 */
export function stopSyncProgressUI() {
    // Clear poll interval
    if (syncPollInterval) {
        clearInterval(syncPollInterval);
        syncPollInterval = null;
    }

    // Reset sync state
    isSyncing = false;
    syncProgress = { percentage: 0, message: '', status: 'idle' };

    // Hide overlay
    const overlay = document.getElementById('sync-progress-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }

    // Re-enable refresh button
    const refreshBtn = document.querySelector('.header-refresh-btn');
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.classList.remove('disabled');
    }
}

/**
 * Refresh data using advanced sync
 * This is the new function that replaces direct loadDashboard() call
 */
export async function refreshWithAdvancedSync() {
    await startAdvancedSync();
}

/**
 * Simple cache refresh - reloads data from database without full sync
 * This is called when the refresh button is clicked
 */
export async function simpleCacheRefresh() {
    console.log('[Dashboard] Simple cache refresh...');
    try {
        const response = await fetch(apiEndpoints.refresh, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            console.log('[Dashboard] Cache refreshed successfully:', data);
            // Reload dashboard data to reflect changes
            await loadDashboard();
            showNotification('Dashboard refreshed! ✅', 'success');
        } else {
            console.error('[Dashboard] Cache refresh failed:', data.message);
            showNotification(data.message || 'Refresh failed', 'error');
        }
    } catch (error) {
        console.error('[Dashboard] Error during cache refresh:', error);
        showNotification('Error refreshing dashboard', 'error');
    }
}

// ========== Refresh Dropdown Functions ==========

/**
 * Toggle the refresh dropdown menu
 */
export function toggleRefreshDropdown() {
    const dropdown = document.getElementById('refresh-dropdown-menu');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

/**
 * Sync data and refresh cache
 * This is called when "Sync Data" option is selected
 */
export async function syncAndRefresh() {
    console.log('[Dashboard] Sync and refresh...');
    // Start advanced sync - this will automatically refresh cache when complete
    await startAdvancedSync();
}

/**
 * Run gtasks remote sync command in background thread
 * This is called when "Sync External DB" option is selected
 */
export async function syncRemoteDb() {
    console.log('[Dashboard] Sync External DB - starting background command...');
    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/remote/sync-command`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            console.log('[Dashboard] Remote sync command started:', data.message);
            showNotification('Remote sync started in background... ℹ️', 'info');
        } else {
            console.error('[Dashboard] Failed to start remote sync:', data.message);
            showNotification(data.message || 'Failed to start remote sync', 'error');
        }
    } catch (error) {
        console.error('[Dashboard] Error starting remote sync:', error);
        showNotification('Error starting remote sync', 'error');
    }
}

/**
 * Close refresh dropdown when clicking outside
 */
export function setupRefreshDropdown() {
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('refresh-dropdown-menu');
        const toggle = document.querySelector('.refresh-dropdown-toggle');
        if (dropdown && toggle && !dropdown.contains(e.target) && !toggle.contains(e.target)) {
            dropdown.classList.remove('active');
        }
    });
}

// ========== Authentication ==========

/**
 * Check authentication status
 */
export async function checkAuthStatus() {
    try {
        const response = await fetch(apiEndpoints.auth.status);
        const data = await response.json();

        if (data.authenticated) {
            currentUser = data.user;
            updateAuthUI(true, data.user);
            await loadPendingInvitations();
        } else {
            currentUser = null;
            updateAuthUI(false, null);
        }

        return data;
    } catch (error) {
        console.error('Error checking auth status:', error);
        currentUser = null;
        updateAuthUI(false, null);
        return { authenticated: false };
    }
}

/**
 * Update UI based on authentication status
 * @param {boolean} isAuthenticated - Whether user is authenticated
 * @param {Object} user - User data if authenticated
 */
function updateAuthUI(isAuthenticated, user) {
    // Find or create auth section in header
    let authSection = document.getElementById('auth-section');

    if (!authSection) {
        // Create auth section if it doesn't exist
        const headerActions = document.querySelector('.header-actions');
        if (headerActions) {
            authSection = document.createElement('div');
            authSection.id = 'auth-section';
            authSection.className = 'auth-section';
            authSection.innerHTML = `
                <div id="auth-login-link" class="auth-link" style="display: none;">
                    <a href="${apiEndpoints.auth.login}" class="btn btn-primary btn-sm">
                        <i class="fas fa-sign-in-alt"></i> Sign In
                    </a>
                </div>
                <div id="auth-user-info" class="auth-user-info" style="display: none;">
                    <div class="auth-user-dropdown">
                        <button class="auth-user-btn" onclick="toggleUserDropdown()">
                            <i class="fas fa-user-circle"></i>
                            <span id="auth-user-name"></span>
                            <i class="fas fa-chevron-down"></i>
                        </button>
                        <div id="auth-user-menu" class="auth-user-menu">
                            <div class="auth-user-details">
                                <strong id="auth-user-email"></strong>
                                <span id="auth-user-id" class="auth-user-id"></span>
                            </div>
                            <div class="auth-user-actions">
                                <a href="#" onclick="viewSharedTasks(); return false;">
                                    <i class="fas fa-share-alt"></i> Shared Tasks
                                    <span id="auth-invitations-badge" class="badge badge-warning" style="display: none;">0</span>
                                </a>
                                <a href="#" onclick="viewPendingInvitations(); return false;">
                                    <i class="fas fa-envelope"></i> Invitations
                                    <span id="auth-pending-badge" class="badge badge-info" style="display: none;">0</span>
                                </a>
                                <hr>
                                <form method="POST" action="${apiEndpoints.auth.logout}" style="margin: 0;">
                                    <button type="submit" class="auth-logout-btn">
                                        <i class="fas fa-sign-out-alt"></i> Sign Out
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            headerActions.appendChild(authSection);

            // Add click outside listener for user dropdown
            document.addEventListener('click', (e) => {
                const dropdown = document.getElementById('auth-user-menu');
                const btn = document.querySelector('.auth-user-btn');
                if (dropdown && btn && !dropdown.contains(e.target) && !btn.contains(e.target)) {
                    dropdown.classList.remove('active');
                }
            });
        }
    }

    const loginLink = document.getElementById('auth-login-link');
    const userInfo = document.getElementById('auth-user-info');

    if (isAuthenticated && user) {
        // Show user info, hide login link
        if (loginLink) loginLink.style.display = 'none';
        if (userInfo) userInfo.style.display = 'flex';

        // Update user details
        const userName = document.getElementById('auth-user-name');
        const userEmail = document.getElementById('auth-user-email');
        const userId = document.getElementById('auth-user-id');

        if (userName) userName.textContent = user.display_name || user.email.split('@')[0];
        if (userEmail) userEmail.textContent = user.email;
        if (userId) userId.textContent = `ID: ${user.user_id}`;
    } else {
        // Show login link, hide user info
        if (loginLink) loginLink.style.display = 'block';
        if (userInfo) userInfo.style.display = 'none';
    }
}

/**
 * Toggle user dropdown menu
 */
export function toggleUserDropdown() {
    const menu = document.getElementById('auth-user-menu');
    if (menu) {
        menu.classList.toggle('active');
    }
}

/**
 * Load pending invitations count
 */
async function loadPendingInvitations() {
    if (!currentUser) return;

    try {
        const response = await fetch(apiEndpoints.invitations.pending);
        const data = await response.json();

        pendingInvitationsCount = data.count || 0;

        // Update badge
        const badge = document.getElementById('auth-pending-badge');
        if (badge) {
            if (pendingInvitationsCount > 0) {
                badge.textContent = pendingInvitationsCount;
                badge.style.display = 'inline-flex';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading pending invitations:', error);
    }
}

/**
 * View pending invitations - show modal
 */
export function viewPendingInvitations() {
    // Close dropdown
    const menu = document.getElementById('auth-user-menu');
    if (menu) menu.classList.remove('active');

    // Show pending invitations modal
    showPendingInvitationsModal();
}

/**
 * Show pending invitations modal
 */
async function showPendingInvitationsModal() {
    if (!currentUser) return;

    try {
        const response = await fetch(apiEndpoints.invitations.pending);
        const data = await response.json();

        const invitations = data.invitations || [];

        // Create modal if not exists
        let modal = document.getElementById('pending-invitations-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'pending-invitations-modal';
            modal.className = 'modal';
            document.body.appendChild(modal);
        }

        // Build modal content
        let content = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2><i class="fas fa-envelope"></i> Pending Invitations</h2>
                    <button class="modal-close" onclick="closePendingInvitationsModal()">&times;</button>
                </div>
                <div class="modal-body">
        `;

        if (invitations.length === 0) {
            content += `
                <div class="empty-state">
                    <i class="fas fa-envelope-open"></i>
                    <p>No pending invitations</p>
                </div>
            `;
        } else {
            content += `<div class="invitations-list">`;

            for (const inv of invitations) {
                content += `
                    <div class="invitation-card">
                        <div class="invitation-header">
                            <strong>${inv.from_email}</strong>
                            <span class="invitation-date">${new Date(inv.created_at).toLocaleDateString()}</span>
                        </div>
                        ${inv.task_title ? `<div class="invitation-task"><i class="fas fa-tasks"></i> ${inv.task_title}</div>` : ''}
                        ${inv.message ? `<div class="invitation-message">${inv.message}</div>` : ''}
                        <div class="invitation-actions">
                            <button class="btn btn-success btn-sm" onclick="acceptInvitation('${inv.invitation_id}')">
                                <i class="fas fa-check"></i> Accept
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="rejectInvitation('${inv.invitation_id}')">
                                <i class="fas fa-times"></i> Decline
                            </button>
                        </div>
                    </div>
                `;
            }

            content += `</div>`;
        }

        content += `
                </div>
            </div>
        `;

        modal.innerHTML = content;
        modal.classList.add('active');
    } catch (error) {
        console.error('Error showing invitations modal:', error);
        showNotification('Error loading invitations', 'error');
    }
}

/**
 * Close pending invitations modal
 */
export function closePendingInvitationsModal() {
    const modal = document.getElementById('pending-invitations-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

/**
 * Accept an invitation
 * @param {string} invitationId - The invitation ID
 */
export async function acceptInvitation(invitationId) {
    try {
        const response = await fetch(apiEndpoints.invitations.accept(invitationId), {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Invitation accepted! You are now connected.', 'success');
            closePendingInvitationsModal();
            await loadPendingInvitations();
            await checkAuthStatus();
        } else {
            showNotification(data.message || 'Failed to accept invitation', 'error');
        }
    } catch (error) {
        console.error('Error accepting invitation:', error);
        showNotification('Error accepting invitation', 'error');
    }
}

/**
 * Reject an invitation
 * @param {string} invitationId - The invitation ID
 */
export async function rejectInvitation(invitationId) {
    try {
        const response = await fetch(apiEndpoints.invitations.reject(invitationId), {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Invitation declined', 'info');
            closePendingInvitationsModal();
            await loadPendingInvitations();
        } else {
            showNotification(data.message || 'Failed to decline invitation', 'error');
        }
    } catch (error) {
        console.error('Error rejecting invitation:', error);
        showNotification('Error rejecting invitation', 'error');
    }
}

/**
 * View shared tasks
 */
export function viewSharedTasks() {
    // Close dropdown
    const menu = document.getElementById('auth-user-menu');
    if (menu) menu.classList.remove('active');

    // Redirect to shared tasks page or show modal
    window.location.href = `${window.GTASKS_BASE_PATH || ''}/shared-tasks`;
}

// Make auth functions globally available
window.toggleUserDropdown = toggleUserDropdown;
window.viewPendingInvitations = viewPendingInvitations;
window.closePendingInvitationsModal = closePendingInvitationsModal;
window.acceptInvitation = acceptInvitation;
window.rejectInvitation = rejectInvitation;
window.viewSharedTasks = viewSharedTasks;

/**
 * Update statistics
 */
export function updateStats() {
    const stats = dashboardData.stats || {};
    document.getElementById('total-tasks').textContent = stats.total || 0;
    document.getElementById('completed-tasks').textContent = stats.completed || 0;
    document.getElementById('pending-tasks').textContent = stats.pending || 0;
    document.getElementById('critical-tasks').textContent = stats.critical || 0;
    document.getElementById('high-tasks').textContent = stats.high || 0;
    document.getElementById('overdue-tasks').textContent = stats.overdue || 0;

    // Update progress ring
    const completionRate = stats.completion_rate || 0;
    document.getElementById('completion-rate').textContent = Math.round(completionRate) + '%';
    const circle = document.getElementById('completion-ring');
    if (circle) {
        const circumference = 2 * Math.PI * 52;
        const offset = circumference - (completionRate / 100) * circumference;
        circle.style.strokeDasharray = circumference;
        circle.style.strokeDashoffset = offset;
    }
}

/**
 * Update account selectors
 */
export function updateAccountSelectors() {
    const accounts = dashboardData.accounts || [];
    const currentAccount = dashboardData.current_account;

    const selectors = [
        document.getElementById('account-selector'),
        document.getElementById('hierarchy-account-selector'),
        document.getElementById('tasks-account-selector')
    ];

    selectors.forEach(selector => {
        if (selector) {
            selector.innerHTML = accounts.map(acc =>
                `<option value="${acc.id}" ${acc.id === currentAccount ? 'selected' : ''}>${acc.name}</option>`
            ).join('');
        }
    });
}

/**
 * Switch account
 */
export async function switchAccount(accountId) {
    if (!accountId) return;

    showLoading(true);
    try {
        const response = await fetch(apiEndpoints.accountsSwitch(accountId), { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            await loadDashboard();
        }
    } catch (error) {
        console.error('Error switching account:', error);
    } finally {
        showLoading(false);
    }
}

export function switchAccountForHierarchy(accountId) {
    switchAccount(accountId);
}

export function switchAccountForTasks(accountId) {
    switchAccount(accountId);
}

// ========== Tasks ==========

/**
 * Load tasks
 */
export function loadTasks() {
    const tasks = dashboardData.tasks || [];
    const filteredTasks = filterOutDeletedTasks(tasks);
    const container = document.getElementById('tasks-grid');
    if (!container) return;

    container.innerHTML = '';

    // Initialize task count display
    updateTasksCountDisplay(filteredTasks.length, tasks.length);

    if (filteredTasks.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280;">No tasks found for this account.</p>';
        return;
    }

    // Initialize multiselect filters with available options
    initMultiselectFilters(tasks);

    // This function now delegates to the mainTasksView instance
    if (mainTasksView) {
        mainTasksView.loadTasks(dashboardData.tasks || []);
    } else {
        console.warn('mainTasksView not initialized when loadTasks was called.');
    }
}

// Main Tasks View instance
// Main Tasks View instance (moved to top)

// Multi-select instances for filters (now handled inside TasksView, but keeping legacy ref if needed for a moment)
// let listMultiselect = null;
// let tagsMultiselect = null;
let allTasks = []; // Store all tasks for filtering

/**
 * Initialize Main Tasks View (replaces initMultiselectFilters)
 */
export function initMultiselectFilters(tasks) {
    if (!mainTasksView) {
        console.log('[Dashboard] Initializing TasksView from initMultiselectFilters (Search/Filter handled internal to TasksView)');
        mainTasksView = new TasksView('tasks-view-container', {
            idPrefix: 'task',
            data: tasks || [],
            title: 'Task Management',
            hideFilters: false
        });
    } else {
        mainTasksView.loadTasks(tasks || []);
    }
}

/**
 * Update task count display
 * @param {number} filteredCount - Number of filtered tasks
 * @param {number} totalCount - Total number of tasks
 */
export function updateTasksCountDisplay(filteredCount, totalCount) {
    const countDisplay = document.getElementById('tasks-count-display');
    const countText = document.getElementById('tasks-count-text');

    if (countText) {
        if (filteredCount === totalCount) {
            countText.textContent = `Showing all ${totalCount} tasks`;
        } else {
            countText.textContent = `Showing ${filteredCount} of ${totalCount} tasks`;
        }
    }

    if (countDisplay) {
        countDisplay.style.display = 'block';
    }
}

/**
 * Filter tasks with advanced filters
 */
export function filterTasks() {
    if (mainTasksView) mainTasksView.filterTasks();
}

/**
 * Clear all task filters
 */
export function clearTasksFilters() {
    if (mainTasksView) mainTasksView.clearFilters();
}

// ========== Hierarchy ==========

/**
 * Load hierarchy data
 */
export async function loadHierarchy() {
    console.log('[Dashboard] loadHierarchy called');
    try {
        console.log('[Dashboard] Fetching hierarchy data from:', apiEndpoints.hierarchy);
        const response = await fetch(apiEndpoints.hierarchy);
        console.log('[Dashboard] Hierarchy response status:', response.status);
        const data = await response.json();
        console.log('[Dashboard] Hierarchy data received:', data);
        setHierarchyData(data);

        // Update visualization
        console.log('[Dashboard] Calling updateHierarchyViz...');

        // Make sure hierarchyData is set in the renderer module
        console.log('[Dashboard] window.setHierarchyData exists:', typeof window.setHierarchyData);
        if (typeof window.setHierarchyData === 'function') {
            console.log('[Dashboard] Calling window.setHierarchyData...');
            window.setHierarchyData(data);
            console.log('[Dashboard] window.setHierarchyData called successfully');
        } else {
            console.error('[Dashboard] window.setHierarchyData is not a function!');
        }

        if (typeof updateHierarchyViz === 'function') {
            updateHierarchyViz(data);
        } else {
            console.error('[Dashboard] updateHierarchyViz is not a function:', typeof updateHierarchyViz);
        }

        // Initialize filter event listeners
        console.log('[Dashboard] Calling initHierarchyFilters...');
        if (typeof initHierarchyFilters === 'function') {
            window.initHierarchyFilters();
        } else {
            console.error('[Dashboard] initHierarchyFilters is not a function:', typeof initHierarchyFilters);
        }
    } catch (error) {
        console.error('[Dashboard] Error loading hierarchy:', error);
    }
}

/**
 * Refresh hierarchy
 */
export async function refreshHierarchy() {
    await loadHierarchy();
}

// ========== Settings ==========

/**
 * Initialize settings
 */
export function initSettings() {
    const settings = stateManager.getSettings();

    // Update UI
    const toggleElement = document.getElementById('auto-refresh-toggle');
    const intervalSelect = document.getElementById('refresh-interval');
    const viewSelect = document.getElementById('default-view');
    const hideDeletedToggle = document.getElementById('hide-deleted-toggle');

    if (settings.autoRefreshEnabled && toggleElement) {
        toggleElement.classList.add('active');
    }

    if (intervalSelect) {
        intervalSelect.value = settings.refreshInterval / 1000;
    }

    if (viewSelect) {
        viewSelect.value = settings.defaultView;
    }

    if (hideDeletedToggle && settings.hideDeletedEnabled) {
        hideDeletedToggle.classList.add('active');
    }

    // Apply auto-refresh if enabled
    if (settings.autoRefreshEnabled) {
        stateManager.startAutoRefresh(settings.refreshInterval);
    }

    // Apply default view only when accessing root URL (not /dashboard)
    // URL path takes precedence over saved default view setting
    const path = window.location.pathname;

    // Only apply default view on root URL, not on /dashboard
    if (settings.defaultView && settings.defaultView !== 'dashboard' && path === '/') {
        showSection(settings.defaultView, false);
    }
}

export function openSettings() {
    document.getElementById('settings-modal').classList.add('active');
}

export function closeSettings() {
    document.getElementById('settings-modal').classList.remove('active');
}

export function toggleAutoRefresh() {
    const toggleElement = document.getElementById('auto-refresh-toggle');
    const isEnabled = toggleElement.classList.toggle('active');

    stateManager.updateSetting('autoRefreshEnabled', isEnabled);

    const interval = stateManager.getSettings().refreshInterval;

    if (isEnabled) {
        stateManager.startAutoRefresh(interval);
    } else {
        stateManager.stopAutoRefresh();
    }
}

export function updateRefreshInterval() {
    const intervalSelect = document.getElementById('refresh-interval');
    const interval = intervalSelect ? parseInt(intervalSelect.value) * 1000 : 60000;

    stateManager.updateSetting('refreshInterval', interval);

    // Restart auto-refresh with new interval if enabled
    if (stateManager.getSettings().autoRefreshEnabled) {
        stateManager.stopAutoRefresh();
        stateManager.startAutoRefresh(interval);
    }
}

export function updateDefaultView() {
    const viewSelect = document.getElementById('default-view');
    stateManager.updateSetting('defaultView', viewSelect ? viewSelect.value : 'dashboard');
}

export function toggleHideDeleted() {
    const toggleElement = document.getElementById('hide-deleted-toggle');
    const isEnabled = toggleElement.classList.toggle('active');

    stateManager.updateSetting('hideDeletedEnabled', isEnabled);

    // Refresh tasks and hierarchy to apply the filter
    if (mainTasksView) {
        mainTasksView.loadTasks(dashboardData.tasks || []);
    } else {
        loadTasks(); // Fallback to old loadTasks if mainTasksView not initialized
    }

    console.log(`Hide deleted tasks: ${isEnabled ? 'enabled' : 'disabled'}`);
}

// ========== Keyboard Shortcuts ==========

/**
 * Setup keyboard shortcuts
 */
export function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'b') {
            e.preventDefault();
            toggleSidebar();
        }
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            toggleFullscreen();
            // Show filter panel in fullscreen mode
            if (isFullscreen) {
                document.getElementById('hierarchy-filter-panel').style.display = 'flex';
            }
        }
        if (e.key === 'Escape' && isFullscreen) {
            toggleFullscreen();
        }
    });
}

// ========== Initialize ==========

/**
 * Parse URL query parameters
 * @returns {Object} - Key-value pairs of query parameters
 */
export function parseUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const result = {};
    for (const [key, value] of params) {
        result[key] = value;
    }
    return result;
}

/**
 * Apply URL query parameters to dashboard
 */
export function applyUrlParams() {
    const params = parseUrlParams();

    // Handle account parameter
    if (params.account) {
        console.log('[Dashboard] Applying account from URL:', params.account);
        const accountSelector = document.getElementById('account-selector');
        if (accountSelector) {
            // Check if the account exists in the selector
            const options = accountSelector.options;
            let found = false;
            for (let i = 0; i < options.length; i++) {
                if (options[i].value === params.account || options[i].text === params.account) {
                    accountSelector.selectedIndex = i;
                    found = true;
                    break;
                }
            }

            // If not found, still try to switch
            if (!found) {
                console.log('[Dashboard] Account not found in selector, attempting to switch:', params.account);
                switchAccount(params.account);
            } else {
                switchAccount(params.account);
            }
        }
    }

    // Handle default view parameter
    if (params.view) {
        console.log('[Dashboard] Applying view from URL:', params.view);
        if (['dashboard', 'hierarchy', 'tasks'].includes(params.view)) {
            showSection(params.view);
        }
    }
}

/**
 * Initialize the dashboard
 */
export async function initDashboard() {
    console.log('[Dashboard] initDashboard called');

    // Initialize state from storage
    stateManager.initFromStorage();
    stateManager.initDarkMode();

    // Load settings
    initSettings();

    // Setup refresh dropdown click-outside listener
    setupRefreshDropdown();

    // Check authentication status
    await checkAuthStatus();

    // Apply URL query parameters before loading dashboard data
    applyUrlParams();

    // Detect section from URL path (takes precedence over URL params)
    const pathSection = getCurrentSectionFromPath();
    console.log('[Dashboard] Detected section from path:', pathSection);

    // Show the appropriate section based on URL path
    if (pathSection) {
        showSection(pathSection);
    }

    // Load dashboard data
    await loadDashboard();

    // Setup keyboard shortcuts
    setupKeyboardShortcuts();

    console.log('Dashboard initialized');
}

// ========== Chart Filters ==========

/**
 * Toggle chart filter panel visibility
 */
export function toggleChartFilters() {
    const filterPanel = document.getElementById('hierarchy-filter-panel');
    const toggleBtn = document.querySelector('.filter-toggle-btn');

    if (filterPanel.style.display === 'none') {
        filterPanel.style.display = 'flex';
        toggleBtn.classList.add('active');
    } else {
        filterPanel.style.display = 'none';
        toggleBtn.classList.remove('active');
    }
}

/**
 * Apply chart filters - triggers hierarchy refresh
 */
export function applyChartFilters() {
    console.log('[Dashboard] applyChartFilters called');
    console.log('[Dashboard] typeof refreshHierarchyVisualization:', typeof refreshHierarchyVisualization);
    if (typeof refreshHierarchyVisualization === 'function') {
        console.log('[Dashboard] Calling refreshHierarchyVisualization...');
        refreshHierarchyVisualization();
    } else {
        console.error('[Dashboard] refreshHierarchyVisualization is not a function!');
        // Try calling window.refreshHierarchyVisualization as fallback
        if (typeof window.refreshHierarchyVisualization === 'function') {
            console.log('[Dashboard] Calling window.refreshHierarchyVisualization...');
            window.refreshHierarchyVisualization();
        }
    }
}

/**
 * Clear chart filters
 */
export function clearChartFilters() {
    // Reset hierarchy filter inputs
    const tagSearchInput = document.getElementById('hierarchy-tag-search');
    const statusFilter = document.getElementById('hierarchy-status-filter');
    const dateStartInput = document.getElementById('hierarchy-date-start');
    const dateEndInput = document.getElementById('hierarchy-date-end');

    if (tagSearchInput) tagSearchInput.value = '';
    if (statusFilter) statusFilter.value = '';
    if (dateStartInput) dateStartInput.value = '';
    if (dateEndInput) dateEndInput.value = '';

    // Refresh visualization
    if (typeof refreshHierarchyVisualization === 'function') {
        refreshHierarchyVisualization();
    }
}

/**
 * Clear all node filters
 */
export function clearNodeFilters() {
    // Reset status filter
    const statusFilter = document.getElementById('node-task-status-filter');
    if (statusFilter) statusFilter.value = '';

    // Reset priority filter
    const priorityFilter = document.getElementById('node-task-priority-filter');
    if (priorityFilter) priorityFilter.value = '';

    // Reset search filter
    const searchFilter = document.getElementById('node-task-search-filter');
    if (searchFilter) searchFilter.value = '';

    // Reset project filter
    const projectFilter = document.getElementById('node-task-project-filter');
    if (projectFilter) projectFilter.value = '';

    // Reset tags filter
    const tagsFilter = document.getElementById('node-task-tags-filter');
    if (tagsFilter) tagsFilter.value = '';

    // Reset date field filter
    const dateFieldFilter = document.getElementById('node-task-date-field');
    if (dateFieldFilter) dateFieldFilter.value = 'due';

    // Reset date range filters
    const dateStartFilter = document.getElementById('node-task-date-start');
    if (dateStartFilter) dateStartFilter.value = '';

    const dateEndFilter = document.getElementById('node-task-date-end');
    if (dateEndFilter) dateEndFilter.value = '';

    // Reset sort field
    const sortFieldFilter = document.getElementById('node-task-sort-field');
    if (sortFieldFilter) sortFieldFilter.value = 'due';

    // Reset sort order
    const sortOrderFilter = document.getElementById('node-task-sort-order');
    if (sortOrderFilter) sortOrderFilter.value = 'desc';

    // Re-apply filters if a node is selected
    const node = getSelectedNode();
    if (node) {
        if (typeof window.filterNodeTasksHierarchy === 'function') {
            window.filterNodeTasksHierarchy(node);
        }
    }
}

/**
 * Toggle task filters visibility (for dashboard.html fallback)
 */
export function toggleTaskFilters() {
    const container = document.getElementById('task-filters-container');
    const btn = document.getElementById('task-filter-toggle');
    const icon = btn ? (btn.querySelector('i') || btn.querySelector('svg')) : null;

    if (container && btn) {
        container.classList.toggle('collapsed');
        if (container.classList.contains('collapsed')) {
            if (icon) {
                icon.className = 'fas fa-filter';
            }
            btn.title = "Show Advanced Filters";
            btn.classList.remove('active');
        } else {
            if (icon) {
                icon.className = 'fas fa-chevron-up';
            }
            btn.title = "Hide Advanced Filters";
            btn.classList.add('active');
        }
    }
}

// ========== Complete Task ==========

/**
 * Mark a task as complete
 * @param {string} taskId - The task ID to complete
 */
export async function completeTask(taskId) {
    console.log('[Dashboard] Completing task:', taskId);

    try {
        const basePath = window.GTASKS_BASE_PATH || '';
        const response = await fetch(`${basePath}/api/tasks/${taskId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (data.success) {
            console.log('Task completed:', taskId);

            // Update UI - change task appearance to completed (no full reload)
            updateTaskCompletedState(taskId);

            // Show success feedback
            showNotification('Task completed ✅', 'success');

            // Update stats in place without full dashboard reload
            updateStatsInPlace(taskId);
        } else {
            showNotification(data.message || 'Failed to complete task', 'error');
        }
    } catch (error) {
        console.error('Error completing task:', error);
        showNotification('Error completing task', 'error');
    }
}

/**
 * Update stats in place after task completion (no full reload)
 * @param {string} taskId - The completed task ID
 */
function updateStatsInPlace(taskId) {
    const stats = dashboardData.stats || {};

    // Update counters
    const completedEl = document.getElementById('completed-tasks');
    const pendingEl = document.getElementById('pending-tasks');

    if (completedEl) {
        const currentCompleted = parseInt(completedEl.textContent) || 0;
        completedEl.textContent = currentCompleted + 1;
    }

    if (pendingEl) {
        const currentPending = parseInt(pendingEl.textContent) || 0;
        pendingEl.textContent = Math.max(0, currentPending - 1);
    }

    // Update completion rate
    const completionRateEl = document.getElementById('completion-rate');
    const totalEl = document.getElementById('total-tasks');

    if (completionRateEl && totalEl) {
        const total = parseInt(totalEl.textContent) || 1;
        const completed = parseInt(completedEl?.textContent) || 0;
        const rate = (completed / total) * 100;
        completionRateEl.textContent = Math.round(rate) + '%';

        // Update progress ring
        const circle = document.getElementById('completion-ring');
        if (circle) {
            const circumference = 2 * Math.PI * 52;
            const offset = circumference - (rate / 100) * circumference;
            circle.style.strokeDasharray = circumference;
            circle.style.strokeDashoffset = offset;
        }
    }
}

/**
 * Update task UI to show completed state
 * @param {string} taskId - The task ID that was completed
 */
export function updateTaskCompletedState(taskId) {
    // Update in tasks grid
    const taskElement = document.querySelector(`.task-card[data-task-id="${taskId}"]`);
    if (taskElement) {
        taskElement.classList.add('completed');
        const completeBtn = taskElement.querySelector('.task-complete-btn');
        if (completeBtn) {
            completeBtn.innerHTML = '✅';
            completeBtn.title = 'Completed';
            completeBtn.onclick = null;
            completeBtn.style.cursor = 'default';
        }
    }

    // Update in hierarchy task panel (node-task-card)
    const nodeTaskElement = document.querySelector(`.node-task-card[data-task-id="${taskId}"]`);
    if (nodeTaskElement) {
        nodeTaskElement.classList.add('completed');
        const completeBtn = nodeTaskElement.querySelector('.task-complete-btn');
        if (completeBtn) {
            completeBtn.innerHTML = '✅';
            completeBtn.title = 'Completed';
            completeBtn.onclick = null;
            completeBtn.style.cursor = 'default';
        }
        // Update status badge
        const statusElement = nodeTaskElement.querySelector('.node-task-status');
        if (statusElement) {
            statusElement.textContent = 'completed';
            statusElement.classList.add('status-completed');
        }
    }
}

/**
 * Show notification
 * @param {string} message - The message to show
 * @param {string} type - The notification type ('success' or 'error')
 */
function showNotification(message, type = 'success') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 14px 28px;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        font-size: 15px;
        z-index: 100000;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        ${type === 'success' ? 'background: linear-gradient(135deg, #10b981, #059669);' : 'background: linear-gradient(135deg, #ef4444, #dc2626);'}
    `;
    notification.innerHTML = `
        <span style="margin-right: 10px;">${type === 'success' ? '✅' : '❌'}</span>
        ${message}
    `;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        notification.style.transition = 'all 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Make functions globally available for backward compatibility
window.showLoading = showLoading;
window.showSection = showSection;
window.toggleSidebar = toggleSidebar;
window.toggleFullscreen = toggleFullscreen;
window.loadDashboard = loadDashboard;
window.updateStats = updateStats;
window.updateAccountSelectors = updateAccountSelectors;
window.switchAccount = switchAccount;
window.switchAccountForHierarchy = switchAccountForHierarchy;
window.switchAccountForTasks = switchAccountForTasks;
window.loadTasks = loadTasks;
window.filterTasks = filterTasks;
window.clearTasksFilters = clearTasksFilters;
window.refreshData = simpleCacheRefresh;  // Use simple cache refresh instead of full sync
window.refreshHierarchy = refreshHierarchy;
window.loadHierarchy = loadHierarchy;
window.initSettings = initSettings;
window.openSettings = openSettings;
window.closeSettings = closeSettings;
window.toggleAutoRefresh = toggleAutoRefresh;
window.updateRefreshInterval = updateRefreshInterval;
window.updateDefaultView = updateDefaultView;
window.toggleHideDeleted = toggleHideDeleted;
window.setupKeyboardShortcuts = setupKeyboardShortcuts;
window.toggleChartFilters = toggleChartFilters;
window.applyChartFilters = applyChartFilters;
window.clearChartFilters = clearChartFilters;
window.clearNodeFilters = clearNodeFilters;
window.completeTask = completeTask;
window.updateTaskCompletedState = updateTaskCompletedState;
window.toggleDarkMode = stateManager.toggleDarkMode;
window.showNotification = showNotification;
window.parseUrlParams = parseUrlParams;
window.applyUrlParams = applyUrlParams;
window.updateTasksCountDisplay = updateTasksCountDisplay;
window.getCurrentSectionFromPath = getCurrentSectionFromPath;
window.updateNavActiveState = updateNavActiveState;
window.startAdvancedSync = startAdvancedSync;
window.updateSyncProgressUI = updateSyncProgressUI;
window.stopSyncProgressUI = stopSyncProgressUI;
window.refreshWithAdvancedSync = refreshWithAdvancedSync;
window.simpleCacheRefresh = simpleCacheRefresh;
window.toggleRefreshDropdown = toggleRefreshDropdown;
window.syncAndRefresh = syncAndRefresh;
window.syncRemoteDb = syncRemoteDb;
window.setupRefreshDropdown = setupRefreshDropdown;
window.getListsWithCounts = getListsWithCounts;
window.getTagsWithCounts = getTagsWithCounts;
window.toggleTaskFilters = toggleTaskFilters;


// ========== Settings Submenu Functions ==========

/**
 * Toggle settings dropdown submenu
 * @param {Event} event - The click event
 */
export function toggleSettingsDropdown(event) {
    event.preventDefault();
    event.stopPropagation();

    const dropdown = document.getElementById('nav-settings-dropdown');
    const submenu = document.getElementById('settings-submenu');

    if (dropdown && submenu) {
        dropdown.classList.toggle('open');
        submenu.classList.toggle('open');

        // Update arrow icon
        const arrow = dropdown.querySelector('.dropdown-arrow');
        if (arrow) {
            if (dropdown.classList.contains('open')) {
                arrow.classList.remove('fa-chevron-down');
                arrow.classList.add('fa-chevron-up');
            } else {
                arrow.classList.remove('fa-chevron-up');
                arrow.classList.add('fa-chevron-down');
            }
        }
    }
}

/**
 * Show Tags Import section
 */
export function showTagsImport() {
    console.log('[Dashboard] showTagsImport called - navigating to /settings/tags-import');
    window.location.href = `${window.GTASKS_BASE_PATH || ''}/settings/tags-import`;
}

/**
 * Show Tags Management section
 */
export function showTagsManagement() {
    console.log('[Dashboard] showTagsManagement called - navigating to /settings/tags-management');
    window.location.href = `${window.GTASKS_BASE_PATH || ''}/settings/tags-management`;
}

/**
 * Show Connected Accounts section
 */
export function showConnectedAccounts() {
    console.log('[Dashboard] showConnectedAccounts called - navigating to /settings/connected-accounts');
    window.location.href = `${window.GTASKS_BASE_PATH || ''}/settings/connected-accounts`;
}

/**
 * Show Remote Sync section
 */
export function showRemoteSync() {
    console.log('[Dashboard] showRemoteSync called - navigating to /settings/remote-sync');
    window.location.href = `${window.GTASKS_BASE_PATH || ''}/settings/remote-sync`;
}

/**
 * Close settings submenu
 */
function closeSettingsSubmenu() {
    const dropdown = document.getElementById('nav-settings-dropdown');
    const submenu = document.getElementById('settings-submenu');

    if (dropdown && submenu) {
        dropdown.classList.remove('open');
        submenu.classList.remove('open');

        // Reset arrow icon
        const arrow = dropdown.querySelector('.dropdown-arrow');
        if (arrow) {
            arrow.classList.remove('fa-chevron-up');
            arrow.classList.add('fa-chevron-down');
        }
    }
}

/**
 * Hide all sections
 */
export function hideAllSections() {
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => {
        section.style.display = 'none';
    });

    // Remove active state from nav items
    document.querySelectorAll('.nav-item').forEach(nav => {
        nav.classList.remove('active');
    });
}

// Make settings submenu functions globally available
window.toggleSettingsDropdown = toggleSettingsDropdown;
window.showTagsImport = showTagsImport;
window.showTagsManagement = showTagsManagement;
window.showConnectedAccounts = showConnectedAccounts;
window.showRemoteSync = showRemoteSync;
window.hideAllSections = hideAllSections;

// ========== Tags Import Functions ==========

/**
 * Load tags for import
 */
export function loadTagsForImport() {
    console.log('[Dashboard] Loading tags for import...');

    const resultsContainer = document.getElementById('tags-import-results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '<div class="loading-spinner"></div><p>Loading tags...</p>';
    }

    // Fetch tags from API
    fetch(apiEndpoints.tags)
        .then(response => response.json())
        .then(data => {
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="tags-import-summary">
                        <h3>Available Tags</h3>
                        <p>Total tags: ${data.tags ? data.tags.length : 0}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error loading tags:', error);
            if (resultsContainer) {
                resultsContainer.innerHTML = '<p class="error">Error loading tags</p>';
            }
        });
}

/**
 * View tag statistics
 */
export function viewTagStatistics() {
    console.log('[Dashboard] Viewing tag statistics...');

    // Fetch statistics from API
    fetch(`${apiEndpoints.tags}/statistics`)
        .then(response => response.json())
        .then(data => {
            const resultsContainer = document.getElementById('tags-import-results');
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="tag-statistics">
                        <h3>Tag Statistics</h3>
                        <div class="statistics-grid">
                            <div class="stat-item">
                                <span class="stat-value">${data.total_tags || 0}</span>
                                <span class="stat-label">Total Tags</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${data.account_tags || 0}</span>
                                <span class="stat-label">Account Tags</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${data.regular_tags || 0}</span>
                                <span class="stat-label">Regular Tags</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${data.used_tags || 0}</span>
                                <span class="stat-label">Used Tags</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${data.unused_tags || 0}</span>
                                <span class="stat-label">Unused Tags</span>
                            </div>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error fetching statistics:', error);
            showNotification('Error fetching tag statistics', 'error');
        });
}

/**
 * Dry run for tags import
 */
export function importTagsDryRun() {
    console.log('[Dashboard] Running tags import dry run...');

    const resultsContainer = document.getElementById('tags-import-results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '<div class="loading-spinner"></div><p>Running dry run...</p>';
    }

    fetch(`${apiEndpoints.tags}/dry-run`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="tags-import-dry-run">
                        <h3>Dry Run Results</h3>
                        <p>Tags to import: ${data.tags_to_import || 0}</p>
                        <p>Tags to update: ${data.tags_to_update || 0}</p>
                        <p>Tags to skip: ${data.tags_to_skip || 0}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error in dry run:', error);
            if (resultsContainer) {
                resultsContainer.innerHTML = '<p class="error">Error running dry run</p>';
            }
        });
}

/**
 * Import tags from Google Tasks
 */
export function importTagsFromGoogle() {
    console.log('[Dashboard] Importing tags from Google Tasks...');

    const resultsContainer = document.getElementById('tags-import-results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '<div class="loading-spinner"></div><p>Importing tags...</p>';
    }

    fetch(apiEndpoints.tags, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Successfully imported ${data.imported_count} tags`, 'success');
                if (resultsContainer) {
                    resultsContainer.innerHTML = `
                        <div class="tags-import-success">
                            <h3>Import Complete</h3>
                            <p>Tags imported: ${data.imported_count || 0}</p>
                            <p>Tags updated: ${data.updated_count || 0}</p>
                            <p>Errors: ${data.error_count || 0}</p>
                        </div>
                    `;
                }
            } else {
                showNotification(data.message || 'Import failed', 'error');
                if (resultsContainer) {
                    resultsContainer.innerHTML = '<p class="error">Import failed</p>';
                }
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error importing tags:', error);
            showNotification('Error importing tags', 'error');
            if (resultsContainer) {
                resultsContainer.innerHTML = '<p class="error">Error importing tags</p>';
            }
        });
}

/**
 * Sync tags with tasks
 */
export function syncTags() {
    console.log('[Dashboard] Syncing tags...');

    const resultsContainer = document.getElementById('tags-import-results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '<div class="loading-spinner"></div><p>Syncing tags...</p>';
    }

    fetch(`${apiEndpoints.tags}/sync`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Tags synced successfully', 'success');
                if (resultsContainer) {
                    resultsContainer.innerHTML = `
                        <div class="tags-sync-success">
                            <h3>Sync Complete</h3>
                            <p>Tags synced: ${data.synced_count || 0}</p>
                        </div>
                    `;
                }
            } else {
                showNotification(data.message || 'Sync failed', 'error');
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error syncing tags:', error);
            showNotification('Error syncing tags', 'error');
        });
}

// Make tags import functions globally available
window.loadTagsForImport = loadTagsForImport;
window.viewTagStatistics = viewTagStatistics;
window.importTagsDryRun = importTagsDryRun;
window.importTagsFromGoogle = importTagsFromGoogle;
window.syncTags = syncTags;

// ========== Tags Management Functions ==========

/**
 * Load tags management
 */
export function loadTagsManagement() {
    console.log('[Dashboard] Loading tags management...');

    const listContainer = document.getElementById('tags-management-list');
    if (listContainer) {
        listContainer.innerHTML = '<div class="loading-spinner"></div><p>Loading tags...</p>';
    }

    // Fetch all tags from API
    fetch(apiEndpoints.tags)
        .then(response => response.json())
        .then(data => {
            const tags = data.tags || [];

            if (listContainer) {
                if (tags.length === 0) {
                    listContainer.innerHTML = '<p class="empty-state">No tags found</p>';
                } else {
                    listContainer.innerHTML = `
                        <div class="tags-list">
                            ${tags.map(tag => `
                                <div class="tag-item" data-tag-id="${tag.id}">
                                    <span class="tag-name">${tag.name}</span>
                                    <span class="tag-type">${tag.is_account ? 'Account' : 'Regular'}</span>
                                    <span class="tag-count">${tag.usage_count || 0} tasks</span>
                                    <div class="tag-actions">
                                        <button class="btn btn-sm" onclick="editTag('${tag.id}')">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                        <button class="btn btn-sm" onclick="deleteTag('${tag.id}')">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error loading tags:', error);
            if (listContainer) {
                listContainer.innerHTML = '<p class="error">Error loading tags</p>';
            }
        });
}

// Make tags management functions globally available
window.loadTagsManagement = loadTagsManagement;

// ========== Connected Accounts Functions ==========

/**
 * Load connected accounts
 */
export function loadConnectedAccounts() {
    console.log('[Dashboard] Loading connected accounts...');

    const listContainer = document.getElementById('connected-accounts-list');
    if (listContainer) {
        listContainer.innerHTML = '<div class="loading-spinner"></div><p>Loading connected accounts...</p>';
    }

    // Fetch connected accounts from API
    fetch(apiEndpoints.connections)
        .then(response => response.json())
        .then(data => {
            const connections = data.connections || [];

            if (listContainer) {
                if (connections.length === 0) {
                    listContainer.innerHTML = '<p class="empty-state">No connected accounts found</p>';
                } else {
                    listContainer.innerHTML = `
                        <div class="connections-list">
                            ${connections.map(conn => `
                                <div class="connection-item" data-connection-id="${conn.id}">
                                    <div class="connection-info">
                                        <span class="connection-email">${conn.email}</span>
                                        <span class="connection-user-id">ID: ${conn.user_id}</span>
                                    </div>
                                    <span class="connection-status">${conn.status}</span>
                                    <div class="connection-actions">
                                        <button class="btn btn-sm" onclick="viewConnection('${conn.id}')">
                                            <i class="fas fa-eye"></i>
                                        </button>
                                        <button class="btn btn-sm" onclick="disconnectUser('${conn.id}')">
                                            <i class="fas fa-unlink"></i>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error loading connections:', error);
            if (listContainer) {
                listContainer.innerHTML = '<p class="error">Error loading connected accounts</p>';
            }
        });
}

// Make connected accounts functions globally available
window.loadConnectedAccounts = loadConnectedAccounts;

// ========== Remote Sync Functions ==========

/**
 * Load remote sync status
 */
export function loadRemoteSync() {
    console.log('[Dashboard] Loading remote sync status...');

    const statusContainer = document.getElementById('remote-sync-status');
    if (statusContainer) {
        statusContainer.innerHTML = '<div class="loading-spinner"></div><p>Loading sync status...</p>';
    }

    // Fetch remote sync status from API
    fetch(apiEndpoints.sync.status)
        .then(response => response.json())
        .then(data => {
            if (statusContainer) {
                statusContainer.innerHTML = `
                    <div class="sync-status-info">
                        <h3>Sync Status</h3>
                        <div class="status-item">
                            <span class="status-label">Status:</span>
                            <span class="status-value status-${data.status}">${data.status || 'unknown'}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Last Sync:</span>
                            <span class="status-value">${data.last_sync || 'Never'}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Next Sync:</span>
                            <span class="status-value">${data.next_sync || 'Not scheduled'}</span>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error loading sync status:', error);
            if (statusContainer) {
                statusContainer.innerHTML = '<p class="error">Error loading sync status</p>';
            }
        });
}

/**
 * Start remote sync
 */
export function startRemoteSync() {
    console.log('[Dashboard] Starting remote sync...');
    showNotification('Starting remote sync...', 'info');

    fetch(apiEndpoints.sync.remote, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Remote sync started successfully', 'success');
                loadRemoteSync();
            } else {
                showNotification(data.message || 'Failed to start sync', 'error');
            }
        })
        .catch(error => {
            console.error('[Dashboard] Error starting sync:', error);
            showNotification('Error starting remote sync', 'error');
        });
}

/**
 * Configure remote sync
 */
export function configureRemoteSync() {
    console.log('[Dashboard] Configuring remote sync...');
    showNotification('Remote sync configuration coming soon', 'info');
}

// Make remote sync functions globally available
window.loadRemoteSync = loadRemoteSync;
window.startRemoteSync = startRemoteSync;
window.configureRemoteSync = configureRemoteSync;
window.toggleDarkMode = () => stateManager.toggleDarkMode();

// ========== Placeholder Functions for Tag Management and Connections ==========

export function editTag(tagId) {
    console.log('[Dashboard] Editing tag:', tagId);
    showNotification('Tag editing coming soon', 'info');
}

export function deleteTag(tagId) {
    console.log('[Dashboard] Deleting tag:', tagId);
    if (confirm('Are you sure you want to delete this tag?')) {
        fetch(`${apiEndpoints.tags}/${tagId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Tag deleted successfully', 'success');
                    loadTagsManagement();
                } else {
                    showNotification(data.message || 'Failed to delete tag', 'error');
                }
            })
            .catch(error => {
                console.error('[Dashboard] Error deleting tag:', error);
                showNotification('Error deleting tag', 'error');
            });
    }
}

export function viewConnection(connectionId) {
    console.log('[Dashboard] Viewing connection:', connectionId);
    showNotification('Connection details coming soon', 'info');
}

export function disconnectUser(connectionId) {
    console.log('[Dashboard] Disconnecting user:', connectionId);
    if (confirm('Are you sure you want to disconnect this user?')) {
        fetch(`${apiEndpoints.connections}/${connectionId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('User disconnected successfully', 'success');
                    loadConnectedAccounts();
                } else {
                    showNotification(data.message || 'Failed to disconnect user', 'error');
                }
            })
            .catch(error => {
                console.error('[Dashboard] Error disconnecting user:', error);
                showNotification('Error disconnecting user', 'error');
            });
    }
}

// Make placeholder functions globally available
window.editTag = editTag;
window.deleteTag = deleteTag;
window.viewConnection = viewConnection;
window.disconnectUser = disconnectUser;
window.disconnectUser = disconnectUser;

/**
 * Open Task Details Modal
 * @param {Object} task - The task object
 */
export function openTaskDetailsModal(task) {
    if (!task) return;

    // Populate Modal Content
    document.getElementById('modal-task-title').textContent = task.title || 'No Title';

    const notesEl = document.getElementById('modal-task-notes');
    notesEl.textContent = task.notes || task.description || 'No notes available.';

    // Status Badge
    const statusEl = document.getElementById('modal-task-status');
    statusEl.textContent = task.status || 'pending';
    statusEl.className = `task-status-badge status-${(task.status || 'pending').toLowerCase().replace(' ', '-')}`;

    // Priority Badge
    const priorityEl = document.getElementById('modal-task-priority');
    priorityEl.textContent = task.calculated_priority || task.priority || 'No Priority';
    priorityEl.className = `task-priority-badge priority-${(task.calculated_priority || task.priority || 'medium').toLowerCase()}`;

    // Due Date
    const dueEl = document.getElementById('modal-task-due');
    if (task.due) {
        dueEl.innerHTML = `<i class="fas fa-calendar"></i> Due: ${new Date(task.due).toLocaleDateString()} ${new Date(task.due).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        dueEl.style.display = 'flex';
    } else {
        dueEl.style.display = 'none';
    }

    // Tags
    const tagsContainer = document.getElementById('modal-task-tags');
    tagsContainer.innerHTML = '';

    // Regular Tags
    if (task.tags && task.tags.length > 0) {
        task.tags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'task-tag regular-tag';
            tagEl.innerHTML = `<i class="fas fa-hashtag"></i> ${tag}`;
            tagsContainer.appendChild(tagEl);
        });
    }

    // Account Tags
    if (task.account_tags && task.account_tags.length > 0) {
        task.account_tags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'task-tag account-tag';
            tagEl.innerHTML = `<i class="fas fa-user-tag"></i> ${tag}`;
            tagsContainer.appendChild(tagEl);
        });
    }

    if (tagsContainer.children.length === 0) {
        tagsContainer.innerHTML = '<span style="color: #9ca3af; font-style: italic;">No tags</span>';
    }

    // Meta Info
    document.getElementById('modal-task-list').textContent = task.list_title || task.parent || 'N/A';
    document.getElementById('modal-task-account').textContent = task.account || 'N/A';
    document.getElementById('modal-task-updated').textContent = task.updated ? new Date(task.updated).toLocaleString() : 'N/A';

    // Show Modal
    const overlay = document.getElementById('task-details-modal');
    overlay.style.display = 'flex';
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

export function closeTaskDetailsModal() {
    const overlay = document.getElementById('task-details-modal');
    overlay.classList.remove('active');
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300);
}

window.openTaskDetailsModal = openTaskDetailsModal;
window.closeTaskDetailsModal = closeTaskDetailsModal;
// Export for use in other modules
export default {
    initDashboard,
    loadDashboard,
    updateStats,
    showSection,
    toggleSidebar,
    toggleFullscreen,
    switchAccount,
    loadTasks,
    filterTasks: () => mainTasksView?.filterTasks(),
    loadHierarchy,
    simpleCacheRefresh
};

// Initialize the dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Add event listener to track clicks on settings dropdown items
    const settingsSubmenu = document.getElementById('settings-submenu');
    if (settingsSubmenu) {
        settingsSubmenu.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link) {
                console.log('[Dashboard] Settings dropdown item clicked:', link.textContent.trim());
                console.log('[Dashboard] onclick attribute:', link.getAttribute('onclick'));
            }
        });
    }

    // Initialize the dashboard
    initDashboard();

    console.log('[Dashboard] All functions exported to window:');
    console.log('[Dashboard] openSettings:', typeof window.openSettings);
    console.log('[Dashboard] showTagsImport:', typeof window.showTagsImport);
    console.log('[Dashboard] showTagsManagement:', typeof window.showTagsManagement);
    console.log('[Dashboard] showConnectedAccounts:', typeof window.showConnectedAccounts);
    console.log('[Dashboard] showRemoteSync:', typeof window.showRemoteSync);
    console.log('[Dashboard] hideAllSections:', typeof window.hideAllSections);
});
