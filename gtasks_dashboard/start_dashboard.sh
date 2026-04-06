#!/bin/bash

# GTasks Dashboard - Background Start/Stop Script
# Usage: ./start_dashboard.sh [start|stop|status]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/dashboard.pid"
LOG_FILE="$SCRIPT_DIR/dashboard.log"

start_dashboard() {
    echo "Starting GTasks Dashboard..."
    
    # Kill existing process if running
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "Stopping existing process (PID: $OLD_PID)..."
            kill "$OLD_PID" 2>/dev/null
            sleep 1
        fi
        rm -f "$PID_FILE"
    fi
    
    # Also check for any existing dashboard processes
    EXISTING_PID=$(pgrep -f "main_dashboard.py" 2>/dev/null)
    if [ -n "$EXISTING_PID" ]; then
        echo "Stopping existing dashboard process (PID: $EXISTING_PID)..."
        kill "$EXISTING_PID" 2>/dev/null
        sleep 1
    fi
    
    # Start the dashboard with setsid to fully detach from terminal
    cd "$SCRIPT_DIR"
    setsid python main_dashboard.py > /dev/null 2>&1 &
    NEW_PID=$!
    
    # Save PID
    echo "$NEW_PID" > "$PID_FILE"
    
    # Wait a moment and verify it's running
    sleep 2
    if ps -p "$NEW_PID" > /dev/null 2>&1; then
        echo "✅ Dashboard started successfully!"
        echo "   PID: $NEW_PID"
        echo "   URL: http://localhost:8081"
        echo "   To stop: $0 stop"
    else
        echo "❌ Failed to start dashboard"
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop_dashboard() {
    echo "Stopping GTasks Dashboard..."
    
    # Try PID file first
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null
            echo "Stopped process (PID: $PID)"
        fi
        rm -f "$PID_FILE"
    fi
    
    # Also kill any remaining processes
    pgrep -f "main_dashboard.py" | while read pid; do
        kill "$pid" 2>/dev/null
        echo "Stopped process (PID: $pid)"
    done
    
    echo "✅ Dashboard stopped"
}

status_dashboard() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ Dashboard is running (PID: $PID)"
            echo "   URL: http://localhost:8081"
        else
            echo "⚠️ PID file exists but process is not running"
            rm -f "$PID_FILE"
        fi
    else
        # Check if process is running anyway
        PID=$(pgrep -f "main_dashboard.py" 2>/dev/null)
        if [ -n "$PID" ]; then
            echo "✅ Dashboard is running (PID: $PID)"
            echo "   URL: http://localhost:8081"
        else
            echo "❌ Dashboard is not running"
        fi
    fi
}

case "$1" in
    start)
        start_dashboard
        ;;
    stop)
        stop_dashboard
        ;;
    status)
        status_dashboard
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        echo ""
        echo "Examples:"
        echo "  $0 start    # Start dashboard in background"
        echo "  $0 stop     # Stop the dashboard"
        echo "  $0 status   # Check if dashboard is running"
        exit 1
        ;;
esac