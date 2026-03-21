# GTasks Dashboard - Modular Architecture

A modern, modular GTasks dashboard with enhanced functionality and clean architecture.

## 🏗️ Architecture

The dashboard is now organized into separate, focused modules:

```
gtasks_dashboard/
├── gtasks_dashboard.py      # Main orchestrator (47 lines)
├── data_manager.py          # Data handling (400+ lines)
├── api_handlers.py          # API routes (200+ lines)
├── ui_components.py         # UI templates (600+ lines)
├── config.py               # Configuration (100+ lines)
└── README.md               # This file
```

## ✨ Key Improvements

### 1. **Modular Architecture**
- **Separation of Concerns**: Each module has a single responsibility
- **Maintainability**: Easy to update and debug individual components
- **Testability**: Components can be tested independently

### 2. **Sidebar Hide Functionality**
- **Toggle Button**: Hamburger menu in header
- **Smooth Animations**: CSS transitions for professional feel
- **Persistence**: User preference saved in localStorage
- **Responsive**: Works on all screen sizes

### 3. **Data Display Fixes**
- **API Response Structure**: Properly formatted JSON responses
- **Error Handling**: Graceful fallbacks for missing data
- **Loading States**: Visual feedback during data loading
- **Real-time Updates**: Auto-refresh every 60 seconds

### 4. **Enhanced Features**
- **Account Switching**: Dynamic account selection
- **Advanced Filtering**: Multi-criteria task filtering
- **Export Functionality**: JSON export of all tasks
- **Settings Management**: Persistent user preferences

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup script
chmod +x setup.sh
./setup.sh

# The script will:
# 1. Set up Python virtual environment
# 2. Install dependencies
# 3. Ask for your GTasks account name
# 4. Create the account directory in ~/.gtasks/
```

### Option 2: Manual Setup

#### Step 1: Set up Python environment
```bash
# Create virtual environment
python3 -m venv gtasks-dashboard

# Activate it
source gtasks-dashboard/bin/activate

# Install dependencies
pip install -r requirements-python.txt
```

#### Step 2: Install GTasks CLI (for remote sync)
```bash
cd ../gtasks_cli
pip install -e .
```

#### Step 3: Create your account directory
```bash
# Replace 'Work' with your preferred account name
mkdir -p ~/.gtasks/Work

# Sync with Google Tasks
gtasks advanced-sync

# Copy tasks to your account
cp ~/.gtasks/tasks.db ~/.gtasks/Work/tasks.db
```

#### Step 4: Run the Dashboard
```bash
cd ../gtasks_dashboard
python main_dashboard.py
```

### 2. **Access the Dashboard**
- Open browser to `http://localhost:8081`
- Click the hamburger menu (☰) to hide/show sidebar
- Use the refresh button to manually update data

### 3. **Features Available**
- ✅ **Dashboard Overview**: Statistics and quick charts
- ✅ **Task Management**: Full CRUD operations
- ✅ **Hierarchical Visualization**: Interactive D3.js graphs
- ✅ **Account Management**: Multi-account support
- ✅ **Reports**: Productivity and distribution analytics
- ✅ **Settings**: User preferences and configuration

## 📱 UI/UX Improvements

### Sidebar Toggle
- **Location**: Top-left header with hamburger icon
- **Animation**: Smooth 300ms transitions
- **State**: Maintains visibility preference
- **Responsive**: Collapses on mobile devices

### Data Display
- **Real-time Updates**: Automatic data refresh
- **Error Handling**: Graceful degradation
- **Loading States**: Visual feedback
- **Data Validation**: Ensures data integrity

### Navigation
- **Single Page Application**: Smooth page transitions
- **Active States**: Visual indication of current page
- **Breadcrumbs**: Clear navigation context
- **Search**: Global task search functionality

## 🔧 Technical Details

### Dependencies
```python
Flask==2.3.3
sqlite3 (built-in)
pathlib (built-in)
threading (built-in)
```

### Configuration
- **Port**: Configurable via command line or config.py
- **Refresh Interval**: 60 seconds (configurable)
- **Theme**: Light mode (extensible for dark mode)
- **Animations**: Enabled by default

### API Endpoints
```
GET  /                     # Main dashboard
GET  /api/dashboard        # Dashboard data
GET  /api/tasks           # Tasks with filtering
POST /api/refresh          # Manual data refresh
POST /api/switch_account   # Account switching
GET  /api/export          # Export all tasks
```

## 🎯 Fixes Implemented

### 1. **Sidebar Hide Functionality**
- ✅ Added toggle button in header
- ✅ Smooth CSS animations
- ✅ LocalStorage persistence
- ✅ Mobile responsive design

### 2. **Data Display Issues**
- ✅ Fixed API response structure
- ✅ Improved JavaScript data handling
- ✅ Added error boundaries
- ✅ Enhanced loading states

### 3. **Code Organization**
- ✅ Modular architecture
- ✅ Separation of concerns
- ✅ Configuration management
- ✅ Error handling

## 📊 Data Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI Components │◄──►│   API Handlers │◄──►│  Data Manager   │
│                 │    │                 │    │                 │
│ • HTML Templates│    │ • Flask Routes │    │ • Data Loading  │
│ • JavaScript    │    │ • Request/Resp │    │ • Processing    │
│ • CSS Styles    │    │ • Validation   │    │ • Hierarchy     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔄 Real-time Updates

- **Interval**: 60 seconds (configurable)
- **Background Thread**: Non-blocking updates
- **Error Handling**: Automatic retry on failure
- **User Feedback**: Console logging for debugging

## 🛠️ Development

### Adding New Features
1. **Data Logic**: Add to `data_manager.py`
2. **API Endpoint**: Add to `api_handlers.py`
3. **UI Component**: Add to `ui_components.py`
4. **Configuration**: Update `config.py`

### Testing
```bash
# Test the dashboard
python gtasks_dashboard.py 8081

# Test API endpoints
curl http://localhost:8081/api/dashboard

# Check logs
python gtasks_dashboard.py 8081 2>&1 | tee dashboard.log
```

## 📝 Migration from Old Version

The refactored dashboard maintains full compatibility with:
- Existing GTasks data structures
- Current API endpoints
- User settings and preferences
- Browser bookmarks and workflows

## 🎉 Success Metrics

- **Code Quality**: Reduced from 1523 lines to modular components
- **Maintainability**: Each module <500 lines, single responsibility
- **User Experience**: Smooth sidebar animations, responsive design
- **Performance**: Efficient data loading, background updates
- **Reliability**: Error handling, graceful degradation

## 🔄 Remote Sync Features

The dashboard supports two types of sync:

### 1. Google Tasks Sync (Local ↔ Google)

Sync your tasks with Google Tasks API:

```bash
# Run advanced sync with Google
gtasks advanced-sync

# Or use basic sync
gtasks sync
```

### 2. Turso Remote Sync (Local ↔ Cloud)

Sync your tasks with a Turso cloud database for multi-device access:

```bash
# Quick setup (see full guide: ../REMOTE_SYNC_README.md)
export GTASKS_TURSO_TOKEN="your-token"
gtasks remote add "libsql://your-db.turso.io" "My Tasks"
gtasks remote sync
```

### Dashboard Sync UI

The dashboard includes visual sync indicators:

| Feature | Description |
|---------|-------------|
| **Status Indicator** | Shows connected/disconnected status |
| **Sync Button** | Manual trigger for remote sync |
| **Last Sync Time** | Shows when data was last synced |
| **DB Count** | Number of configured remote databases |

### API Endpoints for Remote Sync

```
GET  /api/remote/status          - Get connection status
GET  /api/remote/databases      - List configured databases
POST /api/remote/sync           - Start sync operation
POST /api/remote/push           - Push to remote
POST /api/remote/pull           - Pull from remote
```

### Setup for Remote Sync

1. **Create Turso Database**
   ```bash
   # Install Turso CLI
   brew install tursodatabase/tap/turso
   
   # Create database
   turso db create my-gtasks --region ap-south-1
   ```

2. **Configure Token**
   ```bash
   export GTASKS_TURSO_TOKEN="your-jwt-token"
   ```

3. **Add & Sync**
   ```bash
   gtasks remote add "libsql://my-db.turso.io" "My Tasks"
   gtasks remote sync
   ```

For detailed setup instructions, see [REMOTE_SYNC_README.md](../REMOTE_SYNC_README.md).

---

**Status**: ✅ **COMPLETED** - Modular architecture with sidebar hide and data display fixes implemented successfully!
