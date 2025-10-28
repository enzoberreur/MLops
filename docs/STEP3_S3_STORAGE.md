# Étape 3 : Stockage du Modèle sur S3/Minio ✅

## Vue d'ensemble

Cette étape implémente le stockage et la gestion des modèles entraînés sur un système S3-compatible (Minio) avec versionnement automatique, métadonnées et vérification d'intégrité.

## Architecture

```
┌─────────────────┐
│  Trained Model  │
│  (best_model)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Model Storage Manager         │
│   - Versioning                  │
│   - Metadata tracking           │
│   - Checksum verification       │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   S3 Client (boto3)             │
│   - Upload/Download             │
│   - Bucket management           │
│   - Object operations           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Minio Server (Docker)         │
│   - S3-compatible storage       │
│   - Web console (port 9001)     │
│   - API endpoint (port 9000)    │
└─────────────────────────────────┘
```

## Composants Implémentés

### 1. Infrastructure Minio (Docker)
- **Fichier**: `docker-compose.yml`
- **Services**:
  - `minio`: Serveur de stockage S3-compatible
  - `minio-client`: Initialisation automatique des buckets
- **Buckets créés**:
  - `models`: Stockage des modèles entraînés
  - `plants-images`: Images du dataset
  - `data`: Autres données du projet
- **Accès Web**: http://localhost:9001 (minioadmin/minioadmin)

### 2. Client S3 (`src/storage/s3_client.py`)
Classe `S3Client` avec les méthodes suivantes :

```python
- create_bucket(bucket_name)           # Créer un bucket
- upload_file(file_path, bucket_name)  # Upload avec métadonnées
- download_file(bucket_name, object_name, local_path)
- list_objects(bucket_name, prefix)    # Lister les objets
- delete_object(bucket_name, object_name)
- get_object_metadata(bucket_name, object_name)
- bucket_exists(bucket_name)
- object_exists(bucket_name, object_name)
- get_presigned_url(bucket_name, object_name, expiration)
```

### 3. Gestionnaire de Modèles (`src/storage/model_storage.py`)
Classe `ModelStorage` pour la gestion avancée :

```python
- upload_model(model_path, model_name, version, metadata)
  → Upload avec versionnement automatique
  → Calcul de checksum (MD5)
  → Création de manifest JSON
  → Support fichiers additionnels (history, config)

- download_model(model_name, version, local_dir)
  → Téléchargement avec vérification
  → Validation du checksum
  → Récupération du manifest

- list_model_versions(model_name)
  → Liste toutes les versions disponibles

- get_latest_version(model_name)
  → Obtient la dernière version

- delete_model_version(model_name, version)
  → Supprime une version spécifique
```

### 4. Scripts Utilitaires

#### `upload_model.py`
Upload automatique du meilleur modèle entraîné avec métadonnées :
```bash
python3 upload_model.py
```

Métadonnées incluses :
- Architecture (resnet18)
- Nombre de classes (2)
- Meilleure époque (7)
- Précision train/validation (95.71% / 95.00%)
- Loss train/validation
- Optimiseur et hyperparamètres

#### `verify_s3.py`
Script de vérification complet :
```bash
python3 verify_s3.py
```

Tests effectués :
1. ✅ Liste des versions de modèles
2. ✅ Récupération de la dernière version
3. ✅ Téléchargement du modèle
4. ✅ Vérification des fichiers
5. ✅ Validation du manifest
6. ✅ Tests des méthodes S3
7. ✅ Liste des objets dans le bucket

## Résultats

### Modèle Uploadé

```
Model: plant_classifier
Version: 20251028_181858
Validation Accuracy: 95.00%
S3 URL: http://localhost:9000/models/plant_classifier/v20251028_181858/best_model.pth
```

### Fichiers Stockés

```
plant_classifier/v20251028_181858/
├── best_model.pth (131.82 MB)
├── training_history.json (1.2 KB)
└── manifest.json (1.0 KB)
```

### Structure du Manifest

```json
{
  "model_name": "plant_classifier",
  "version": "20251028_181858",
  "model_file": "plant_classifier/v20251028_181858/best_model.pth",
  "model_url": "http://localhost:9000/models/...",
  "checksum": "61be1039f61babf7311ee09b3d735920",
  "metadata": {
    "architecture": "resnet18",
    "num_classes": 2,
    "best_epoch": 7,
    "train_accuracy": 0.9571,
    "val_accuracy": 0.9500,
    "train_loss": 0.1324,
    "val_loss": 0.4722,
    "total_epochs": 10,
    "optimizer": "AdamW"
  },
  "created_at": "2025-10-28T18:19:00.455545"
}
```

## Configuration

### Variables d'Environnement (`.env`)

```bash
# S3/Minio Configuration
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1
S3_BUCKET_MODELS=models
S3_BUCKET_IMAGES=plants-images
S3_BUCKET_DATA=data
```

## Utilisation

### 1. Démarrer Minio
```bash
docker-compose up -d
```

### 2. Uploader un Modèle
```bash
python3 upload_model.py
```

### 3. Vérifier le Stockage
```bash
python3 verify_s3.py
```

### 4. Accéder à l'Interface Web
Ouvrir http://localhost:9001 dans le navigateur
- Username: `minioadmin`
- Password: `minioadmin`

### 5. Télécharger un Modèle (Python)
```python
from src.storage.model_storage import ModelStorage

storage = ModelStorage()
model_path = storage.download_model(
    model_name="plant_classifier",
    version="20251028_181858",
    local_dir="./models/downloaded"
)
```

## Fonctionnalités Clés

### ✅ Versionnement Automatique
- Format : `YYYYMMDD_HHMMSS`
- Permet de garder plusieurs versions
- Récupération facile de la dernière version

### ✅ Intégrité des Données
- Checksum MD5 pour chaque fichier
- Vérification lors du téléchargement
- Détection des corruptions

### ✅ Métadonnées Riches
- Métriques de performance
- Configuration du modèle
- Timestamps et traçabilité

### ✅ Gestion des Fichiers Additionnels
- Historique d'entraînement
- Configuration
- Logs
- Tout fichier associé au modèle

### ✅ API Complète
- Operations CRUD sur les objets
- Gestion des buckets
- URLs pré-signées pour partage temporaire
- Liste et recherche d'objets

## Tests de Validation

Tous les tests ont passé avec succès ✅ :

1. **Upload** : Modèle de 131.82 MB uploadé
2. **Download** : Téléchargement et vérification OK
3. **Checksum** : Intégrité validée
4. **Versioning** : Version v20251028_181858 créée
5. **Metadata** : Toutes les métadonnées présentes
6. **Buckets** : 3 buckets créés et accessibles

## Performance

- **Temps d'upload** : ~2 secondes pour 132 MB
- **Temps de download** : ~1 seconde pour 132 MB
- **Stockage** : Efficace avec compression native

## Sécurité

- Credentials configurables via variables d'environnement
- Support des AWS credentials standards
- Isolation réseau via Docker
- URLs pré-signées avec expiration

## Prochaines Étapes (Étape 4)

L'infrastructure S3 est maintenant en place et prête pour :
- **MLflow** : Tracking des expériences avec modèles stockés sur S3
- **API REST** : Servir les modèles depuis S3
- **CI/CD** : Déploiement automatique des modèles

## Commandes Utiles

### Docker
```bash
# Démarrer Minio
docker-compose up -d

# Voir les logs
docker-compose logs -f minio

# Arrêter Minio
docker-compose down

# Arrêter et supprimer les données
docker-compose down -v
```

### Minio CLI (dans le container)
```bash
# Se connecter au container
docker exec -it mlops-minio-client mc

# Lister les buckets
mc ls myminio

# Lister les objets
mc ls myminio/models --recursive
```

## Conclusion

✅ **Étape 3 terminée avec succès !**

Le modèle entraîné est maintenant :
- Stocké de manière sécurisée sur S3/Minio
- Versionné automatiquement
- Accessible via API
- Prêt pour l'intégration MLflow (Étape 4)

---

**Statut** : ✅ COMPLÉTÉ
**Validation Accuracy** : 95.00%
**Taille du Modèle** : 131.82 MB
**Version** : v20251028_181858
