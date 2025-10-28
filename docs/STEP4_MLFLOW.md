# Étape 4 : MLflow Tracking et Model Registry 🎯

## Vue d'ensemble

Cette étape implémente le tracking complet des expériences avec MLflow, incluant le logging des métriques, paramètres, artifacts et modèles. MLflow utilise PostgreSQL pour le backend de métadonnées et Minio/S3 pour le stockage des artifacts.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                Training Script                        │
│            (train_with_mlflow.py)                    │
└───────────────────┬──────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────┐
│            MLflow Tracker Wrapper                     │
│         (src/tracking/mlflow_tracker.py)             │
│  - Log params, metrics, artifacts                    │
│  - Start/end runs                                    │
│  - Model logging                                     │
└─────┬────────────────────────────────────────┬───────┘
      │                                        │
      ▼                                        ▼
┌─────────────────┐                  ┌──────────────────┐
│  MLflow Server  │                  │   Minio (S3)     │
│   (Port 5001)   │                  │   (Port 9000)    │
│                 │                  │                  │
│  - Tracking UI  │◄─────────────────┤  - Artifacts     │
│  - REST API     │                  │  - Models        │
│  - Experiments  │                  │  - Plots         │
└────────┬────────┘                  └──────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Port 5432)   │
│                 │
│  - Runs         │
│  - Parameters   │
│  - Metrics      │
│  - Tags         │
└─────────────────┘
```

## Infrastructure Docker

### Services Déployés

1. **PostgreSQL** (Backend de métadonnées)
   - Port: 5432
   - Database: mlflow
   - User: mlflow / mlflow
   - Stocke: runs, params, metrics, tags

2. **Minio** (Stockage d'artifacts)
   - API Port: 9000
   - Console Port: 9001
   - Buckets: models, plants-images, data, **mlflow**
   - Stocke: models, plots, artifacts

3. **MLflow Server** (Tracking Server)
   - Port: 5001
   - UI: http://localhost:5001
   - Backend: PostgreSQL
   - Artifact Store: S3 (Minio)

### Configuration

#### docker-compose.yml

```yaml
services:
  # PostgreSQL for MLflow backend
  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: mlflow
      POSTGRES_PASSWORD: mlflow
      POSTGRES_DB: mlflow

  # Minio for S3-compatible storage  
  minio:
    image: minio/minio:latest
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"

  # MLflow tracking server
  mlflow:
    image: python:3.9-slim
    ports: ["5001:5000"]
    environment:
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
    command: |
      mlflow server 
        --backend-store-uri postgresql://mlflow:mlflow@postgres:5432/mlflow 
        --default-artifact-root s3://mlflow/ 
        --host 0.0.0.0 
        --port 5000
```

## Code Implémenté

### 1. MLflowTracker (`src/tracking/mlflow_tracker.py`)

Classe wrapper complète pour MLflow avec les méthodes suivantes :

#### Initialisation
```python
tracker = MLflowTracker(
    tracking_uri="http://localhost:5001",
    experiment_name="plant_classification",
    s3_endpoint="http://localhost:9000",
    aws_access_key="minioadmin",
    aws_secret_key="minioadmin"
)
```

#### Gestion des Runs
```python
# Démarrer un run
tracker.start_run(run_name="resnet18_experiment", tags={"model": "resnet18"})

# Terminer un run
tracker.end_run(status="FINISHED")
```

#### Logging de Paramètres
```python
# Paramètres uniques
tracker.log_param("learning_rate", 0.001)

# Paramètres multiples
tracker.log_params({
    "backbone": "resnet18",
    "epochs": 10,
    "batch_size": 32
})
```

#### Logging de Métriques
```python
# Métrique unique
tracker.log_metric("accuracy", 0.95, step=10)

# Métriques multiples par époque
tracker.log_metrics({
    "train_loss": 0.1,
    "val_loss": 0.2,
    "train_acc": 0.95,
    "val_acc": 0.93
}, step=epoch)

# Méthode spécialisée pour entraînement
tracker.log_training_metrics(
    epoch=10,
    train_loss=0.1,
    train_acc=0.95,
    val_loss=0.2,
    val_acc=0.93,
    learning_rate=0.0001
)
```

#### Logging d'Artifacts
```python
# Fichier unique
tracker.log_artifact(Path("model.pth"), artifact_path="models")

# Répertoire entier
tracker.log_artifacts(Path("logs/"), artifact_path="training_logs")

# Figure matplotlib
tracker.log_figure(fig, "confusion_matrix.png")

# Dictionnaire JSON
tracker.log_dict(history, "training_history.json")

# Texte
tracker.log_text(summary, "model_summary.txt")
```

#### Logging de Modèles PyTorch
```python
# Log avec PyTorch flavor
tracker.log_model(
    model=model,
    artifact_path="model",
    registered_model_name="plant_classifier_resnet18"
)
```

#### Tags et Métadonnées
```python
# Tags uniques
tracker.set_tag("status", "production")

# Tags multiples
tracker.set_tags({
    "best_val_accuracy": "0.9500",
    "best_epoch": "7",
    "framework": "pytorch"
})

# Métriques système automatiques
tracker.log_system_metrics()  # CPU, RAM, Python version, etc.
```

#### Recherche et Analyse
```python
# Rechercher des runs
runs = tracker.search_runs(
    filter_string="metrics.val_accuracy > 0.90",
    max_results=10,
    order_by=["metrics.val_accuracy DESC"]
)

# Obtenir le meilleur run
best_run = tracker.get_best_run(
    metric="val_accuracy",
    ascending=False  # Plus haut est mieux
)
```

### 2. Script d'Entraînement avec MLflow (`train_with_mlflow.py`)

Script complet d'entraînement avec intégration MLflow :

```bash
python3 train_with_mlflow.py \
    --backbone resnet18 \
    --epochs 10 \
    --batch-size 32 \
    --learning-rate 0.001 \
    --experiment-name plant_classification \
    --run-name resnet18_exp1
```

#### Paramètres CLI

```
Model:
  --backbone           : resnet18, resnet50, efficientnet_b0, mobilenet_v2
  --epochs             : Nombre d'époques
  --batch-size         : Taille du batch
  --learning-rate      : Taux d'apprentissage
  --device             : cuda ou cpu

Training:
  --freeze-backbone    : Geler le backbone initialement
  --unfreeze-epoch     : Époque pour dégeler
  --early-stopping-patience : Patience pour early stopping

MLflow:
  --experiment-name    : Nom de l'expérience MLflow
  --run-name           : Nom du run (auto si non spécifié)
  --no-mlflow          : Désactiver MLflow
```

#### Fonctionnalités

- ✅ Logging automatique de tous les hyperparamètres
- ✅ Logging des métriques à chaque époque (train/val loss/acc)
- ✅ Logging du learning rate à chaque époque
- ✅ Logging de l'historique d'entraînement (JSON)
- ✅ Logging du modèle PyTorch (best model)
- ✅ Logging des métriques système (CPU, RAM, Python)
- ✅ Enregistrement dans le Model Registry
- ✅ Tags pour catégorisation

### 3. Script de Vérification (`verify_mlflow.py`)

Script de test complet de l'installation MLflow :

```bash
python3 verify_mlflow.py
```

#### Tests Effectués

1. ✅ Connexion au serveur MLflow
2. ✅ Création d'expérience
3. ✅ Démarrage de run
4. ✅ Logging de paramètres
5. ✅ Logging de métriques
6. ✅ Logging d'artifacts
7. ✅ Setting de tags
8. ✅ Récupération d'informations de run

## Utilisation

### Démarrer l'Infrastructure

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier l'état
docker-compose ps

# Voir les logs
docker-compose logs -f mlflow
```

### Vérifier MLflow

```bash
python3 verify_mlflow.py
```

Output attendu :
```
✓ MLflow server is ready!
✓ MLflow tracker initialized
✓ Test run started
✓ Parameters logged
✓ Metrics logged (5 steps)
✓ Artifact logged
✓ Tags set
✓ ALL MLFLOW TESTS PASSED
```

### Entraîner avec MLflow

```bash
# Entraînement rapide (3 époques de test)
python3 train_with_mlflow.py --epochs 3

# Entraînement complet
python3 train_with_mlflow.py --epochs 10 --backbone resnet18

# Entraînement avec modèle différent
python3 train_with_mlflow.py --epochs 15 --backbone resnet50 \
    --batch-size 16 --learning-rate 0.0001

# Sans MLflow
python3 train_with_mlflow.py --epochs 10 --no-mlflow
```

### Accéder à l'Interface MLflow

1. **Ouvrir le navigateur** : http://localhost:5001

2. **Vue des Expériences** :
   - Liste de toutes les expériences
   - Nombre de runs par expérience
   - Liens vers les détails

3. **Vue des Runs** :
   - Tableau comparatif de tous les runs
   - Métriques en colonnes (triables, filtrables)
   - Graphiques de comparaison

4. **Détails d'un Run** :
   - Onglet **Overview** : Informations générales
   - Onglet **Parameters** : Tous les hyperparamètres
   - Onglet **Metrics** : Graphiques des métriques
   - Onglet **Artifacts** : Fichiers (modèles, plots, logs)
   - Onglet **Tags** : Métadonnées

### Accéder aux Artifacts (Minio)

1. **Ouvrir le navigateur** : http://localhost:9001

2. **Se connecter** :
   - Username: minioadmin
   - Password: minioadmin

3. **Naviguer** :
   - Bucket `mlflow` : Tous les artifacts MLflow
   - Structure : `experiment_name/run_id/artifacts/`

## Métriques Trackées

### Par Époque

- `train_loss` : Loss sur le training set
- `train_accuracy` : Accuracy sur le training set
- `val_loss` : Loss sur le validation set
- `val_accuracy` : Accuracy sur le validation set
- `learning_rate` : Learning rate courant

### Système

- `python_version` : Version Python
- `platform` : OS et architecture
- `cpu_count` : Nombre de CPUs
- `memory_gb` : RAM totale en GB

### Paramètres Loggés

```python
{
    "backbone": "resnet18",
    "epochs": 10,
    "batch_size": 32,
    "learning_rate": 0.001,
    "device": "cpu",
    "freeze_backbone": True,
    "unfreeze_epoch": 5,
    "early_stopping_patience": 10,
    "optimizer": "AdamW",
    "scheduler": "CosineAnnealingLR",
    "loss_function": "CrossEntropyLoss",
    "num_classes": 2,
    "train_size": 280,
    "val_size": 60,
    "test_size": 60,
    "total_parameters": 11689538,
    "trainable_parameters": 1443842
}
```

### Artifacts Loggés

- `training/training_history.json` : Historique complet
- `models/best_model.pth` : Meilleur checkpoint
- `model/` : Modèle PyTorch avec MLflow flavor

## Comparaison des Runs

### Via l'UI MLflow

1. Sélectionner plusieurs runs (checkbox)
2. Cliquer "Compare"
3. Voir les tableaux et graphiques comparatifs
4. Exporter en CSV si besoin

### Via l'API Python

```python
from src.tracking.mlflow_tracker import MLflowTracker

tracker = MLflowTracker(tracking_uri="http://localhost:5001")

# Rechercher les meilleurs runs
best_runs = tracker.search_runs(
    filter_string="metrics.val_accuracy > 0.90",
    max_results=5,
    order_by=["metrics.val_accuracy DESC"]
)

for run in best_runs:
    print(f"Run: {run['tags.mlflow.runName']}")
    print(f"Accuracy: {run['metrics.val_accuracy']:.4f}")
    print(f"Backbone: {run['params.backbone']}")
    print()
```

## Model Registry

### Enregistrement Automatique

Lors de l'entraînement avec `train_with_mlflow.py`, le modèle est automatiquement enregistré :

```python
mlflow.pytorch.log_model(
    model=model,
    artifact_path="model",
    registered_model_name=f"{backbone}_plant_classifier"
)
```

### Versions de Modèles

- MLflow crée automatiquement des versions (v1, v2, v3...)
- Chaque version est liée à un run spécifique
- Possibilité de promouvoir en "Production", "Staging", etc.

### Charger un Modèle depuis le Registry

```python
import mlflow.pytorch

# Charger la version de production
model_uri = "models:/resnet18_plant_classifier/Production"
model = mlflow.pytorch.load_model(model_uri)

# Ou une version spécifique
model_uri = "models:/resnet18_plant_classifier/1"
model = mlflow.pytorch.load_model(model_uri)
```

## Configuration

### Variables d'Environnement (`.env`)

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5001
MLFLOW_EXPERIMENT_NAME=plant_classification
MLFLOW_S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

### Configuration Programmatique

```python
import os
os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5001"
os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
```

## Commandes Utiles

### Docker

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Redémarrer MLflow
docker-compose restart mlflow

# Logs
docker-compose logs -f mlflow
docker-compose logs -f postgres
docker-compose logs -f minio

# État
docker-compose ps
```

### MLflow CLI

```bash
# Lister les expériences
mlflow experiments list --tracking-uri http://localhost:5001

# Chercher des runs
mlflow runs list --experiment-name plant_classification

# Servir un modèle
mlflow models serve -m models:/resnet18_plant_classifier/1 -p 8080
```

## Troubleshooting

### MLflow ne démarre pas

```bash
# Vérifier les logs
docker-compose logs mlflow

# Redémarrer
docker-compose restart mlflow

# Recréer le container
docker-compose up -d --force-recreate mlflow
```

### Erreur de connexion PostgreSQL

```bash
# Vérifier que PostgreSQL est prêt
docker-compose logs postgres

# Attendre le healthcheck
docker-compose ps postgres
```

### Artifacts non accessibles

```bash
# Vérifier Minio
docker-compose logs minio

# Vérifier le bucket mlflow
# Aller sur http://localhost:9001
```

### Port 5001 déjà utilisé

Modifier dans `docker-compose.yml` et `.env` :
```yaml
ports:
  - "5002:5000"  # Au lieu de 5001:5000
```

```bash
MLFLOW_TRACKING_URI=http://localhost:5002
```

## Avantages de MLflow

### ✅ Traçabilité Complète
- Historique de tous les runs
- Comparaison facile
- Reproductibilité garantie

### ✅ Collaboration
- Partage d'expériences
- UI centralisée
- Artifacts accessibles

### ✅ Versioning de Modèles
- Registry centralisé
- Promotion de versions
- Rollback facile

### ✅ Intégration
- Compatible avec PyTorch, TensorFlow, sklearn...
- API REST pour CI/CD
- Export vers production

## Prochaines Étapes (Étape 5)

L'infrastructure MLflow est maintenant en place pour :
- **API REST** : Servir les modèles enregistrés
- **WebApp** : Interface de prédiction
- **CI/CD** : Déploiement automatique des modèles trackés
- **Monitoring** : Suivi des performances en production

## Résumé

**Étape 4 : COMPLÉTÉE AVEC SUCCÈS !** ✅

- ✅ Infrastructure Docker (PostgreSQL + MLflow + Minio)
- ✅ MLflowTracker wrapper complet
- ✅ Script d'entraînement avec tracking intégré
- ✅ Script de vérification
- ✅ Interface UI accessible
- ✅ Model Registry fonctionnel
- ✅ Documentation complète

**Prêt pour l'Étape 5** : API REST pour serving de modèles

---

**Date** : 28 octobre 2025
**Lignes de code** : ~800 lignes
**Services déployés** : 4 (Postgres, Minio, MLflow, Minio-client)
**Ports utilisés** : 5001 (MLflow), 5432 (Postgres), 9000 (Minio API), 9001 (Minio Console)
