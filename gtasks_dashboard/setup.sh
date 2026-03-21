#!/bin/bash

# GTasks Dashboard - Automated Setup Script
# This script will set up the GTasks Dashboard with all dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="gtasks-dashboard"
PYTHON_ENV_NAME="gtasks-dashboard"
MIN_NODE_VERSION="16"
MIN_PYTHON_VERSION="3.8"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check version
check_version() {
    local cmd=$1
    local version_arg=$2
    local min_version=$3
    
    if command_exists $cmd; then
        local current_version=$(eval $cmd $version_arg 2>/dev/null | head -n1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -n1)
        if [[ $(printf '%s\n' "$min_version" "$current_version" | sort -V | head -n1) == "$min_version" ]]; then
            print_success "$cmd version $current_version is compatible"
            return 0
        else
            print_error "$cmd version $current_version is too old. Minimum required: $min_version"
            return 1
        fi
    else
        print_error "$cmd is not installed"
        return 1
    fi
}

# Function to install Node.js via nvm (if needed)
install_nodejs() {
    if ! command_exists node; then
        print_status "Installing Node.js..."
        
        # Install nvm if not present
        if [[ ! -f "$HOME/.nvm/nvm.sh" ]]; then
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
        fi
        
        # Load nvm and install Node.js
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        nvm install node
        nvm use node
        nvm alias default node
        
        print_success "Node.js installed successfully"
    fi
}

# Function to install Python and virtual environment
install_python() {
    if ! command_exists python3; then
        print_status "Python 3 is required but not installed"
        print_warning "Please install Python 3.8+ manually and run this script again"
        exit 1
    fi
    
    print_status "Setting up Python virtual environment..."
    
    # Create virtual environment
    python3 -m venv $PYTHON_ENV_NAME
    
    # Activate virtual environment
    source $PYTHON_ENV_NAME/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping Python dependencies"
    fi
}

# Function to install Node.js dependencies
install_nodejs_deps() {
    print_status "Installing Node.js dependencies..."
    
    # Install root dependencies
    npm install
    
    # Install server dependencies
    cd server && npm install && cd ..
    
    print_success "Node.js dependencies installed"
}

# Function to set up environment files
setup_environment() {
    print_status "Setting up environment files..."
    
    # Create .env file if it doesn't exist
    if [[ ! -f ".env" ]]; then
        cat > .env << EOF
# GTasks Dashboard Environment Configuration
NODE_ENV=development
PORT=8080
CLIENT_URL=http://localhost:3000

# GTasks CLI Integration
GTASKS_CLI_PATH=../gtasks_cli

# Database Configuration
DATABASE_PATH=./data/dashboard.db

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# Sync Configuration
SYNC_INTERVAL=30000
AUTO_SYNC=true

# MCP Configuration
MCP_ENABLED=true
MCP_PORT=3001

# Notification Settings
NOTIFICATIONS_ENABLED=true
DESKTOP_NOTIFICATIONS=true

# Logging
LOG_LEVEL=info
LOG_FILE=./logs/app.log
EOF
        print_success "Created .env file with default configuration"
    else
        print_warning ".env file already exists, skipping creation"
    fi
    
    # Create necessary directories
    mkdir -p data logs
    
    print_success "Environment setup complete"
}

# Function to set up GTasks account
setup_gtasks_account() {
    print_status "Setting up GTasks account..."
    
    # Check if ~/.gtasks exists
    if [[ ! -d "$HOME/.gtasks" ]]; then
        print_warning "GTasks CLI not found. Please install gtasks-cli first."
        print_status "You can install it with: cd ../gtasks_cli && pip install -e ."
        return 1
    fi
    
    # Ask user for account name
    echo ""
    print_status "GTasks accounts are stored in ~/.gtasks/ directory"
    echo "Existing accounts:"
    ls -1 "$HOME/.gtasks/" 2>/dev/null | grep -v -E '\.(db|json|yaml|pickle)$' || echo "  (default)"
    echo ""
    
    read -p "Enter account name to use (or press Enter for 'Work'): " ACCOUNT_NAME
    ACCOUNT_NAME=${ACCOUNT_NAME:-Work}
    
    # Create account directory if it doesn't exist
    ACCOUNT_DIR="$HOME/.gtasks/$ACCOUNT_NAME"
    if [[ ! -d "$ACCOUNT_DIR" ]]; then
        mkdir -p "$ACCOUNT_DIR"
        print_success "Created account directory: $ACCOUNT_DIR"
    else
        print_status "Using existing account: $ACCOUNT_NAME"
    fi
    
    # Check for tasks.db in the account directory or parent
    if [[ -f "$ACCOUNT_DIR/tasks.db" ]]; then
        print_success "Found tasks.db in account directory"
    elif [[ -f "$HOME/.gtasks/tasks.db" ]]; then
        # Copy main tasks.db to account directory
        cp "$HOME/.gtasks/tasks.db" "$ACCOUNT_DIR/tasks.db"
        print_success "Copied tasks to $ACCOUNT_NAME account"
    else
        print_warning "No tasks.db found. Run 'gtasks advanced-sync' to sync tasks."
    fi
    
    # Save the default account for dashboard
    echo "$ACCOUNT_NAME" > "$HOME/.gtasks/dashboard_account.txt"
    print_success "Default account set to: $ACCOUNT_NAME"
    
    # Display next steps
    echo ""
    echo -e "${YELLOW}Next steps to sync with Google Tasks:${NC}"
    echo "  1. gtasks advanced-sync   # Sync with Google Tasks"
    echo "  2. cp ~/.gtasks/tasks.db ~/.gtasks/$ACCOUNT_NAME/tasks.db"
    echo "  3. python main_dashboard.py"
    echo ""
}

# Function to set up Remote Sync (Turso cloud database)
setup_remote_sync() {
    echo ""
    print_status "Setting up Remote Sync with Turso cloud database..."
    echo ""
    
    # Check if gtasks-cli is installed
    if ! command_exists gtasks; then
        print_warning "gtasks-cli is not installed."
        echo ""
        read -p "Do you want to install gtasks-cli first? (y/n): " INSTALL_GTASKS
        if [[ "$INSTALL_GTASKS" =~ ^[Yy]$ ]]; then
            if command_exists pipx; then
                print_status "Installing gtasks-cli with pipx..."
                pipx install gtasks-cli
            elif command_exists pip; then
                print_status "Installing gtasks-cli with pip..."
                pip install gtasks-cli
            else
                print_error "Neither pipx nor pip is available. Please install gtasks-cli manually."
                return 1
            fi
        else
            print_warning "Skipping remote sync setup."
            return 0
        fi
    fi
    
    # Install cmake if not available (required for libsql)
    if ! command_exists cmake; then
        echo ""
        print_warning "cmake is required for remote sync but is not installed."
        read -p "Do you want to install cmake? (y/n): " INSTALL_CMAKE
        if [[ "$INSTALL_CMAKE" =~ ^[Yy]$ ]]; then
            if command_exists brew; then
                print_status "Installing cmake with Homebrew..."
                brew install cmake
            else
                print_error "Homebrew not found. Please install cmake manually from https://cmake.org/download/"
                return 1
            fi
        else
            print_warning "Skipping remote sync setup. cmake is required."
            return 0
        fi
    fi
    
    # Install libsql into pipx venv
    echo ""
    print_status "Installing libsql package for remote database support..."
    
    if command_exists pipx; then
        # Check if gtasks-cli was installed with pipx
        PIPX_VENV="$HOME/.local/pipx/venvs/gtasks-cli"
        if [[ -d "$PIPX_VENV" ]]; then
            print_status "Installing libsql into pipx venv..."
            "$PIPX_VENV/bin/python" -m pip install libsql 2>/dev/null || {
                print_error "Failed to install libsql. Make sure cmake is in PATH and try again."
                return 1
            }
        else
            print_warning "gtasks-cli was not installed with pipx. Please install libsql manually:"
            echo "  pip install libsql"
        fi
    else
        print_status "Installing libsql with pip..."
        pip install libsql 2>/dev/null || {
            print_error "Failed to install libsql."
            return 1
        }
    fi
    
    print_success "libsql installed successfully"
    
    # Ask for Turso database URL
    echo ""
    echo -e "${YELLOW}Turso Database Setup:${NC}"
    echo "You need a Turso database to enable remote sync."
    echo "If you don't have one, create one at: https://turso.tech"
    echo ""
    read -p "Enter your Turso database URL (e.g., libsql://my-db.turso.io): " TURSO_URL
    TURSO_URL=${TURSO_URL:-}
    
    if [[ -z "$TURSO_URL" ]]; then
        print_warning "No database URL provided. Skipping remote sync."
        return 0
    fi
    
    read -p "Enter a name for this remote (or press Enter for 'Cloud'): " REMOTE_NAME
    REMOTE_NAME=${REMOTE_NAME:-Cloud}
    
    # Ask for Turso token
    echo ""
    print_status "Getting Turso authentication token..."
    if command_exists turso; then
        read -p "Enter database name for token creation: " TURSO_DB_NAME
        if [[ -n "$TURSO_DB_NAME" ]]; then
            TURSO_TOKEN=$(turso db tokens create "$TURSO_DB_NAME" 2>/dev/null)
            if [[ -n "$TURSO_TOKEN" ]]; then
                print_success "Token created successfully"
            fi
        fi
    fi
    
    if [[ -z "$TURSO_TOKEN" ]]; then
        echo ""
        read -p "Enter your Turso JWT token (or press Enter to set it later): " TURSO_TOKEN
    fi
    
    # Set the environment variable
    if [[ -n "$TURSO_TOKEN" ]]; then
        export GTASKS_TURSO_TOKEN="$TURSO_TOKEN"
        print_success "GTASKS_TURSO_TOKEN environment variable set"
        
        # Add to shell profile for persistence
        echo ""
        read -p "Do you want to add GTASKS_TURSO_TOKEN to your shell profile? (y/n): " ADD_TO_PROFILE
        if [[ "$ADD_TO_PROFILE" =~ ^[Yy]$ ]]; then
            SHELL_PROFILE="$HOME/.zshrc"
            [[ -f "$HOME/.bashrc" ]] && SHELL_PROFILE="$HOME/.bashrc"
            echo "" >> "$SHELL_PROFILE"
            echo "# GTasks CLI - Turso Remote Sync Token" >> "$SHELL_PROFILE"
            echo "export GTASKS_TURSO_TOKEN=\"$TURSO_TOKEN\"" >> "$SHELL_PROFILE"
            print_success "Added token to $SHELL_PROFILE"
        fi
    fi
    
    # Add the remote database
    echo ""
    print_status "Adding remote database to gtasks..."
    if gtasks remote add "$TURSO_URL" "$TURSO_TOKEN" --name "$REMOTE_NAME" 2>/dev/null; then
        print_success "Remote database '$REMOTE_NAME' added successfully!"
        
        echo ""
        echo -e "${GREEN}Remote Sync Setup Complete!${NC}"
        echo ""
        echo -e "${BLUE}Quick Commands:${NC}"
        echo "  gtasks remote list    # List configured remotes"
        echo "  gtasks remote sync    # Sync with all remotes"
        echo "  gtasks remote status  # Show sync status"
        echo ""
    else
        print_warning "Could not add remote. Make sure GTASKS_TURSO_TOKEN is set and try:"
        echo "  export GTASKS_TURSO_TOKEN=\"your-token\""
        echo "  gtasks remote add \"$TURSO_URL\" \"$REMOTE_NAME\""
    fi
    
    echo ""
}

# Function to build the project
build_project() {
    print_status "Building the project..."
    
    # Build client
    npm run build:client
    
    # Build server
    cd server && npm run build && cd ..
    
    print_success "Project built successfully"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    # Run client tests
    if npm run test --silent 2>/dev/null; then
        print_success "Client tests passed"
    else
        print_warning "No client tests configured or tests failed"
    fi
    
    # Run server tests
    cd server
    if npm run test --silent 2>/dev/null; then
        print_success "Server tests passed"
    else
        print_warning "No server tests configured or tests failed"
    fi
    cd ..
}

# Function to create startup scripts
create_startup_scripts() {
    print_status "Creating startup scripts..."
    
    # Development startup script
    cat > start-dev.sh << 'EOF'
#!/bin/bash
echo "Starting GTasks Dashboard in development mode..."
npm run dev
EOF
    
    # Production startup script
    cat > start-prod.sh << 'EOF'
#!/bin/bash
echo "Starting GTasks Dashboard in production mode..."
npm run build
npm run start
EOF
    
    # Make scripts executable
    chmod +x start-dev.sh start-prod.sh
    
    print_success "Startup scripts created"
}

# Function to display final instructions
show_final_instructions() {
    print_success "GTasks Dashboard setup complete!"
    echo ""
    echo -e "${GREEN}Quick Start:${NC}"
    echo "  Development: ./start-dev.sh"
    echo "  Production:  ./start-prod.sh"
    echo ""
    echo -e "${BLUE}Manual Commands:${NC}"
    echo "  npm run dev     - Start in development mode"
    echo "  npm run build   - Build the project"
    echo "  npm run start   - Start in production mode"
    echo ""
    echo -e "${BLUE}Server Commands:${NC}"
    echo "  cd server && npm run dev  - Start server in development"
    echo "  cd server && npm run start - Start server in production"
    echo ""
    echo -e "${BLUE}Access the Dashboard:${NC}"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8080"
    echo "  WebSocket: ws://localhost:8080"
    echo ""
    echo -e "${BLUE}Docker Deployment:${NC}"
    echo "  docker build -t gtasks-dashboard ."
    echo "  docker run -p 3000:3000 -p 8080:8080 gtasks-dashboard"
    echo ""
    echo -e "${YELLOW}Don't forget to:${NC}"
    echo "  1. Configure your .env file with proper settings"
    echo "  2. Set up your GTasks CLI credentials"
    echo "  3. Configure MCP integration if needed"
    echo ""
}

# Main setup process
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   GTasks Dashboard Setup                    ║"
    echo "║                Advanced Task Management                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    print_status "Starting setup process..."
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    # Check Node.js
    if ! check_version node "--version" "$MIN_NODE_VERSION"; then
        install_nodejs
    fi
    
    # Check Python
    if ! check_version python3 "--version" "$MIN_PYTHON_VERSION"; then
        print_error "Python $MIN_PYTHON_VERSION+ is required"
        exit 1
    fi
    
    # Install Python environment
    install_python
    
    # Install Node.js dependencies
    install_nodejs_deps
    
    # Set up environment
    setup_environment
    
    # Set up GTasks account (ask user for account name)
    setup_gtasks_account
    
    # Ask about Remote Sync setup
    echo ""
    read -p "Do you want to set up Remote Sync with Turso cloud database? (y/n): " SETUP_REMOTE
    if [[ "$SETUP_REMOTE" =~ ^[Yy]$ ]]; then
        setup_remote_sync
    fi
    
    # Create startup scripts
    create_startup_scripts
    
    # Build project
    build_project
    
    # Run tests
    run_tests
    
    # Show final instructions
    show_final_instructions
}

# Run main function
main "$@"