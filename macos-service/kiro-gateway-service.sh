#!/bin/bash

# Kiro Gateway Service Control Script
# Control script for managing Kiro Gateway LaunchAgent service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="com.github.kirowhat.gateway"
PLIST_FILE="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"
LOG_DIR="$HOME/Library/Logs/$SERVICE_NAME"
STDOUT_LOG="$LOG_DIR/stdout.log"
STDERR_LOG="$LOG_DIR/stderr.log"

# Print colored message
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Check if service is loaded
is_loaded() {
    launchctl list | grep -q "$SERVICE_NAME"
}

# Check if service is running
is_running() {
    if is_loaded; then
        local pid=$(launchctl list | grep "$SERVICE_NAME" | awk '{print $1}')
        if [ -n "$pid" ] && [ "$pid" != "-" ]; then
            return 0
        fi
    fi
    return 1
}

# Start the service
start_service() {
    print_header "Starting Kiro Gateway Service"

    if is_running; then
        print_warning "Service is already running!"
        show_status
        return 0
    fi

    print_info "Loading service..."
    launchctl load "$PLIST_FILE" 2>/dev/null || print_warning "Service might already be loaded"

    # Wait for service to start
    sleep 2

    if is_running; then
        print_success "Service started successfully!"
        show_status
    else
        print_error "Failed to start service!"
        echo ""
        echo "Check logs for errors:"
        echo "  $0 logs"
    fi
}

# Stop the service
stop_service() {
    print_header "Stopping Kiro Gateway Service"

    if ! is_loaded; then
        print_warning "Service is not loaded!"
        return 0
    fi

    print_info "Stopping service..."
    launchctl unload "$PLIST_FILE"

    # Wait for service to stop
    sleep 1

    if ! is_loaded; then
        print_success "Service stopped successfully!"
    else
        print_error "Failed to stop service!"
    fi
}

# Restart the service
restart_service() {
    print_header "Restarting Kiro Gateway Service"

    if is_loaded; then
        print_info "Stopping service..."
        launchctl unload "$PLIST_FILE"
        sleep 1
    fi

    print_info "Starting service..."
    launchctl load "$PLIST_FILE"
    sleep 2

    if is_running; then
        print_success "Service restarted successfully!"
        show_status
    else
        print_error "Failed to restart service!"
    fi
}

# Show service status
show_status() {
    echo ""
    print_info "Service Status"

    if is_running; then
        echo -e "  State: ${GREEN}Running${NC}"

        # Get PID
        local pid=$(launchctl list | grep "$SERVICE_NAME" | awk '{print $1}')
        echo -e "  PID:   $pid"

        # Get memory usage
        if [ -n "$pid" ]; then
            local mem_usage=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
            echo -e "  Memory: $mem_usage"
        fi

        # Check if health endpoint is responding
        if command -v curl &> /dev/null; then
            local health_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
            if [ "$health_status" = "200" ]; then
                echo -e "  Health: ${GREEN}OK${NC} (http://localhost:8000/health)"
            else
                echo -e "  Health: ${YELLOW}Checking...${NC} (may be starting up)"
            fi
        fi
    elif is_loaded; then
        echo -e "  State: ${YELLOW}Loaded but not running${NC}"
    else
        echo -e "  State: ${RED}Not loaded${NC}"
    fi

    echo ""
}

# Show logs
show_logs() {
    local log_type="${1:-combined}"

    case "$log_type" in
        combined|all)
            print_info "Showing combined logs (Ctrl+C to exit)..."
            echo ""
            tail -f "$STDOUT_LOG" "$STDERR_LOG" 2>/dev/null || print_error "No logs found"
            ;;
        stdout)
            print_info "Showing stdout logs (Ctrl+C to exit)..."
            echo ""
            tail -f "$STDOUT_LOG" 2>/dev/null || print_error "No stdout log found"
            ;;
        stderr)
            print_info "Showing stderr logs (Ctrl+C to exit)..."
            echo ""
            tail -f "$STDERR_LOG" 2>/dev/null || print_error "No stderr log found"
            ;;
        *)
            print_error "Unknown log type: $log_type"
            echo ""
            echo "Usage: $0 logs [combined|stdout|stderr]"
            exit 1
            ;;
    esac
}

# Install the service
install_service() {
    local script_dir="$(dirname "$0")"
    local install_script="$script_dir/install-macos-service.sh"

    if [ -f "$install_script" ]; then
        exec "$install_script"
    else
        print_error "Installation script not found: $install_script"
        exit 1
    fi
}

# Uninstall the service
uninstall_service() {
    print_header "Uninstalling Kiro Gateway Service"

    if ! is_loaded; then
        print_warning "Service is not loaded!"
    else
        print_info "Stopping and unloading service..."
        launchctl unload "$PLIST_FILE"
        print_success "Service unloaded!"
    fi

    # Remove plist file
    if [ -f "$PLIST_FILE" ]; then
        print_info "Removing plist file..."
        rm "$PLIST_FILE"
        print_success "Removed: $PLIST_FILE"
    fi

    # Ask about logs
    echo ""
    echo -n "Remove log files? (y/N): "
    read -r remove_logs

    if [ "$remove_logs" = "y" ] || [ "$remove_logs" = "Y" ]; then
        if [ -d "$LOG_DIR" ]; then
            print_info "Removing log directory..."
            rm -rf "$LOG_DIR"
            print_success "Removed: $LOG_DIR"
        fi
    else
        print_info "Logs preserved at: $LOG_DIR"
    fi

    echo ""
    print_success "Uninstallation complete!"
}

# Show usage
show_usage() {
    print_header "Kiro Gateway Service Control"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start     Start the service"
    echo "  stop      Stop the service"
    echo "  restart   Restart the service"
    echo "  status    Show service status"
    echo "  logs      Show service logs (default: combined)"
    echo "  install   Install the service"
    echo "  uninstall Uninstall the service"
    echo ""
    echo "Log Types:"
    echo "  combined  Show both stdout and stderr (default)"
    echo "  stdout    Show only stdout"
    echo "  stderr    Show only stderr"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 logs"
    echo "  $0 logs stderr"
    echo ""
}

# Main
case "${1:-}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-combined}"
        ;;
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    help|--help|-h)
        show_usage
        ;;
    "")
        show_status
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac
