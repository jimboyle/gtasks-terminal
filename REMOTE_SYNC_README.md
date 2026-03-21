# Remote Sync Feature - Complete Guide

> **Sync your tasks across devices with Turso cloud database**

## 🎯 Features

- **Bidirectional Sync**: Local SQLite ↔ Remote Turso DB (sync in both directions)
- **Multi-Device Access**: Access your tasks from any device via the cloud database
- **Google Tasks Integration**: Sync with Google Tasks API as the source of truth
- **Smart Conflict Resolution**: Automatic resolution using "newest wins" strategy
- **Background Sync**: Non-blocking sync operations with progress tracking
- **Dashboard Integration**: Visual sync status in the web dashboard
- **Security First**: Tokens stored in environment variables, never in config files

---

## 🚀 Quick Start (5 minutes)

### Prerequisites

- Python 3.7 or higher
- A Turso account (free tier available at [turso.tech](https://turso.tech))
- Turso CLI installed

### Step 0: Install gtasks-cli

```bash
# If using pipx (recommended on macOS)
pipx install gtasks-cli

# If using pip (may need --break-system-packages on some systems)
pip install gtasks-cli

# For development from local repo
cd ~/path/to/gtasks-terminal/gtasks_cli
pipx install -e . --force
```

### Step 0.5: Enable Remote Sync (Optional)

For remote sync features, you need to install the `libsql` package which requires cmake:

```bash
# Install cmake (required for libsql)
brew install cmake

# Install libsql into your gtasks-cli environment
~/.local/pipx/venvs/gtasks-cli/bin/python -m pip install libsql
```

> **Note:** If you installed gtasks-cli with pipx, the libsql package must be injected into the pipx venv using the above command.

### Step 1: Install Turso CLI

```bash
# macOS
brew install tursodatabase/tap/turso

# Or download from https://github.com/tursodatabase/libsql/releases
```

### Step 2: Create a Turso Database

```bash
# Login to Turso (create account if needed)
turso auth login

# Create a new database (use aws-ap-south-1 for India region)
turso db create my-gtasks --location aws-ap-south-1

# Get the database URL
turso db show my-gtasks
```

### Step 3: Get Authentication Token

```bash
# Create an authentication token for your database
turso db tokens create my-gtasks
```

### Step 4: Set Environment Variable

```bash
# Add this to your shell profile (~/.zshrc or ~/.bashrc)
export GTASKS_TURSO_TOKEN="eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9..."

# Reload your shell
source ~/.zshrc
```

### Step 5: Add Remote Database & Sync

```bash
# Get your database URL and token
turso db show my-gtasks
turso db tokens create my-gtasks

# Add the remote database to gtasks (URL first, TOKEN second, --name for friendly name)
gtasks remote add "libsql://my-gtasks-xxxxx.ap-south-1.turso.io" "your-jwt-token" --name "My Tasks"

# Perform initial sync
gtasks remote sync

# Verify
gtasks remote list
```

> **Important:** The command syntax is `gtasks remote add <URL> <TOKEN> --name "<friendly name>"`
> - First argument: Database URL
> - Second argument: JWT authentication token
> - `--name`: Optional friendly name (defaults to URL hostname)

---

## 📋 CLI Commands

### Add a Remote Database

```bash
gtasks remote add <url> <token> [--name <friendly-name>] [--account <account-name>]

# Example (URL, TOKEN, --name)
gtasks remote add "libsql://my-db.turso.io" "eyJhbGci..." --name "Work Tasks"
```

### List Remote Databases

```bash
gtasks remote list [--account <account-name>]

# Output:
# 1. My Tasks
#    URL: libsql://my-db.turso.io
#    Status: ✓ Active
#    Last synced: 2024-01-15 10:30:00
```

### Sync with Remote

```bash
# Full sync (push & pull)
gtasks remote sync [--account <account-name>]

# Push only (local → remote)
gtasks remote push [--account <account-name>]

# Pull only (remote → local)
gtasks remote pull [--account <account-name>]
```

### Remove a Remote Database

```bash
gtasks remote remove <url> [--account <account-name>]
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GTASKS_TURSO_TOKEN` | JWT token for Turso authentication | Yes |
| `GTASKS_CONFIG_DIR` | Custom config directory path | No |
| `GTASKS_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING) | No |

### Config File Location

Remote database configurations are stored at:
- Default: `~/.gtasks/remote_dbs.yaml`
- Custom: `$GTASKS_CONFIG_DIR/remote_dbs.yaml`

### Multiple Accounts

```bash
# Configure remote for specific account
gtasks remote add "libsql://work-db.turso.io" "Work" --account work
gtasks remote add "libsql://personal-db.turso.io" "Personal" --account personal

# Sync specific account
gtasks remote sync --account work
```

---

## 🌐 Dashboard Integration

### Enable Remote Sync in Dashboard

The dashboard automatically detects configured remote databases and shows:

1. **Sync Status Indicator** in the header
2. **Manual Sync Button** to trigger sync
3. **Last Sync Timestamp** showing when data was last synced

### Dashboard API Endpoints

```
GET  /api/remote/status          - Get connection status
GET  /api/remote/databases       - List configured databases
POST /api/remote/sync            - Start sync operation
GET  /api/remote/sync/progress   - Get sync progress
POST /api/remote/push            - Push to remote
POST /api/remote/pull            - Pull from remote
```

### Dashboard Sync Flow

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Local SQLite   │ ←──→ │  Dashboard API   │ ←──→ │  Remote Turso   │
│   (Your Device)  │      │  (Background)   │      │  (Cloud DB)     │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        ↑                          ↓
        │                          │
        └─────── Sync Button ───────┘
```

---

## 🛡️ Security Best Practices

### ✅ DO

1. **Use environment variables for tokens**
   ```bash
   export GTASKS_TURSO_TOKEN="your-token"
   ```

2. **Add to shell profile for persistence**
   ```bash
   echo 'export GTASKS_TURSO_TOKEN="your-token"' >> ~/.zshrc
   ```

3. **Rotate tokens regularly**
   ```bash
   turso db tokens rotate my-gtasks
   # Then update your environment variable
   ```

4. **Use different tokens for different environments**
   ```bash
   export GTASKS_TURSO_TOKEN_DEV="dev-token"
   export GTASKS_TURSO_TOKEN_PROD="prod-token"
   ```

### ❌ DON'T

1. **Never commit tokens to Git**
   ```bash
   # BAD
   git commit -am "Added my token"
   
   # The .gitignore already excludes these files:
   # - .env, .env.local
   # - *.token, *.auth
   # - *turso*, remote_dbs.yaml
   ```

2. **Never share tokens**
   - Don't send via Slack, email, or chat
   - Don't hardcode in source code
   - Don't put in public repositories

3. **Never use production tokens on public servers**
   - Use separate tokens for development and production

---

## 🔄 Sync Strategy

### Conflict Resolution

When the same task exists in both local and remote databases with different content:

1. **Compare timestamps**: Task with newest `modified_at` wins
2. **Source priority** (when timestamps equal):
   - Google Tasks (highest priority)
   - Local changes
   - Remote database

### Sync Process

```
1. Load tasks from Local SQLite
2. Load tasks from Remote Turso DB
3. Load tasks from Google Tasks (if enabled)
4. Merge by task_id
5. Compare timestamps
6. Resolve conflicts (newest wins)
7. Save merged tasks to Local SQLite
8. Push merged tasks to Remote Turso
9. Update Google Tasks (if enabled)
```

---

## 🐛 Troubleshooting

### "No auth token provided"

```bash
# Check if token is set
echo $GTASKS_TURSO_TOKEN

# If empty, set it
export GTASKS_TURSO_TOKEN="your-token"
```

### "Connection refused" or timeout

```bash
# Test connection to Turso
curl -I "https://your-db.turso.io"

# Check your database URL
turso db show my-gtasks
```

### "Token expired" or "Invalid token"

```bash
# Rotate your token
turso db tokens rotate my-gtasks

# Update environment variable with new token
export GTASKS_TURSO_TOKEN="new-token"
```

### Sync hangs or takes too long

```bash
# Run with verbose output
export GTASKS_LOG_LEVEL=DEBUG
gtasks remote sync -v

# Check number of tasks (large task lists take longer)
gtasks list | wc -l
```

### Dashboard shows "Offline"

```bash
# Verify remote is configured
gtasks remote list

# Check if GTASKS_TURSO_TOKEN is set
echo $GTASKS_TURSO_TOKEN

# Try manual sync
gtasks remote sync
```

---

## 📊 Features in Detail

### Background Sync

- Non-blocking sync operations
- Progress tracking via API
- Automatic retry on failure

### Multi-Database Support

- Connect to multiple remote Turso databases
- Separate sync for different accounts
- Independent sync settings per database

### Offline Support

- Local SQLite always has full data
- Works without internet connection
- Syncs when connection restored

### Dashboard Features

| Feature | Description |
|---------|-------------|
| Status Indicator | Shows connected/disconnected status |
| Sync Button | Manual trigger for sync |
| Last Sync Time | Shows when data was last synced |
| DB Count | Number of configured remote databases |

---

## 🔗 Related Documentation

- [REMOTE_SYNC_FEATURE_PLAN.md](./REMOTE_SYNC_FEATURE_PLAN.md) - Technical implementation details
- [REMOTE_SYNC_SECURITY_GUIDE.md](./REMOTE_SYNC_SECURITY_GUIDE.md) - Security best practices
- [gtasks_dashboard/README.md](./gtasks_dashboard/README.md) - Dashboard documentation

---

## 💡 Tips

1. **Set up a cron job for automatic sync**
   ```bash
   # Sync every 5 minutes
   */5 * * * * export GTASKS_TURSO_TOKEN="..." && gtasks remote sync
   ```

2. **Use aliases for quick commands**
   ```bash
   # Add to ~/.zshrc
   alias gs='gtasks'
   alias gss='gtasks remote sync'
   alias gsl='gtasks remote list'
   ```

3. **Check sync status before important operations**
   ```bash
   gtasks remote list  # Verify last sync time
   gtasks remote sync  # Ensure data is current
   ```

4. **Export your data regularly**
   ```bash
   gtasks export --format json --output backup.json
   ```

---

## 🆘 Need Help?

- **CLI Help**: `gtasks remote --help`
- **Dashboard Help**: Access `/help` endpoint when running
- **Report Issues**: https://github.com/sirusdas/gtasks-terminal/issues

---

**Remember**: Your tokens are your keys. Keep them safe, never share them, and rotate them periodically!
