"""
MLflow tracking utilities for experiment and model management.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

import mlflow
import mlflow.pytorch
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))


class MLflowTracker:
    """Manage MLflow experiment tracking and model logging."""
    
    def __init__(
        self,
        tracking_uri: str = "http://localhost:5000",
        experiment_name: str = "plant_classification",
        s3_endpoint: Optional[str] = None,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None
    ):
        """
        Initialize MLflow tracker.
        
        Args:
            tracking_uri: MLflow tracking server URI
            experiment_name: Name of the experiment
            s3_endpoint: S3 endpoint for artifacts
            aws_access_key: AWS access key
            aws_secret_key: AWS secret key
        """
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        
        # Set MLflow tracking URI
        mlflow.set_tracking_uri(tracking_uri)
        
        # Configure S3 for artifacts
        if s3_endpoint:
            os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint
        if aws_access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key
        if aws_secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_key
        
        # Create or get experiment
        try:
            self.experiment = mlflow.get_experiment_by_name(experiment_name)
            if self.experiment is None:
                self.experiment_id = mlflow.create_experiment(
                    experiment_name,
                    artifact_location=f"s3://mlflow/{experiment_name}"
                )
                logger.info(f"Created experiment: {experiment_name}")
            else:
                self.experiment_id = self.experiment.experiment_id
                logger.info(f"Using existing experiment: {experiment_name}")
            
            mlflow.set_experiment(experiment_name)
        except Exception as e:
            logger.warning(f"Could not connect to MLflow server: {e}")
            logger.info("Continuing without MLflow tracking")
            self.experiment_id = None
    
    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[mlflow.ActiveRun]:
        """
        Start a new MLflow run.
        
        Args:
            run_name: Name for the run
            tags: Dictionary of tags
        
        Returns:
            MLflow active run object
        """
        if self.experiment_id is None:
            return None
        
        try:
            if run_name is None:
                run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            run = mlflow.start_run(run_name=run_name, tags=tags)
            logger.info(f"Started MLflow run: {run_name} (ID: {run.info.run_id})")
            return run
        except Exception as e:
            logger.error(f"Failed to start MLflow run: {e}")
            return None
    
    def log_params(self, params: Dict[str, Any]):
        """Log parameters to MLflow."""
        try:
            mlflow.log_params(params)
            logger.debug(f"Logged {len(params)} parameters")
        except Exception as e:
            logger.error(f"Failed to log parameters: {e}")
    
    def log_param(self, key: str, value: Any):
        """Log a single parameter."""
        try:
            mlflow.log_param(key, value)
        except Exception as e:
            logger.error(f"Failed to log parameter {key}: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log metrics to MLflow."""
        try:
            mlflow.log_metrics(metrics, step=step)
            logger.debug(f"Logged {len(metrics)} metrics at step {step}")
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
    
    def log_metric(self, key: str, value: float, step: Optional[int] = None):
        """Log a single metric."""
        try:
            mlflow.log_metric(key, value, step=step)
        except Exception as e:
            logger.error(f"Failed to log metric {key}: {e}")
    
    def log_artifact(self, local_path: Path, artifact_path: Optional[str] = None):
        """Log an artifact file."""
        try:
            mlflow.log_artifact(str(local_path), artifact_path)
            logger.debug(f"Logged artifact: {local_path}")
        except Exception as e:
            logger.error(f"Failed to log artifact {local_path}: {e}")
    
    def log_artifacts(self, local_dir: Path, artifact_path: Optional[str] = None):
        """Log all artifacts in a directory."""
        try:
            mlflow.log_artifacts(str(local_dir), artifact_path)
            logger.debug(f"Logged artifacts from: {local_dir}")
        except Exception as e:
            logger.error(f"Failed to log artifacts from {local_dir}: {e}")
    
    def log_model(
        self,
        model: Any,
        artifact_path: str = "model",
        registered_model_name: Optional[str] = None,
        **kwargs
    ):
        """
        Log a PyTorch model to MLflow.
        
        Args:
            model: PyTorch model to log
            artifact_path: Path within run's artifact directory
            registered_model_name: Name for model registry
            **kwargs: Additional arguments for mlflow.pytorch.log_model
        """
        try:
            mlflow.pytorch.log_model(
                model,
                artifact_path=artifact_path,
                registered_model_name=registered_model_name,
                **kwargs
            )
            logger.success(f"Logged model to MLflow: {artifact_path}")
            
            if registered_model_name:
                logger.info(f"Registered model: {registered_model_name}")
        except Exception as e:
            logger.error(f"Failed to log model: {e}")
    
    def log_figure(self, figure: Any, artifact_file: str):
        """Log a matplotlib figure."""
        try:
            mlflow.log_figure(figure, artifact_file)
            logger.debug(f"Logged figure: {artifact_file}")
        except Exception as e:
            logger.error(f"Failed to log figure: {e}")
    
    def log_dict(self, dictionary: Dict, artifact_file: str):
        """Log a dictionary as JSON artifact."""
        try:
            mlflow.log_dict(dictionary, artifact_file)
            logger.debug(f"Logged dict: {artifact_file}")
        except Exception as e:
            logger.error(f"Failed to log dict: {e}")
    
    def log_text(self, text: str, artifact_file: str):
        """Log text content."""
        try:
            mlflow.log_text(text, artifact_file)
            logger.debug(f"Logged text: {artifact_file}")
        except Exception as e:
            logger.error(f"Failed to log text: {e}")
    
    def set_tags(self, tags: Dict[str, str]):
        """Set tags for the current run."""
        try:
            mlflow.set_tags(tags)
            logger.debug(f"Set {len(tags)} tags")
        except Exception as e:
            logger.error(f"Failed to set tags: {e}")
    
    def set_tag(self, key: str, value: str):
        """Set a single tag."""
        try:
            mlflow.set_tag(key, value)
        except Exception as e:
            logger.error(f"Failed to set tag {key}: {e}")
    
    def end_run(self, status: str = "FINISHED"):
        """End the current MLflow run."""
        try:
            mlflow.end_run(status=status)
            logger.info(f"Ended MLflow run with status: {status}")
        except Exception as e:
            logger.error(f"Failed to end run: {e}")
    
    def log_training_metrics(
        self,
        epoch: int,
        train_loss: float,
        train_acc: float,
        val_loss: float,
        val_acc: float,
        learning_rate: float
    ):
        """
        Log training metrics for an epoch.
        
        Args:
            epoch: Current epoch number
            train_loss: Training loss
            train_acc: Training accuracy
            val_loss: Validation loss
            val_acc: Validation accuracy
            learning_rate: Current learning rate
        """
        self.log_metrics({
            "train_loss": train_loss,
            "train_accuracy": train_acc,
            "val_loss": val_loss,
            "val_accuracy": val_acc,
            "learning_rate": learning_rate
        }, step=epoch)
    
    def log_system_metrics(self):
        """Log system information."""
        try:
            import platform
            import psutil
            
            system_info = {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "cpu_count": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2)
            }
            
            for key, value in system_info.items():
                self.set_tag(key, str(value))
            
            logger.debug("Logged system metrics")
        except Exception as e:
            logger.warning(f"Could not log system metrics: {e}")
    
    def get_run_info(self) -> Optional[Dict]:
        """Get information about the current run."""
        try:
            run = mlflow.active_run()
            if run:
                return {
                    "run_id": run.info.run_id,
                    "run_name": run.info.run_name,
                    "experiment_id": run.info.experiment_id,
                    "artifact_uri": run.info.artifact_uri,
                    "lifecycle_stage": run.info.lifecycle_stage
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get run info: {e}")
            return None
    
    def search_runs(
        self,
        filter_string: str = "",
        max_results: int = 10,
        order_by: List[str] = None
    ) -> List[Dict]:
        """
        Search for runs in the experiment.
        
        Args:
            filter_string: Filter query string
            max_results: Maximum number of results
            order_by: List of order by clauses
        
        Returns:
            List of run dictionaries
        """
        try:
            runs = mlflow.search_runs(
                experiment_ids=[self.experiment_id],
                filter_string=filter_string,
                max_results=max_results,
                order_by=order_by
            )
            return runs.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to search runs: {e}")
            return []
    
    def get_best_run(
        self,
        metric: str = "val_accuracy",
        ascending: bool = False
    ) -> Optional[Dict]:
        """
        Get the best run based on a metric.
        
        Args:
            metric: Metric name to compare
            ascending: If True, lower is better
        
        Returns:
            Best run dictionary
        """
        try:
            order = "ASC" if ascending else "DESC"
            runs = self.search_runs(
                max_results=1,
                order_by=[f"metrics.{metric} {order}"]
            )
            if runs:
                return runs[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get best run: {e}")
            return None


if __name__ == "__main__":
    # Test MLflow tracker
    logger.info("Testing MLflow tracker...")
    
    # Initialize tracker
    tracker = MLflowTracker(
        tracking_uri="http://localhost:5000",
        experiment_name="test_experiment",
        s3_endpoint="http://localhost:9000",
        aws_access_key="minioadmin",
        aws_secret_key="minioadmin"
    )
    
    # Start a test run
    tracker.start_run(run_name="test_run", tags={"test": "true"})
    
    # Log some test data
    tracker.log_params({"param1": "value1", "param2": 42})
    tracker.log_metrics({"metric1": 0.95, "metric2": 0.85}, step=1)
    
    # End run
    tracker.end_run()
    
    logger.success("MLflow tracker test completed!")
