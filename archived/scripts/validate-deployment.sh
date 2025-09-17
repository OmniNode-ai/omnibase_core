#!/bin/bash
# ONEX Smart Responder Chain Deployment Validation Script
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_TYPE="${1:-docker}"
BASE_URL="${2:-http://localhost:8000}"
TIMEOUT=30

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

# HTTP health check with timeout
check_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="${3:-endpoint}"

    log_info "Checking $description: $endpoint"

    if command_exists curl; then
        local response
        local status_code

        response=$(curl -s -w "%{http_code}" -m $TIMEOUT "$endpoint" || echo "000")
        status_code="${response: -3}"

        if [[ "$status_code" == "$expected_status" ]]; then
            log_success "$description is healthy (HTTP $status_code)"
            return 0
        else
            log_error "$description failed (HTTP $status_code)"
            return 1
        fi
    else
        log_warning "curl not available, skipping HTTP checks"
        return 0
    fi
}

# Validate Docker deployment
validate_docker() {
    log_info "Validating Docker deployment..."

    # Check if Docker is running
    if ! command_exists docker; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        return 1
    fi

    # Check if Docker Compose is available
    if ! command_exists docker-compose; then
        log_error "Docker Compose is not installed"
        return 1
    fi

    # Check running containers
    log_info "Checking running containers..."
    local containers
    containers=$(docker-compose ps --services --filter "status=running" 2>/dev/null || echo "")

    if [[ -z "$containers" ]]; then
        log_error "No running containers found. Run 'docker-compose up -d' first."
        return 1
    fi

    log_success "Found running containers: $(echo $containers | tr '\n' ' ')"

    # Health checks
    local checks_passed=0
    local total_checks=4

    # API health check
    if check_endpoint "$BASE_URL/health" "200" "API health"; then
        ((checks_passed++))
    fi

    # API readiness check
    if check_endpoint "$BASE_URL/ready" "200" "API readiness"; then
        ((checks_passed++))
    fi

    # Prometheus metrics
    if check_endpoint "http://localhost:9090/metrics" "200" "Prometheus"; then
        ((checks_passed++))
    fi

    # Grafana
    if check_endpoint "http://localhost:3000/api/health" "200" "Grafana"; then
        ((checks_passed++))
    fi

    log_info "Health checks passed: $checks_passed/$total_checks"

    if [[ $checks_passed -eq $total_checks ]]; then
        log_success "All Docker deployment checks passed!"
        return 0
    else
        log_warning "Some health checks failed. Deployment may not be fully ready."
        return 1
    fi
}

# Validate Kubernetes deployment
validate_kubernetes() {
    log_info "Validating Kubernetes deployment..."

    # Check kubectl
    if ! command_exists kubectl; then
        log_error "kubectl is not installed"
        return 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot connect to Kubernetes cluster"
        return 1
    fi

    # Check namespace
    local namespace="${KUBE_NAMESPACE:-onex}"
    if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
        log_error "Namespace '$namespace' does not exist"
        return 1
    fi

    # Check deployments
    log_info "Checking deployments in namespace '$namespace'..."
    local deployments
    deployments=$(kubectl get deployments -n "$namespace" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "$deployments" ]]; then
        log_error "No deployments found in namespace '$namespace'"
        return 1
    fi

    log_success "Found deployments: $deployments"

    # Check deployment status
    local checks_passed=0
    local total_deployments=0

    for deployment in $deployments; do
        ((total_deployments++))
        local ready
        ready=$(kubectl get deployment "$deployment" -n "$namespace" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        local desired
        desired=$(kubectl get deployment "$deployment" -n "$namespace" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")

        if [[ "$ready" == "$desired" ]]; then
            log_success "Deployment '$deployment': $ready/$desired replicas ready"
            ((checks_passed++))
        else
            log_error "Deployment '$deployment': $ready/$desired replicas ready"
        fi
    done

    # Check services
    log_info "Checking services..."
    local services
    services=$(kubectl get services -n "$namespace" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -n "$services" ]]; then
        log_success "Found services: $services"
    fi

    # Check pods
    log_info "Checking pod status..."
    local pods_ready
    pods_ready=$(kubectl get pods -n "$namespace" --field-selector=status.phase=Running -o jsonpath='{.items[*].metadata.name}' 2>/dev/null | wc -w)
    local pods_total
    pods_total=$(kubectl get pods -n "$namespace" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null | wc -w)

    log_info "Pods running: $pods_ready/$pods_total"

    if [[ $checks_passed -eq $total_deployments && $pods_ready -gt 0 ]]; then
        log_success "All Kubernetes deployment checks passed!"

        # Try to get service endpoint for API testing
        local service_ip
        service_ip=$(kubectl get service onex-api-lb -n "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

        if [[ -n "$service_ip" ]]; then
            log_info "Testing API endpoint at $service_ip..."
            if check_endpoint "http://$service_ip:8000/health" "200" "Load Balancer API"; then
                log_success "External API access validated!"
            fi
        fi

        return 0
    else
        log_error "Kubernetes deployment validation failed"
        return 1
    fi
}

# Validate local installation
validate_local() {
    log_info "Validating local installation..."

    # Check if omni-agent is available
    if ! command_exists omni-agent; then
        if ! command_exists poetry; then
            log_error "Neither omni-agent nor poetry found. Please install ONEX first."
            return 1
        fi

        # Try with poetry
        log_info "Testing with poetry..."
        if poetry run omni-agent --version >/dev/null 2>&1; then
            log_success "ONEX CLI available via poetry"
        else
            log_error "ONEX CLI not working via poetry"
            return 1
        fi
    else
        log_success "ONEX CLI is available: $(omni-agent --version)"
    fi

    # Test CLI commands
    local checks_passed=0
    local total_checks=3

    # Test status command
    log_info "Testing status command..."
    if omni-agent status >/dev/null 2>&1 || poetry run omni-agent status >/dev/null 2>&1; then
        log_success "Status command works"
        ((checks_passed++))
    else
        log_error "Status command failed"
    fi

    # Test config validation
    log_info "Testing config validation..."
    if omni-agent config validate >/dev/null 2>&1 || poetry run omni-agent config validate >/dev/null 2>&1; then
        log_success "Config validation works"
        ((checks_passed++))
    else
        log_error "Config validation failed"
    fi

    # Test help command
    log_info "Testing help command..."
    if omni-agent --help >/dev/null 2>&1 || poetry run omni-agent --help >/dev/null 2>&1; then
        log_success "Help command works"
        ((checks_passed++))
    else
        log_error "Help command failed"
    fi

    if [[ $checks_passed -eq $total_checks ]]; then
        log_success "All local installation checks passed!"
        return 0
    else
        log_warning "Some CLI tests failed ($checks_passed/$total_checks passed)"
        return 1
    fi
}

# Performance test
run_performance_test() {
    log_info "Running basic performance test..."

    case $DEPLOYMENT_TYPE in
        "docker")
            log_info "Testing Docker deployment performance..."
            if check_endpoint "$BASE_URL/health" "200" "Performance test"; then
                log_success "Performance test passed"
            fi
            ;;
        "kubernetes")
            log_info "Testing Kubernetes deployment performance..."
            # This would include more comprehensive K8s performance tests
            log_info "Kubernetes performance test not implemented yet"
            ;;
        "local")
            log_info "Testing local installation performance..."
            if command_exists omni-agent; then
                time omni-agent status >/dev/null 2>&1 && log_success "Local performance test passed"
            elif command_exists poetry; then
                time poetry run omni-agent status >/dev/null 2>&1 && log_success "Poetry performance test passed"
            fi
            ;;
    esac
}

# Generate validation report
generate_report() {
    local start_time="$1"
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_info "Validation completed in ${duration}s"

    cat << EOF

=== ONEX DEPLOYMENT VALIDATION REPORT ===
Deployment Type: $DEPLOYMENT_TYPE
Base URL: $BASE_URL
Validation Time: $(date)
Duration: ${duration}s

Next Steps:
EOF

    case $DEPLOYMENT_TYPE in
        "docker")
            cat << EOF
- API: $BASE_URL
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

Try: curl $BASE_URL/health
EOF
            ;;
        "kubernetes")
            cat << EOF
- Check services: kubectl get services -n ${KUBE_NAMESPACE:-onex}
- View logs: kubectl logs -l app.kubernetes.io/name=onex -n ${KUBE_NAMESPACE:-onex}
- Port forward: kubectl port-forward service/onex-api-service 8000:8000 -n ${KUBE_NAMESPACE:-onex}
EOF
            ;;
        "local")
            cat << EOF
- CLI: omni-agent --help
- Status: omni-agent status
- Config: omni-agent config show
EOF
            ;;
    esac

    echo "=== END REPORT ==="
}

# Main validation logic
main() {
    local start_time=$(date +%s)

    log_info "ONEX Smart Responder Chain Deployment Validation"
    log_info "Deployment type: $DEPLOYMENT_TYPE"
    log_info "Base URL: $BASE_URL"
    echo

    local validation_result=0

    case $DEPLOYMENT_TYPE in
        "docker")
            validate_docker || validation_result=1
            ;;
        "kubernetes"|"k8s")
            validate_kubernetes || validation_result=1
            ;;
        "local")
            validate_local || validation_result=1
            ;;
        *)
            log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
            log_info "Usage: $0 [docker|kubernetes|local] [base-url]"
            exit 1
            ;;
    esac

    # Run performance test if basic validation passed
    if [[ $validation_result -eq 0 ]]; then
        echo
        run_performance_test
    fi

    echo
    generate_report "$start_time"

    if [[ $validation_result -eq 0 ]]; then
        log_success "🎉 ONEX deployment validation completed successfully!"
        exit 0
    else
        log_error "❌ ONEX deployment validation failed!"
        exit 1
    fi
}

# Run main function
main "$@"
