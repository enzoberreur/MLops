#!/bin/bash
# MLOps Demo Script for Presentation
# This script demonstrates the complete MLOps workflow

echo "======================================"
echo "MLOps Project - Demo Flow"
echo "======================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to pause and wait for user
pause() {
    echo ""
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read -r
}

echo -e "${BLUE}Step 1: Verify all services are running${NC}"
echo "----------------------------------------"
docker compose ps
pause

echo -e "${BLUE}Step 2: Trigger the data pipeline in Airflow${NC}"
echo "--------------------------------------------"
echo "The pipeline will:"
echo "  1. Download 200 dandelion and 200 grass images"
echo "  2. Upload raw data to MinIO"
echo "  3. Preprocess images (resize to 128x128)"
echo "  4. Upload processed data to MinIO"
echo "  5. Train a ResNet18 model"
echo "  6. Track metrics in MLflow"
echo ""
echo "Triggering the DAG now..."

# Trigger the DAG
docker compose exec -T airflow-scheduler airflow dags trigger dandelion_data_pipeline

echo -e "${GREEN}✓ Pipeline triggered successfully!${NC}"
echo ""
echo "Monitor the pipeline at: http://localhost:8080/dags/dandelion_data_pipeline/grid"
pause

echo -e "${BLUE}Step 3: Wait for pipeline completion${NC}"
echo "-----------------------------------"
echo "This will take approximately 5-7 minutes."
echo "The training process will:"
echo "  - Train for 3 epochs (configured in .env)"
echo "  - Log metrics to MLflow"
echo "  - Save the best model to MinIO"
echo ""
echo "Waiting for the pipeline to complete..."

# Wait for the pipeline to complete (check every 30 seconds)
for i in {1..20}; do
    status=$(docker compose exec -T airflow-scheduler airflow dags state dandelion_data_pipeline 2>/dev/null | tail -1)
    if [[ $status == *"success"* ]]; then
        echo -e "${GREEN}✓ Pipeline completed successfully!${NC}"
        break
    fi
    echo "Still running... (check $i/20)"
    sleep 30
done

pause

echo -e "${BLUE}Step 4: Verify model in MinIO${NC}"
echo "-----------------------------"
echo "Opening MinIO console in browser..."
echo "URL: http://localhost:9001"
echo "Credentials: minioadmin / minioadmin"
echo ""
echo "Navigate to:"
echo "  - dandelion-models bucket → models/latest/best_model.pt"
echo "  - mlflow-artifacts bucket → experiment artifacts"
pause

echo -e "${BLUE}Step 5: Check MLflow experiment tracking${NC}"
echo "---------------------------------------"
echo "Opening MLflow UI in browser..."
echo "URL: http://localhost:5500"
echo ""
echo "You should see:"
echo "  - Experiment 'dandelion-classifier'"
echo "  - Training metrics (accuracy, loss, f1-score)"
echo "  - Model artifacts"
pause

echo -e "${BLUE}Step 6: Test the FastAPI endpoint${NC}"
echo "--------------------------------"
echo "First, let's check the API status:"
curl -s http://localhost:8000/health | jq .
echo ""
echo "Now let's check the API documentation:"
echo "URL: http://localhost:8000/docs"
pause

echo -e "${BLUE}Step 7: Create a test image and make a prediction${NC}"
echo "------------------------------------------------"

# Create a simple test request
echo "Testing the prediction endpoint..."
echo ""

# Download a sample dandelion image
echo "Downloading a test image..."
curl -s "https://raw.githubusercontent.com/btphan95/greenr-airflow/refs/heads/master/data/dandelion/00000001.jpg" -o /tmp/test_dandelion.jpg

if [ -f "/tmp/test_dandelion.jpg" ]; then
    echo -e "${GREEN}✓ Test image downloaded${NC}"
    echo ""
    echo "Making prediction via API..."
    
    # Make prediction
    result=$(curl -s -X POST "http://localhost:8000/predict" \
        -H "accept: application/json" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@/tmp/test_dandelion.jpg")
    
    echo "Prediction result:"
    echo "$result" | jq .
    echo ""
else
    echo -e "${YELLOW}⚠ Could not download test image${NC}"
fi
pause

echo -e "${BLUE}Step 8: Test the Streamlit web interface${NC}"
echo "--------------------------------------"
echo "Opening Streamlit app in browser..."
echo "URL: http://localhost:8501"
echo ""
echo "In the Streamlit app, you can:"
echo "  - Upload images for classification"
echo "  - See real-time predictions"
echo "  - View confidence scores"
pause

echo -e "${BLUE}Step 9: Monitor with Prometheus and Grafana${NC}"
echo "------------------------------------------"
echo "Prometheus metrics: http://localhost:9090"
echo "Grafana dashboards: http://localhost:3000 (admin/admin)"
echo ""
echo "In Grafana, you'll find:"
echo "  - API prediction metrics dashboard"
echo "  - Airflow monitoring dashboard"
pause

echo -e "${BLUE}Step 10: Check logs and monitoring${NC}"
echo "--------------------------------"
echo "View API logs:"
echo "  docker compose logs api"
echo ""
echo "View Airflow scheduler logs:"
echo "  docker compose logs airflow-scheduler"
echo ""
echo "View all metrics:"
echo "  curl http://localhost:8000/metrics"
pause

echo ""
echo "======================================"
echo -e "${GREEN}Demo Complete!${NC}"
echo "======================================"
echo ""
echo "Summary of what we demonstrated:"
echo "  ✓ Complete MLOps pipeline with Airflow"
echo "  ✓ Data ingestion and preprocessing"
echo "  ✓ Model training with PyTorch"
echo "  ✓ Experiment tracking with MLflow"
echo "  ✓ Artifact storage in MinIO (S3-compatible)"
echo "  ✓ Model serving via FastAPI"
echo "  ✓ User interface with Streamlit"
echo "  ✓ Monitoring with Prometheus & Grafana"
echo ""
echo "To stop the stack:"
echo "  docker compose down"
echo ""
echo "To restart everything:"
echo "  docker compose up -d"
echo ""
