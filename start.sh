#!/bin/bash

# PyBOG Workbench Startup Script
# This script sets up and starts the complete PyBOG system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker and try again."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

# Check environment file
check_env() {
    log_info "Checking environment configuration..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_warning ".env file not found. Copying from .env.example"
            cp .env.example .env
        else
            log_warning "Creating basic .env file"
            cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
N8N_ENCRYPTION_KEY=dev_encryption_key_change_me
EOF
        fi
    fi
    
    # Check if OpenAI API key is set
    if grep -q "your_openai_api_key_here" .env; then
        log_warning "OpenAI API key not set in .env file"
        log_warning "Please edit .env and add your OpenAI API key for full functionality"
    fi
    
    log_success "Environment configuration checked"
}

# Build and start services
start_services() {
    log_info "Building and starting PyBOG services..."
    
    # Stop any existing services
    docker-compose down &> /dev/null || true
    
    # Build and start services
    docker-compose up --build -d
    
    log_success "Services started"
}

# Wait for services to be ready
wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    # Wait for API
    log_info "Waiting for API to be ready..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            log_success "API is ready"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    if [ $elapsed -ge $timeout ]; then
        log_error "API failed to start within $timeout seconds"
        return 1
    fi
    
    # Wait for frontend
    log_info "Waiting for frontend to be ready..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            log_success "Frontend is ready"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    if [ $elapsed -ge $timeout ]; then
        log_warning "Frontend may not be ready yet, but continuing..."
    fi
    
    # Wait for N8N
    log_info "Waiting for N8N to be ready..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:5678 > /dev/null 2>&1; then
            log_success "N8N is ready"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    if [ $elapsed -ge $timeout ]; then
        log_warning "N8N may not be ready yet, but continuing..."
    fi
}

# Run basic tests
run_tests() {
    log_info "Running basic system tests..."
    
    if command -v python3 &> /dev/null; then
        if python3 test_integration.py; then
            log_success "System tests passed"
        else
            log_warning "Some system tests failed, but services are running"
        fi
    else
        log_warning "Python3 not found, skipping tests"
    fi
}

# Show service status
show_status() {
    log_info "Service Status:"
    docker-compose ps
    
    echo ""
    log_info "Access URLs:"
    echo "  🎨 PyBOG Workbench: http://localhost:3000"
    echo "  🔧 API Documentation: http://localhost:8000/docs"
    echo "  🔄 N8N Workflow Engine: http://localhost:5678"
    echo ""
    
    log_info "Next Steps:"
    echo "  1. Open PyBOG Workbench at http://localhost:3000"
    echo "  2. Import N8N workflow from workflow_data/pybog-enhanced-agent-v3.json"
    echo "  3. Upload HVAC documents or describe your system requirements"
    echo "  4. Generate BOG files for your control system"
    echo ""
    
    if grep -q "your_openai_api_key_here" .env; then
        log_warning "Don't forget to set your OpenAI API key in .env for AI features!"
    fi
}

# Main execution
main() {
    echo "🚀 PyBOG Workbench Startup"
    echo "=========================="
    echo ""
    
    check_docker
    check_env
    start_services
    wait_for_services
    run_tests
    show_status
    
    log_success "PyBOG Workbench is ready to use!"
}

# Run main function
main "$@"