"""
Model loading utilities for the API.
Supports loading from MLflow registry or local storage.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
import torch
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.model import PlantClassifier


class ModelLoader:
    """Load and manage ML models for inference."""
    
    def __init__(
        self,
        model_source: str = "local",  # "local" or "mlflow"
        model_path: Optional[Path] = None,
        mlflow_model_uri: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        Initialize model loader.
        
        Args:
            model_source: Source of the model ("local" or "mlflow")
            model_path: Path to local model checkpoint
            mlflow_model_uri: MLflow model URI (e.g., "models:/plant_classifier/Production")
            device: Device to load model on
        """
        self.model_source = model_source
        self.model_path = model_path
        self.mlflow_model_uri = mlflow_model_uri
        self.device = device
        self.model = None
        self.model_info = {}
        
    def load_from_local(self, checkpoint_path: Path) -> torch.nn.Module:
        """
        Load model from local checkpoint.
        
        Args:
            checkpoint_path: Path to the checkpoint file
            
        Returns:
            Loaded model
        """
        logger.info(f"Loading model from local checkpoint: {checkpoint_path}")
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        # Load checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        # Extract model info
        self.model_info = {
            "epoch": checkpoint.get("epoch", "unknown"),
            "val_accuracy": checkpoint.get("val_accuracy", "unknown"),
            "backbone": checkpoint.get("backbone", "resnet18"),
            "num_classes": checkpoint.get("num_classes", 2)
        }
        
        # Create model
        model = PlantClassifier(
            backbone=self.model_info["backbone"],
            num_classes=self.model_info["num_classes"]
        )
        
        # Load state dict
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(self.device)
        model.eval()
        
        logger.success(f"Model loaded successfully from {checkpoint_path}")
        logger.info(f"Model info: {self.model_info}")
        
        return model
    
    def load_from_mlflow(self, model_uri: str) -> torch.nn.Module:
        """
        Load model from MLflow registry.
        
        Args:
            model_uri: MLflow model URI
            
        Returns:
            Loaded model
        """
        logger.info(f"Loading model from MLflow: {model_uri}")
        
        try:
            import mlflow.pytorch
            
            # Load model
            model = mlflow.pytorch.load_model(model_uri, map_location=self.device)
            model.eval()
            
            # Try to get run info
            try:
                import mlflow
                run_id = model_uri.split("/")[-2] if "runs:/" in model_uri else None
                if run_id:
                    run = mlflow.get_run(run_id)
                    self.model_info = {
                        "run_id": run_id,
                        "val_accuracy": run.data.metrics.get("val_accuracy", "unknown"),
                        "backbone": run.data.params.get("backbone", "unknown"),
                        "experiment": run.info.experiment_id
                    }
            except Exception as e:
                logger.warning(f"Could not fetch run info: {e}")
                self.model_info = {"model_uri": model_uri}
            
            logger.success(f"Model loaded successfully from MLflow")
            logger.info(f"Model info: {self.model_info}")
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model from MLflow: {e}")
            raise
    
    def load(self) -> torch.nn.Module:
        """
        Load model based on configured source.
        
        Returns:
            Loaded model ready for inference
        """
        if self.model is not None:
            logger.info("Model already loaded, returning cached model")
            return self.model
        
        if self.model_source == "local":
            if self.model_path is None:
                raise ValueError("model_path must be provided for local loading")
            self.model = self.load_from_local(self.model_path)
            
        elif self.model_source == "mlflow":
            if self.mlflow_model_uri is None:
                raise ValueError("mlflow_model_uri must be provided for MLflow loading")
            self.model = self.load_from_mlflow(self.mlflow_model_uri)
            
        else:
            raise ValueError(f"Invalid model_source: {self.model_source}")
        
        return self.model
    
    def get_model(self) -> torch.nn.Module:
        """Get the loaded model (load if not already loaded)."""
        if self.model is None:
            self.load()
        return self.model
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata."""
        return self.model_info
    
    def reload(self) -> torch.nn.Module:
        """Reload the model (useful for model updates)."""
        logger.info("Reloading model...")
        self.model = None
        return self.load()


def get_default_model_loader(device: str = "cpu") -> ModelLoader:
    """
    Get default model loader with best available model.
    
    Priority:
    1. MLflow Production model
    2. Local best_model.pth
    
    Args:
        device: Device to load model on
        
    Returns:
        Configured ModelLoader
    """
    # Try MLflow first
    try:
        import mlflow
        mlflow.set_tracking_uri("http://localhost:5001")
        
        # Try to get production model
        model_uri = "models:/resnet18_plant_classifier/Production"
        loader = ModelLoader(
            model_source="mlflow",
            mlflow_model_uri=model_uri,
            device=device
        )
        loader.load()
        logger.info("Using MLflow Production model")
        return loader
    except Exception as e:
        logger.warning(f"Could not load from MLflow: {e}")
    
    # Fallback to local
    from src.config.config import PROJECT_ROOT
    checkpoint_path = PROJECT_ROOT / "models" / "checkpoints" / "best_model.pth"
    
    if checkpoint_path.exists():
        logger.info("Using local best_model.pth")
        loader = ModelLoader(
            model_source="local",
            model_path=checkpoint_path,
            device=device
        )
        loader.load()  # Load the model immediately
        return loader
    
    raise RuntimeError("No model found. Train a model first or specify model path.")


if __name__ == "__main__":
    # Test model loading
    logger.info("Testing model loader...")
    
    # Test local loading
    from src.config.config import PROJECT_ROOT
    checkpoint_path = PROJECT_ROOT / "models" / "checkpoints" / "best_model.pth"
    
    if checkpoint_path.exists():
        loader = ModelLoader(
            model_source="local",
            model_path=checkpoint_path,
            device="cpu"
        )
        model = loader.load()
        logger.success(f"Local model loaded: {type(model)}")
        logger.info(f"Model info: {loader.get_model_info()}")
    
    # Test default loader
    default_loader = get_default_model_loader()
    logger.success("Default loader initialized successfully")
