#!/bin/bash
# Docker Startup Script for Linux/Mac/WSL
# AI Employee Gold Tier - Docker Compose Management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "=========================================="
    echo "   AI Employee - Gold Tier Docker Manager"
    echo "=========================================="
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Check if .env exists
check_env() {
    if [ ! -f .env ]; then
        print_warning ".env file not found!"
        print_info "Copying from .env.example..."
        cp .env.example .env
        echo ""
        print_warning "Please edit .env with your configuration before continuing."
        echo ""

        # Try to open with default editor
        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        else
            print_info "Please edit .env manually and run this script again."
        fi
        exit 1
    fi
}

# First time setup
first_time_setup() {
    print_info "Building and starting all services..."
    docker-compose up -d --build

    print_info "Waiting for services to initialize (30s)..."
    sleep 30

    print_info "Checking service health..."
    docker-compose ps

    echo ""
    echo "=========================================="
    print_success "Services started! Access URLs:"
    echo "  Odoo:       http://localhost:8069"
    echo "  pgAdmin:    http://localhost:5050"
    echo "=========================================="
    echo ""
    print_warning "IMPORTANT: Complete Odoo setup at http://localhost:8069"
    echo "  1. Create database with credentials from .env"
    echo "  2. Install Accounting module"
    echo "  3. Configure API access"
    echo ""
}

# Start services
start_services() {
    print_info "Starting services in background..."
    docker-compose up -d
    print_success "Services started!"
    docker-compose ps
}

# Stop services
stop_services() {
    print_info "Stopping services..."
    docker-compose down
    print_success "Services stopped."
}

# Restart services
restart_services() {
    print_info "Restarting services..."
    docker-compose restart
    print_success "Services restarted."
    docker-compose ps
}

# View logs
view_logs() {
    print_info "Viewing logs (Press Ctrl+C to stop)..."
    docker-compose logs -f
}

# Check status
check_status() {
    print_info "Service Status:"
    docker-compose ps
}

# Open URLs
open_odoo() {
    print_info "Opening Odoo in browser..."
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8069
    elif command -v open &> /dev/null; then
        open http://localhost:8069
    else
        print_info "Please open: http://localhost:8069"
    fi
}

open_pgadmin() {
    print_info "Opening pgAdmin in browser..."
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:5050
    elif command -v open &> /dev/null; then
        open http://localhost:5050
    else
        print_info "Please open: http://localhost:5050"
    fi
}

# Backup database
backup_database() {
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backup_${BACKUP_DATE}.sql"

    print_info "Creating backup..."
    docker-compose exec db pg_dump -U odoo ai_employee_db > "$BACKUP_FILE"

    if [ -f "$BACKUP_FILE" ]; then
        print_success "Backup saved to: $BACKUP_FILE"
        ls -lh "$BACKUP_FILE"
    else
        print_error "Backup failed!"
    fi
}

# Cleanup
cleanup() {
    echo ""
    print_warning "This will DELETE all data including:"
    echo "  - Odoo database"
    echo "  - All invoices and accounting data"
    echo "  - pgAdmin configuration"
    echo ""
    read -p "Are you sure? Type YES to confirm: " confirm

    if [ "$confirm" = "YES" ]; then
        print_info "Removing all data..."
        docker-compose down -v
        print_success "All data has been removed."
    else
        print_info "Cleanup cancelled."
    fi
}

# Show menu
show_menu() {
    print_header
    echo "  1. Start all services (first time setup)"
    echo "  2. Start services (background)"
    echo "  3. Stop all services"
    echo "  4. Restart services"
    echo "  5. View logs"
    echo "  6. Check status"
    echo "  7. Open Odoo (http://localhost:8069)"
    echo "  8. Open pgAdmin (http://localhost:5050)"
    echo "  9. Backup database"
    echo "  10. Clean up (WARNING: removes data!)"
    echo "  0. Exit"
    echo ""
}

# Main menu loop
main_menu() {
    check_prerequisites
    check_env

    while true; do
        show_menu
        read -p "Enter choice: " choice

        case $choice in
            1) first_time_setup ;;
            2) start_services ;;
            3) stop_services ;;
            4) restart_services ;;
            5) view_logs ;;
            6) check_status ;;
            7) open_odoo ;;
            8) open_pgadmin ;;
            9) backup_database ;;
            10) cleanup ;;
            0) print_info "Goodbye!"; exit 0 ;;
            *) print_error "Invalid choice. Please try again." ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
        clear
    done
}

# Handle command line arguments
case "${1:-}" in
    start)
        check_env
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        view_logs
        ;;
    status)
        check_status
        ;;
    backup)
        check_env
        backup_database
        ;;
    setup)
        check_env
        first_time_setup
        ;;
    *)
        main_menu
        ;;
esac
