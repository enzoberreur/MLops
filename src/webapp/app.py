"""
Plant Classification WebApp with Streamlit
"""

import streamlit as st
import requests
from PIL import Image
import io
import time
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# API Configuration
API_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="🌿 Plant Classification",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E7D32;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .prediction-box {
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .prediction-dandelion {
        background-color: #FFF9C4;
        border: 2px solid #FBC02D;
    }
    .prediction-grass {
        background-color: #C8E6C9;
        border: 2px solid #66BB6A;
    }
    .confidence-high {
        color: #2E7D32;
        font-weight: bold;
    }
    .confidence-medium {
        color: #F57C00;
        font-weight: bold;
    }
    .confidence-low {
        color: #D32F2F;
        font-weight: bold;
    }
    .stat-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1565C0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if the API is healthy and ready."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy" and data.get("model_loaded", False)
        return False
    except Exception:
        return False


def get_api_stats():
    """Get API statistics."""
    try:
        response = requests.get(f"{API_URL}/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def get_model_info():
    """Get model information."""
    try:
        response = requests.get(f"{API_URL}/model/info", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def predict_image(image_bytes, filename="image.jpg"):
    """Send image to API for prediction."""
    try:
        files = {"file": (filename, image_bytes, "image/jpeg")}
        response = requests.post(f"{API_URL}/predict", files=files, timeout=30)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Prediction failed: {response.status_code}"
    except Exception as e:
        return None, f"Error: {str(e)}"


def predict_batch(images_data):
    """Send multiple images to API for batch prediction."""
    try:
        files = [("files", (img["name"], img["bytes"], "image/jpeg")) for img in images_data]
        response = requests.post(f"{API_URL}/predict/batch", files=files, timeout=60)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Batch prediction failed: {response.status_code}"
    except Exception as e:
        return None, f"Error: {str(e)}"


def get_confidence_class(confidence):
    """Return CSS class based on confidence level."""
    if confidence >= 0.9:
        return "confidence-high", "🟢"
    elif confidence >= 0.7:
        return "confidence-medium", "🟡"
    else:
        return "confidence-low", "🔴"


def display_prediction(result, image=None):
    """Display prediction results in a nice format."""
    prediction = result["prediction"]
    confidence = result["confidence"]
    probabilities = result["probabilities"]
    inference_time = result["inference_time_ms"]
    
    # Determine box style
    box_class = "prediction-dandelion" if prediction == "dandelion" else "prediction-grass"
    conf_class, conf_icon = get_confidence_class(confidence)
    
    # Display in columns
    if image:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, use_column_width=True)
    else:
        col2 = st.container()
    
    with col2:
        st.markdown(f'<div class="prediction-box {box_class}">', unsafe_allow_html=True)
        
        # Prediction header
        emoji = "🌼" if prediction == "dandelion" else "🌱"
        st.markdown(f"### {emoji} Prediction: **{prediction.upper()}**")
        
        # Confidence
        st.markdown(f'<p class="{conf_class}">{conf_icon} Confidence: {confidence:.2%}</p>', 
                   unsafe_allow_html=True)
        
        # Probabilities
        st.markdown("**Class Probabilities:**")
        for class_name, prob in probabilities.items():
            st.progress(prob, text=f"{class_name}: {prob:.2%}")
        
        # Inference time
        st.caption(f"⚡ Inference time: {inference_time:.1f}ms")
        
        st.markdown('</div>', unsafe_allow_html=True)


def sidebar():
    """Display sidebar with API status and model info."""
    with st.sidebar:
        st.markdown("## 🔧 System Status")
        
        # Check API health
        is_healthy = check_api_health()
        
        if is_healthy:
            st.success("✅ API is healthy")
        else:
            st.error("❌ API is not responding")
            st.warning("Make sure the API is running on http://localhost:8000")
            st.code("python3 run_api.py")
            return False
        
        # Model info
        st.markdown("## 🤖 Model Information")
        model_info = get_model_info()
        
        if model_info:
            st.info(f"**Source:** {model_info['model_source']}")
            st.info(f"**Backbone:** {model_info.get('backbone', 'N/A')}")
            st.info(f"**Device:** {model_info['device']}")
            st.info(f"**Classes:** {', '.join(model_info['class_names'])}")
        
        # API stats
        st.markdown("## 📊 Statistics")
        stats = get_api_stats()
        
        if stats:
            st.markdown(f"""
            <div class="stat-box">
                <div class="metric-value">{stats['total_predictions']}</div>
                <div class="metric-label">Total Predictions</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="stat-box" style="margin-top: 1rem;">
                <div class="metric-value">{stats['avg_inference_time_ms']:.1f}ms</div>
                <div class="metric-label">Avg Inference Time</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Reload model button
        st.markdown("---")
        if st.button("🔄 Reload Model", use_container_width=True):
            with st.spinner("Reloading model..."):
                try:
                    response = requests.post(f"{API_URL}/model/reload", timeout=30)
                    if response.status_code == 200:
                        st.success("Model reloaded successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to reload model")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        return True


def main():
    """Main application."""
    # Display header
    st.markdown('<h1 class="main-header">🌿 Plant Classification</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload an image to classify between Dandelion and Grass</p>', 
               unsafe_allow_html=True)
    
    # Check API status in sidebar
    api_ready = sidebar()
    
    if not api_ready:
        st.stop()
    
    # Main content
    st.markdown("---")
    
    # Create tabs for different modes
    tab1, tab2, tab3 = st.tabs(["📷 Single Image", "📚 Batch Upload", "ℹ️ About"])
    
    with tab1:
        st.markdown("### Upload a single image for classification")
        
        uploaded_file = st.file_uploader(
            "Choose an image...",
            type=["jpg", "jpeg", "png"],
            help="Upload a plant image (JPEG or PNG format)"
        )
        
        if uploaded_file is not None:
            # Display image
            image = Image.open(uploaded_file)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(image, caption="Uploaded Image", use_column_width=True)
            
            # Predict button
            if st.button("🔍 Classify Image", type="primary", use_container_width=True):
                with st.spinner("Analyzing image..."):
                    # Convert image to bytes
                    img_bytes = io.BytesIO()
                    image.save(img_bytes, format='JPEG')
                    img_bytes.seek(0)
                    
                    # Get prediction
                    result, error = predict_image(img_bytes.getvalue(), uploaded_file.name)
                    
                    if result:
                        st.success("Classification complete!")
                        display_prediction(result, image)
                    else:
                        st.error(f"Prediction failed: {error}")
    
    with tab2:
        st.markdown("### Upload multiple images for batch classification")
        st.info("💡 You can upload up to 10 images at once")
        
        uploaded_files = st.file_uploader(
            "Choose images...",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Upload multiple plant images (max 10)"
        )
        
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} image(s) uploaded**")
            
            if len(uploaded_files) > 10:
                st.warning("⚠️ Maximum 10 images allowed. Only the first 10 will be processed.")
                uploaded_files = uploaded_files[:10]
            
            # Show thumbnails
            cols = st.columns(min(len(uploaded_files), 5))
            for idx, file in enumerate(uploaded_files):
                with cols[idx % 5]:
                    img = Image.open(file)
                    st.image(img, caption=file.name, use_column_width=True)
            
            # Batch predict button
            if st.button("🔍 Classify All Images", type="primary", use_container_width=True):
                with st.spinner(f"Analyzing {len(uploaded_files)} images..."):
                    # Prepare images data
                    images_data = []
                    for file in uploaded_files:
                        img = Image.open(file)
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format='JPEG')
                        img_bytes.seek(0)
                        images_data.append({
                            "name": file.name,
                            "bytes": img_bytes.getvalue(),
                            "image": img
                        })
                    
                    # Get batch predictions
                    result, error = predict_batch(images_data)
                    
                    if result:
                        st.success(f"✅ Successfully classified {result['successful']} images!")
                        
                        if result['failed'] > 0:
                            st.warning(f"⚠️ Failed to classify {result['failed']} images")
                        
                        st.info(f"⚡ Total processing time: {result['total_time_ms']:.1f}ms")
                        
                        # Display results
                        st.markdown("---")
                        st.markdown("### Results")
                        
                        for idx, pred in enumerate(result['predictions']):
                            with st.expander(f"📄 {pred['filename']}", expanded=True):
                                if pred['success']:
                                    # Find corresponding image
                                    img = next((img_data["image"] for img_data in images_data 
                                              if img_data["name"] == pred['filename']), None)
                                    display_prediction(pred['result'], img)
                                else:
                                    st.error(f"❌ Error: {pred['error']}")
                    else:
                        st.error(f"Batch prediction failed: {error}")
    
    with tab3:
        st.markdown("### About this Application")
        
        st.markdown("""
        This web application uses a deep learning model to classify plant images into two categories:
        - 🌼 **Dandelion** (Pissenlit)
        - 🌱 **Grass** (Herbe)
        
        #### 🎯 Model Details
        - **Architecture:** ResNet18 (Transfer Learning)
        - **Training Accuracy:** ~95%
        - **Input Size:** 224x224 pixels
        - **Framework:** PyTorch
        
        #### 🔧 Technology Stack
        - **Backend:** FastAPI
        - **Frontend:** Streamlit
        - **ML Tracking:** MLflow
        - **Storage:** MinIO (S3-compatible)
        - **Database:** PostgreSQL
        
        #### 📊 Features
        - Real-time image classification
        - Batch processing (up to 10 images)
        - Confidence scores and probabilities
        - API statistics tracking
        - Model hot-reload capability
        
        #### 🚀 Performance
        - Average inference time: ~30-80ms per image
        - Support for JPEG and PNG formats
        - Automatic image preprocessing
        
        #### 📝 How to Use
        1. Go to the **Single Image** tab to classify one image
        2. Use the **Batch Upload** tab to classify multiple images
        3. Check the sidebar for system status and statistics
        4. View confidence scores and class probabilities
        
        #### 🔗 API Documentation
        Access the interactive API documentation at:
        - **Swagger UI:** http://localhost:8000/docs
        - **ReDoc:** http://localhost:8000/redoc
        
        #### 📞 Endpoints
        - `POST /predict` - Single image prediction
        - `POST /predict/batch` - Batch predictions
        - `GET /health` - Health check
        - `GET /model/info` - Model information
        - `GET /stats` - API statistics
        """)
        
        st.markdown("---")
        st.markdown("**Made with ❤️ using Streamlit and FastAPI**")
        st.caption("MLOps Project - Step 6: WebApp Development")


if __name__ == "__main__":
    main()
