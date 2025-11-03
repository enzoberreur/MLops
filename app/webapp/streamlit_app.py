"""Simple Streamlit frontend for interacting with the FastAPI service."""
from __future__ import annotations

import io
import os
from typing import Any, Dict

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Dandelion vs Grass", page_icon="🌼")
st.title("🌼 Dandelion or Grass?")
st.write("Upload an image to get a prediction from the model served via FastAPI.")

uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded image", use_column_width=True)

if uploaded_file and st.button("Predict"):
    st.info("Sending image to the API...")
    try:
        response = requests.post(
            f"{API_URL}/predict",
            files={"file": (uploaded_file.name, io.BytesIO(uploaded_file.getvalue()), uploaded_file.type or "image/jpeg")},
            timeout=30,
        )
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()
        st.success(f"Prediction: {payload['prediction']} (confidence {payload['confidence']:.2f})")
        st.json(payload.get("class_probabilities", {}))
    except requests.RequestException as exc:
        st.error(f"API request failed: {exc}")
    except Exception as exc:  # pragma: no cover - user feedback
        st.error(f"Unexpected error: {exc}")
else:
    st.write("⬆️ Upload an image to enable the prediction button.")
