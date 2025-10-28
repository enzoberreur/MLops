#!/bin/bash
# Deploy Plant Classification API to Kubernetes

set -e

echo "🚀 Deploying Plant Classification API to Kubernetes"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker found"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} kubectl found"

# Check cluster access
echo -e "\n${YELLOW}Checking Kubernetes cluster access...${NC}"
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster.${NC}"
    echo "Please enable Kubernetes in Docker Desktop:"
    echo "Docker Desktop → Settings → Kubernetes → Enable Kubernetes"
    exit 1
fi
echo -e "${GREEN}✓${NC} Cluster accessible"

# Check if model exists
echo -e "\n${YELLOW}Checking model file...${NC}"
if [ ! -f "models/best_model.pth" ]; then
    if [ -f "models/checkpoints/best_model.pth" ]; then
        echo -e "${YELLOW}Copying model from checkpoints...${NC}"
        cp models/checkpoints/best_model.pth models/best_model.pth
    else
        echo -e "${RED}❌ Model file not found!${NC}"
        echo "Please train a model first: python3 train_model.py"
        exit 1
    fi
fi
echo -e "${GREEN}✓${NC} Model file found"

# Build Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -t plant-classification-api:latest . || {
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
}
echo -e "${GREEN}✓${NC} Docker image built successfully"

# Test Docker image
echo -e "\n${YELLOW}Testing Docker image...${NC}"
docker run -d --name plant-api-test -p 8080:8000 plant-classification-api:latest || {
    echo -e "${RED}❌ Failed to start test container${NC}"
    exit 1
}

echo "Waiting for container to start..."
sleep 10

if curl -f http://localhost:8080/health &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker image test passed"
else
    echo -e "${RED}❌ Docker image test failed${NC}"
    docker logs plant-api-test
    docker stop plant-api-test &> /dev/null || true
    docker rm plant-api-test &> /dev/null || true
    exit 1
fi

docker stop plant-api-test &> /dev/null
docker rm plant-api-test &> /dev/null
echo -e "${GREEN}✓${NC} Test container cleaned up"

# Deploy to Kubernetes
echo -e "\n${YELLOW}Deploying to Kubernetes...${NC}"

echo "Applying ConfigMap..."
kubectl apply -f k8s/configmap.yaml || {
    echo -e "${RED}❌ Failed to apply ConfigMap${NC}"
    exit 1
}

echo "Applying Deployment..."
kubectl apply -f k8s/deployment.yaml || {
    echo -e "${RED}❌ Failed to apply Deployment${NC}"
    exit 1
}

echo "Applying HPA..."
kubectl apply -f k8s/hpa.yaml || {
    echo -e "${RED}❌ Failed to apply HPA${NC}"
    exit 1
}

# Wait for deployment
echo -e "\n${YELLOW}Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/plant-api || {
    echo -e "${RED}❌ Deployment failed to become ready${NC}"
    echo "Checking pod status..."
    kubectl get pods -l app=plant-api
    echo -e "\nPod logs:"
    kubectl logs -l app=plant-api --tail=50
    exit 1
}

# Get deployment status
echo -e "\n${GREEN}✓${NC} Deployment successful!"
echo -e "\n${YELLOW}Deployment Status:${NC}"
kubectl get pods -l app=plant-api
echo ""
kubectl get svc plant-api-service
echo ""
kubectl get hpa plant-api-hpa

# Test the deployed API
echo -e "\n${YELLOW}Testing deployed API...${NC}"
echo "Waiting for service to be ready..."
sleep 10

if curl -f http://localhost:30080/health &> /dev/null; then
    echo -e "${GREEN}✓${NC} API is accessible at http://localhost:30080"
else
    echo -e "${YELLOW}⚠${NC} API might not be ready yet. Please check:"
    echo "  kubectl get pods -l app=plant-api"
    echo "  kubectl logs -l app=plant-api"
fi

# Summary
echo -e "\n=================================================="
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=================================================="
echo ""
echo "📍 Service Endpoints:"
echo "  - API Health:  http://localhost:30080/health"
echo "  - API Docs:    http://localhost:30080/docs"
echo "  - Metrics:     http://localhost:30080/stats"
echo ""
echo "🔍 Useful Commands:"
echo "  - View pods:   kubectl get pods -l app=plant-api"
echo "  - View logs:   kubectl logs -f -l app=plant-api"
echo "  - View HPA:    kubectl get hpa plant-api-hpa"
echo "  - Scale:       kubectl scale deployment plant-api --replicas=3"
echo "  - Restart:     kubectl rollout restart deployment/plant-api"
echo "  - Delete:      kubectl delete -f k8s/"
echo ""
