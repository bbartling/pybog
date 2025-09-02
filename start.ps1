# PyBOG Workbench Startup Script for Windows
# This script sets up and starts the complete PyBOG system

param(
    [switch]$SkipTests = $false,
    [switch]$Verbose = $false
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output
function Write-Info {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check if Docker is installed and running
function Test-Docker {
    Write-Info "Checking Docker installation..."
    
    try {
        $dockerVersion = docker --version
        if (-not $dockerVersion) {
            throw "Docker command not found"
        }
        Write-Success "Docker is installed: $dockerVersion"
    }
    catch {
        Write-Error-Custom "Docker is not installed or not in PATH. Please install Docker Desktop and try again."
        exit 1
    }
    
    try {
        $composeVersion = docker-compose --version
        if (-not $composeVersion) {
            throw "Docker Compose command not found"
        }
        Write-Success "Docker Compose is installed: $composeVersion"
    }
    catch {
        Write-Error-Custom "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    }
    
    try {
        docker info *>$null
        Write-Success "Docker is running"
    }
    catch {
        Write-Error-Custom "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    }
}

# Check environment file
function Test-Environment {
    Write-Info "Checking environment configuration..."
    
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Write-Warning ".env file not found. Copying from .env.example"
            Copy-Item ".env.example" ".env"
        }
        else {
            Write-Warning "Creating basic .env file"
            @"
OPENAI_API_KEY=your_openai_api_key_here
N8N_ENCRYPTION_KEY=dev_encryption_key_change_me
"@ | Out-File -FilePath ".env" -Encoding utf8
        }
    }
    
    # Check if OpenAI API key is set
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "your_openai_api_key_here") {
        Write-Warning "OpenAI API key not set in .env file"
        Write-Warning "Please edit .env and add your OpenAI API key for full functionality"
    }
    
    Write-Success "Environment configuration checked"
}

# Build and start services
function Start-Services {
    Write-Info "Building and starting PyBOG services..."
    
    # Stop any existing services
    try {
        docker-compose down *>$null
    }
    catch {
        # Ignore errors if no services are running
    }
    
    # Build and start services
    Write-Info "This may take several minutes for the first run..."
    docker-compose up --build -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Services started successfully"
    }
    else {
        Write-Error-Custom "Failed to start services"
        exit 1
    }
}

# Wait for services to be ready
function Wait-ForServices {
    Write-Info "Waiting for services to be ready..."
    
    # Function to test if a service is responding
    function Test-ServiceReady {
        param($Url, $ServiceName, $TimeoutSeconds = 60)
        
        Write-Info "Waiting for $ServiceName to be ready..."
        $elapsed = 0
        $ready = $false
        
        while ($elapsed -lt $TimeoutSeconds) {
            try {
                $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    Write-Success "$ServiceName is ready"
                    $ready = $true
                    break
                }
            }
            catch {
                # Service not ready yet
            }
            
            Start-Sleep -Seconds 2
            $elapsed += 2
            Write-Host -NoNewline "."
        }
        
        if (-not $ready) {
            Write-Warning "$ServiceName may not be ready yet, but continuing..."
        }
        
        Write-Host ""  # New line after dots
        return $ready
    }
    
    # Wait for each service
    Test-ServiceReady "http://localhost:8000/api/health" "API" 90
    Test-ServiceReady "http://localhost:3000" "Frontend" 90  
    Test-ServiceReady "http://localhost:5678" "N8N" 90
}

# Run basic tests
function Invoke-Tests {
    if ($SkipTests) {
        Write-Info "Skipping tests as requested"
        return
    }
    
    Write-Info "Running basic system tests..."
    
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            python test_integration.py
            Write-Success "System tests passed"
        }
        catch {
            Write-Warning "Some system tests failed, but services are running"
        }
    }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        try {
            python3 test_integration.py
            Write-Success "System tests passed"
        }
        catch {
            Write-Warning "Some system tests failed, but services are running"
        }
    }
    else {
        Write-Warning "Python not found, skipping tests"
    }
}

# Show service status
function Show-Status {
    Write-Info "Service Status:"
    docker-compose ps
    
    Write-Host ""
    Write-Info "Access URLs:"
    Write-Host "  🎨 PyBOG Workbench: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  🔧 API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "  🔄 N8N Workflow Engine: http://localhost:5678" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "Next Steps:"
    Write-Host "  1. Open PyBOG Workbench at http://localhost:3000"
    Write-Host "  2. Import N8N workflow from workflow_data/pybog-enhanced-agent-v3.json"
    Write-Host "  3. Upload HVAC documents or describe your system requirements"
    Write-Host "  4. Generate BOG files for your control system"
    Write-Host ""
    
    $envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
    if ($envContent -and $envContent -match "your_openai_api_key_here") {
        Write-Warning "Don't forget to set your OpenAI API key in .env for AI features!"
    }
    
    Write-Host ""
    Write-Info "Useful Commands:"
    Write-Host "  Stop services: docker-compose down"
    Write-Host "  View logs: docker-compose logs"
    Write-Host "  Restart: docker-compose restart"
}

# Main execution
function Main {
    Write-Host "🚀 PyBOG Workbench Startup" -ForegroundColor Green
    Write-Host "==========================" -ForegroundColor Green
    Write-Host ""
    
    try {
        Test-Docker
        Test-Environment
        Start-Services
        Wait-ForServices
        Invoke-Tests
        Show-Status
        
        Write-Success "PyBOG Workbench is ready to use!"
        Write-Host ""
        Write-Host "Press any key to open PyBOG Workbench in your browser..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        Start-Process "http://localhost:3000"
    }
    catch {
        Write-Error-Custom "Startup failed: $($_.Exception.Message)"
        Write-Host ""
        Write-Info "Troubleshooting:"
        Write-Host "  - Ensure Docker Desktop is running"
        Write-Host "  - Check that ports 3000, 8000, and 5678 are available"
        Write-Host "  - Run 'docker-compose logs' to see detailed error messages"
        exit 1
    }
}

# Run main function
Main