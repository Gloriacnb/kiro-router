#!/bin/bash

# Kiro Gateway macOS Service Installer
# This script installs Kiro Gateway as a macOS LaunchAgent for auto-startup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="com.github.kirowhat.gateway"
PLIST_TEMPLATE="$(dirname "$0")/com.github.kirowhat.gateway.plist.template"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$LAUNCH_AGENTS_DIR/$SERVICE_NAME.plist"
LOG_DIR="$HOME/Library/Logs/$SERVICE_NAME"

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

# Check if kiro-gateway command exists
check_kiro_gateway() {
    print_info "Checking for kiro-gateway installation..."

    if command -v kiro-gateway &> /dev/null; then
        KIRO_GATEWAY_PATH=$(command -v kiro-gateway)
        print_success "Found kiro-gateway at: $KIRO_GATEWAY_PATH"
        return 0
    else
        print_error "kiro-gateway command not found!"
        echo ""
        echo "Please install kiro-gateway globally first:"
        echo "  cd /path/to/kiro-router"
        echo "  uv tool install . --global"
        echo ""
        exit 1
    fi
}

# Get .env file path
get_env_file() {
    print_info "Configuration file setup"
    echo ""

    # Default to current directory's .env
    DEFAULT_ENV_FILE="$(pwd)/.env"

    # Check if .env exists in current directory
    if [ -f "$DEFAULT_ENV_FILE" ]; then
        print_success "Found .env file in current directory"
        ENV_FILE="$DEFAULT_ENV_FILE"
    else
        print_warning "No .env file found in current directory"
        echo -n "Enter path to .env file (or press Enter to skip): "
        read -r USER_ENV_FILE

        if [ -n "$USER_ENV_FILE" ]; then
            if [ -f "$USER_ENV_FILE" ]; then
                ENV_FILE="$USER_ENV_FILE"
                print_success "Using .env file: $ENV_FILE"
            else
                print_error "File not found: $USER_ENV_FILE"
                exit 1
            fi
        else
            ENV_FILE=""
            print_warning "No .env file specified. Make sure to configure credentials!"
        fi
    fi
    echo ""
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."

    # Create LaunchAgents directory if it doesn't exist
    if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
        mkdir -p "$LAUNCH_AGENTS_DIR"
        print_success "Created LaunchAgents directory"
    fi

    # Create log directory
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        print_success "Created log directory: $LOG_DIR"
    fi
    echo ""
}

# Generate plist file from template
generate_plist() {
    print_info "Generating LaunchAgent plist file..."

    if [ ! -f "$PLIST_TEMPLATE" ]; then
        print_error "Template file not found: $PLIST_TEMPLATE"
        exit 1
    fi

    # Read template and replace placeholders
    PLIST_CONTENT=$(cat "$PLIST_TEMPLATE")

    # Replace placeholders
    PLIST_CONTENT="${PLIST_CONTENT//\{\{KIRO_GATEWAY_PATH\}\}/$KIRO_GATEWAY_PATH}"
    PLIST_CONTENT="${PLIST_CONTENT//\{\{ENV_FILE_PATH\}\}/$ENV_FILE}"
    PLIST_CONTENT="${PLIST_CONTENT//\{\{HOME\}\}/$HOME}"
    PLIST_CONTENT="${PLIST_CONTENT//\{\{PATH\}\}/$PATH}"

    # Write plist file
    echo "$PLIST_CONTENT" > "$PLIST_FILE"

    print_success "Generated plist file: $PLIST_FILE"
    echo ""
}

# Load the service
load_service() {
    print_info "Loading LaunchAgent service..."

    # Unload if already exists
    if launchctl list | grep -q "$SERVICE_NAME"; then
        print_warning "Service already loaded. Unloading first..."
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
    fi

    # Load the service
    launchctl load "$PLIST_FILE"

    # Wait a moment for the service to start
    sleep 2

    print_success "Service loaded successfully!"
    echo ""
}

# Check service status
check_status() {
    print_info "Checking service status..."

    if launchctl list | grep -q "$SERVICE_NAME"; then
        print_success "Service is running!"

        # Get PID
        PID=$(launchctl list | grep "$SERVICE_NAME" | awk '{print $1}')
        echo -e "${BLUE}  PID:${NC} $PID"

        # Check if service is responding
        sleep 1
        echo ""
        echo "You can check the gateway health by visiting:"
        echo "  http://localhost:8000/health"
        echo ""
    else
        print_error "Service failed to start!"
        echo ""
        echo "Check logs for errors:"
        echo "  cat \"$LOG_DIR/stderr.log\""
        echo ""
    fi
}

# Print next steps
print_next_steps() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Service Management Commands:"
    echo "  Start:   ./kiro-gateway-service.sh start"
    echo "  Stop:    ./kiro-gateway-service.sh stop"
    echo "  Restart: ./kiro-gateway-service.sh restart"
    echo "  Status:  ./kiro-gateway-service.sh status"
    echo "  Logs:    ./kiro-gateway-service.sh logs"
    echo ""
    echo "Log Files:"
    echo "  stdout:  $LOG_DIR/stdout.log"
    echo "  stderr:  $LOG_DIR/stderr.log"
    echo ""
    echo "To uninstall:"
    echo "  ./kiro-gateway-service.sh uninstall"
    echo ""
}

# Main installation flow
main() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Kiro Gateway macOS Service Installer  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""

    # Check prerequisites
    check_kiro_gateway
    get_env_file
    create_directories
    generate_plist
    load_service
    check_status
    print_next_steps
}

# Run main function
main
