# Step 5: Plant Classification API 🌿

## Overview

Une API REST construite avec FastAPI pour servir le modèle de classification de plantes. L'API permet de classifier des images de plantes (pissenlit ou herbe) avec des scores de confiance.

## Architecture

```
┌─────────────────┐
│   FastAPI App   │
│   (port 8000)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │  Model  │
    │ Loader  │
    └────┬────┘
         │
    ┌────┴─────────┐
    │              │
┌───▼───┐    ┌────▼────┐
│MLflow │    │  Local  │
│ Model │    │  Model  │
└───────┘    └─────────┘
```

### Composants

1. **FastAPI Application** (`src/api/main.py`)
   - 8 endpoints REST
   - Middleware CORS
   - Validation automatique avec Pydantic
   - Documentation OpenAPI automatique
   - Gestion asynchrone des requêtes

2. **Model Loader** (`src/api/model_loader.py`)
   - Chargement depuis MLflow (priorité)
   - Fallback sur le modèle local
   - Support du hot-reload
   - Prétraitement des images

3. **Serveur Uvicorn** (`run_api.py`)
   - ASGI server
   - Auto-reload en développement
   - Accessible sur toutes les interfaces (0.0.0.0)

## Endpoints

### 1. Root - `GET /`
Informations de base sur l'API.

**Response:**
```json
{
  "message": "Plant Classification API",
  "version": "1.0.0",
  "endpoints": {
    "/predict": "Single image prediction",
    "/predict/batch": "Batch image predictions",
    "/health": "Health check",
    "/model/info": "Model information"
  }
}
```

### 2. Health Check - `GET /health`
Vérifie le statut de l'API et du modèle.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_info": {
    "epoch": 7,
    "val_accuracy": "unknown",
    "backbone": "resnet18",
    "num_classes": 2
  },
  "predictions_count": 4,
  "avg_inference_time_ms": 79.51
}
```

### 3. Single Prediction - `POST /predict`
Classifie une seule image.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (image JPEG/PNG)

**Response:**
```json
{
  "prediction": "dandelion",
  "confidence": 0.9998,
  "probabilities": {
    "dandelion": 0.9998,
    "grass": 0.0002
  },
  "inference_time_ms": 212.60
}
```

**Exemple cURL:**
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg"
```

**Exemple Python:**
```python
import requests

with open("image.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/predict",
        files={"file": f}
    )
    result = response.json()
    print(f"Prediction: {result['prediction']} ({result['confidence']:.2%})")
```

### 4. Batch Prediction - `POST /predict/batch`
Classifie plusieurs images en une seule requête (max 10).

**Request:**
- Content-Type: `multipart/form-data`
- Body: `files` (multiple images)

**Response:**
```json
{
  "predictions": [
    {
      "filename": "dandelion.jpg",
      "success": true,
      "result": {
        "prediction": "dandelion",
        "confidence": 0.9998,
        "probabilities": {
          "dandelion": 0.9998,
          "grass": 0.0002
        },
        "inference_time_ms": 212.60
      }
    },
    {
      "filename": "grass.jpg",
      "success": true,
      "result": {
        "prediction": "grass",
        "confidence": 0.5776,
        "probabilities": {
          "dandelion": 0.4224,
          "grass": 0.5776
        },
        "inference_time_ms": 28.60
      }
    }
  ],
  "total_images": 2,
  "successful": 2,
  "failed": 0,
  "total_time_ms": 241.20
}
```

**Exemple Python:**
```python
import requests

files = [
    ('files', open('image1.jpg', 'rb')),
    ('files', open('image2.jpg', 'rb'))
]

response = requests.post(
    "http://localhost:8000/predict/batch",
    files=files
)

for pred in response.json()['predictions']:
    if pred['success']:
        result = pred['result']
        print(f"{pred['filename']}: {result['prediction']} ({result['confidence']:.2%})")
```

### 5. Model Info - `GET /model/info`
Informations détaillées sur le modèle chargé.

**Response:**
```json
{
  "model_source": "local",
  "model_loaded": true,
  "device": "cpu",
  "class_names": ["dandelion", "grass"],
  "num_classes": 2,
  "backbone": "resnet18",
  "input_size": 224,
  "model_metadata": {
    "epoch": 7,
    "val_accuracy": "unknown",
    "backbone": "resnet18",
    "num_classes": 2
  }
}
```

### 6. Model Reload - `POST /model/reload`
Recharge le modèle (utile après entraînement d'une nouvelle version).

**Response:**
```json
{
  "message": "Model reloaded successfully",
  "model_source": "local",
  "model_info": {
    "epoch": 7,
    "val_accuracy": "unknown",
    "backbone": "resnet18",
    "num_classes": 2
  }
}
```

### 7. Statistics - `GET /stats`
Statistiques d'utilisation de l'API.

**Response:**
```json
{
  "total_predictions": 4,
  "avg_inference_time_ms": 79.51,
  "model_loaded": true,
  "model_source": "local"
}
```

### 8. OpenAPI Documentation - `GET /docs`
Interface Swagger UI interactive pour tester l'API.

Accès: http://localhost:8000/docs

## Prétraitement des Images

Le pipeline de prétraitement applique les transformations suivantes :

```python
1. Resize(256)           # Redimensionne à 256x256
2. CenterCrop(224)       # Crop centré à 224x224
3. ToTensor()            # Conversion en tensor PyTorch
4. Normalize(            # Normalisation ImageNet
    mean=[0.485, 0.456, 0.406],
    std=[0.229, 0.224, 0.225]
)
```

## Gestion des Erreurs

L'API retourne des messages d'erreur structurés :

### 400 Bad Request
```json
{
  "detail": "Invalid image file"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Prediction failed: <error_message>"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Model not loaded"
}
```

## Démarrage

### Prérequis
```bash
pip install fastapi==0.108.0 uvicorn==0.25.0 python-multipart==0.0.6 pydantic==2.5.3
```

### Démarrage de l'API
```bash
python3 run_api.py
```

L'API sera accessible sur : http://localhost:8000

### Tests
```bash
python3 test_api.py
```

## Performance

- **Premier appel (chargement)** : ~213 ms
- **Appels suivants** : ~29 ms
- **Batch (2 images)** : ~241 ms total
- **Charge moyenne** : ~80 ms par image

## Stratégie de Chargement du Modèle

L'API utilise une stratégie de chargement en cascade :

1. **Priorité : MLflow**
   - Cherche un modèle en stage "Production"
   - URI: `models:/resnet18_plant_classifier/Production`
   
2. **Fallback : Local**
   - Charge `models/best_model.pth`
   - Utilisé si MLflow n'est pas disponible

3. **Hot Reload**
   - Endpoint `/model/reload` pour recharger sans redémarrer
   - Utile après entraînement d'une nouvelle version

## Monitoring

L'API trackle automatiquement :
- Nombre total de prédictions
- Temps d'inférence moyen
- Source du modèle (MLflow ou local)
- Statut du modèle (chargé/non chargé)

Accessible via `/stats` et `/health`.

## CORS

L'API est configurée avec CORS pour accepter les requêtes depuis :
- http://localhost:3000 (WebApp React)
- http://localhost:8080 (Autres frontends)
- Toutes les origines en développement

## Sécurité

### Limitations
- **Max file size** : Géré par FastAPI (défaut ~10MB)
- **Max batch size** : 10 images par requête
- **Accepted formats** : JPEG, PNG

### Validation
- Validation automatique du format d'image
- Gestion des images corrompues
- Timeout sur les longues inférences

## Documentation Interactive

FastAPI génère automatiquement :

1. **Swagger UI** : http://localhost:8000/docs
   - Interface interactive
   - Test des endpoints
   - Schémas de requêtes/réponses

2. **ReDoc** : http://localhost:8000/redoc
   - Documentation alternative
   - Plus lisible pour la lecture

## Intégration avec MLflow

L'API s'intègre avec MLflow pour :
- Charger des modèles depuis le registre
- Utiliser des modèles en production
- Tracer la source du modèle utilisé

Configuration dans `.env` :
```bash
MLFLOW_TRACKING_URI=http://localhost:5001
MLFLOW_EXPERIMENT_NAME=plant-classification
```

## Logs

Les logs de l'API sont visibles dans :
- **Console** : Logs Uvicorn en temps réel
- **Format** : `[timestamp] [level] message`

Exemple :
```
INFO:     127.0.0.1:62513 - "POST /predict HTTP/1.1" 200 OK
INFO:     Prediction: dandelion (confidence: 0.9998)
```

## Next Steps

Pour la **Step 6 - WebApp** :
- Interface web React/Vue.js
- Upload d'images drag & drop
- Affichage des résultats
- Historique des prédictions
- Intégration avec cette API

## Tests Validés ✅

```
Health Check: ✓ PASSED
Root: ✓ PASSED
Model Info: ✓ PASSED
Prediction (dandelion): ✓ PASSED (confidence: 99.98%)
Prediction (grass): ✓ PASSED (confidence: 57.76%)
Batch Prediction: ✓ PASSED
Stats: ✓ PASSED

TOTAL: 7/7 tests passed 🎉
```

## Résumé

✅ **API REST fonctionnelle**
- 8 endpoints implémentés
- Validation automatique
- Documentation interactive
- Gestion d'erreurs robuste

✅ **Performance**
- ~29ms par prédiction (après warmup)
- Support du batch processing
- Monitoring intégré

✅ **Production-ready**
- Chargement depuis MLflow
- Hot reload
- CORS configuré
- Tests automatisés

**Step 5 : COMPLÉTÉ** ✅
