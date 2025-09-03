#!/bin/bash
# ONEX Smart Responder Chain Installation Script
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_TYPE="${1:-local}"
PYTHON_VERSION="3.12"
POETRY_VERSION="1.8.0"

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

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Install system dependencies
install_system_deps() {
    local os=$(detect_os)

    log_info "Installing system dependencies for $os..."

    case $os in
        "linux")
            if command_exists apt-get; then
                sudo apt-get update
                sudo apt-get install -y \
                    python3 \
                    python3-pip \
                    python3-venv \
                    postgresql-client \
                    redis-tools \
                    curl \
                    git \
                    build-essential
            elif command_exists yum; then
                sudo yum update -y
                sudo yum install -y \
                    python3 \
                    python3-pip \
                    postgresql \
                    redis \
                    curl \
                    git \
                    gcc \
                    gcc-c++
            else
                log_error "Unsupported Linux distribution"
                exit 1
            fi
            ;;
        "macos")
            if ! command_exists brew; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi

            brew update
            brew install python@3.12 postgresql redis git
            ;;
        *)
            log_error "Unsupported operating system: $os"
            exit 1
            ;;
    esac
}

# Install Poetry
install_poetry() {
    if command_exists poetry; then
        log_info "Poetry already installed: $(poetry --version)"
        return
    fi

    log_info "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

    # Add Poetry to PATH
    export PATH="$HOME/.local/bin:$PATH"

    if command_exists poetry; then
        log_success "Poetry installed successfully: $(poetry --version)"
    else
        log_error "Poetry installation failed"
        exit 1
    fi
}

# Install Docker (if needed)
install_docker() {
    if command_exists docker; then
        log_info "Docker already installed: $(docker --version)"
        return
    fi

    local os=$(detect_os)
    log_info "Installing Docker..."

    case $os in
        "linux")
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
            ;;
        "macos")
            log_warning "Please install Docker Desktop for Mac manually from https://docker.com/products/docker-desktop"
            ;;
        *)
            log_error "Docker installation not supported for $os"
            exit 1
            ;;
    esac
}

# Install kubectl (if needed)
install_kubectl() {
    if command_exists kubectl; then
        log_info "kubectl already installed: $(kubectl version --client --short 2>/dev/null || echo 'installed')"
        return
    fi

    local os=$(detect_os)
    log_info "Installing kubectl..."

    case $os in
        "linux")
            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
            sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
            rm kubectl
            ;;
        "macos")
            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
            chmod +x kubectl
            sudo mv kubectl /usr/local/bin/
            ;;
        *)
            log_error "kubectl installation not supported for $os"
            exit 1
            ;;
    esac
}

# Install ONEX locally
install_local() {
    log_info "Installing ONEX Smart Responder Chain locally..."

    # Check Python version
    if ! command_exists python3; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "$(printf '%s\n' "3.12" "$python_version" | sort -V | head -n1)" != "3.12" ]]; then
        log_warning "Python 3.12+ is recommended (current: $python_version)"
    fi

    # Install Poetry if not present
    install_poetry

    # Install dependencies
    log_info "Installing Python dependencies..."
    poetry install --extras "full"

    # Initialize configuration
    log_info "Initializing configuration..."
    poetry run omni-agent config init

    log_success "ONEX installed locally!"
    log_info "Run 'poetry run omni-agent --help' to get started"
}

# Install ONEX with Docker
install_docker_compose() {
    log_info "Installing ONEX Smart Responder Chain with Docker Compose..."

    # Install Docker if needed
    install_docker

    # Install Docker Compose if needed
    if ! command_exists docker-compose; then
        log_info "Installing Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi

    # Create environment file
    if [[ ! -f .env ]]; then
        log_info "Creating environment file..."
        cat > .env << EOF
# ONEX Production Environment
POSTGRES_PASSWORD=onex_secure_password_change_me
GRAFANA_PASSWORD=admin_change_me

# Optional: External API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Optional: Monitoring
SENTRY_DSN=
EOF
        log_warning "Please update .env file with secure passwords and API keys"
    fi

    # Build and start services
    log_info "Building and starting ONEX services..."
    docker-compose build
    docker-compose up -d

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30

    # Check service health
    if docker-compose exec onex-api omni-agent status >/dev/null 2>&1; then
        log_success "ONEX services are running!"
        log_info "API: http://localhost:8000"
        log_info "Grafana: http://localhost:3000 (admin/admin)"
        log_info "Prometheus: http://localhost:9090"
    else
        log_error "Services failed to start properly"
        docker-compose logs
        exit 1
    fi
}

# Install ONEX on Kubernetes
install_kubernetes() {
    log_info "Installing ONEX Smart Responder Chain on Kubernetes..."

    # Install kubectl if needed
    install_kubectl

    # Check kubectl connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "kubectl is not connected to a Kubernetes cluster"
        log_info "Please configure kubectl to connect to your cluster first"
        exit 1
    fi

    # Apply Kubernetes manifests
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f deployment/kubernetes/namespace.yaml
    kubectl apply -f deployment/kubernetes/configmap.yaml
    kubectl apply -f deployment/kubernetes/secret.yaml
    kubectl apply -f deployment/kubernetes/pvc.yaml
    kubectl apply -f deployment/kubernetes/postgres.yaml
    kubectl apply -f deployment/kubernetes/deployment.yaml
    kubectl apply -f deployment/kubernetes/service.yaml
    kubectl apply -f deployment/kubernetes/ingress.yaml

    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/onex-api -n onex

    # Check deployment status
    if kubectl get pods -n onex | grep -q "Running"; then
        log_success "ONEX deployed successfully on Kubernetes!"
        kubectl get services -n onex
    else
        log_error "Deployment failed"
        kubectl get pods -n onex
        exit 1
    fi
}

# Main installation logic
main() {
    log_info "ONEX Smart Responder Chain Installation"
    log_info "Installation type: $INSTALL_TYPE"

    # Install system dependencies
    install_system_deps

    case $INSTALL_TYPE in
        "local")
            install_local
            ;;
        "docker")
            install_docker_compose
            ;;
        "kubernetes"|"k8s")
            install_kubernetes
            ;;
        *)
            log_error "Invalid installation type: $INSTALL_TYPE"
            log_info "Usage: $0 [local|docker|kubernetes]"
            exit 1
            ;;
    esac

    log_success "Installation complete!"
}

# Run main function
main "$@"
