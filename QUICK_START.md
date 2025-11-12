# 🚀 Guide de Démarrage Rapide - Présentation MLOps

Ce guide vous permet de lancer rapidement le projet pour votre présentation de 10 minutes.

## ⚡ Démarrage en 3 commandes

```bash
# 1. Construire les images Docker
docker compose build

# 2. Initialiser Airflow (une seule fois)
docker compose up airflow-init

# 3. Lancer tous les services
docker compose up -d
```

## 📋 Vérification des Services

Attendez environ 30-60 secondes que tous les services démarrent, puis vérifiez :

```bash
# Voir l'état des conteneurs
docker compose ps

# Vérifier les logs si nécessaire
docker compose logs -f airflow-scheduler
docker compose logs -f api
```

## 🌐 URLs d'Accès

| Service | URL | Credentials |
|---------|-----|-------------|
| **Airflow UI** | http://localhost:8080 | admin / admin |
| **MLflow** | http://localhost:5500 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **FastAPI Docs** | http://localhost:8000/docs | - |
| **Streamlit** | http://localhost:8501 | - |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |

## 🎯 Scénario de Démonstration

### Étape 1 : Montrer l'architecture (2 min)
- Ouvrir le README.md et montrer les diagrammes Mermaid
- Expliquer le flux : Data → Training → Serving → Monitoring

### Étape 2 : Lancer le pipeline de training (3 min)
```bash
# Ouvrir Airflow UI : http://localhost:8080
# Login: admin / admin
# 1. Cliquer sur le DAG "dandelion_data_pipeline"
# 2. Cliquer sur le bouton "Play" (▶️) en haut à droite
# 3. Cliquer sur "Trigger DAG"
```

**Pendant que le pipeline tourne, montrer :**
- MinIO : http://localhost:9001 → Voir les buckets (dandelion-data, dandelion-models, mlflow-artifacts)
- MLflow : http://localhost:5500 → Voir l'expérience "dandelion-classifier" (peut être vide au début)

### Étape 3 : Monitoring du Training (2 min)
```bash
# Dans Airflow, cliquer sur le DAG run en cours
# Montrer la progression des tâches :
# ✅ create_folders → download_images → upload_raw → preprocess → upload_processed → train_model
```

**Pendant l'entraînement :**
- MLflow commence à logger les métriques en temps réel
- Rafraîchir MLflow pour voir le run apparaître

### Étape 4 : Test de l'API de Prédiction (2 min)

Une fois le training terminé (~5-7 min), tester l'API :

```bash
# Option 1 : Via l'interface Streamlit
# Ouvrir : http://localhost:8501
# 1. Uploader une image de pissenlit ou d'herbe
# 2. Cliquer sur "Prédire via l'API"
# 3. Voir le résultat : classe + confiance

# Option 2 : Via la doc FastAPI
# Ouvrir : http://localhost:8000/docs
# 1. Tester GET /health → Voir que le modèle est "ready"
# 2. Tester POST /predict → Uploader une image
```

### Étape 5 : Monitoring avec Grafana (1 min)
```bash
# Ouvrir Grafana : http://localhost:3000
# Login: admin / admin
# 1. Aller dans "Dashboards"
# 2. Ouvrir "Dandelion Classifier" → Métriques API (prédictions, latence)
# 3. Ouvrir "Airflow Overview" → Métriques du scheduler
```

## 🔥 Astuces pour la Présentation

### Si le training prend trop de temps
Le training complet prend ~5-7 minutes. Pour votre présentation :

**Option A : Lancer le pipeline AVANT la présentation**
```bash
# 30 minutes avant votre présentation
docker compose up -d
# Attendre que Airflow démarre (~2 min)
# Trigger le DAG manuellement
# Pendant le training, préparer vos slides
```

**Option B : Utiliser un modèle pré-entraîné**
Si vous avez déjà un modèle de votre démo précédente :
```bash
# Les volumes Docker persistent les données
# Si vous avez déjà run le pipeline une fois, le modèle est stocké
# L'API le chargera automatiquement au démarrage
```

### Si Airflow ne démarre pas
```bash
# Réinitialiser complètement Airflow
docker compose down -v  # ⚠️ Efface tout !
docker compose up airflow-init
docker compose up -d
```

### Télécharger une image de test
```bash
# Télécharger une image de pissenlit pour la démo
curl -o test_dandelion.jpg "https://raw.githubusercontent.com/btphan95/greenr-airflow/refs/heads/master/data/dandelion/00000001.jpg"

# Télécharger une image d'herbe
curl -o test_grass.jpg "https://raw.githubusercontent.com/btphan95/greenr-airflow/refs/heads/master/data/grass/00000001.jpg"
```

## 🐛 Dépannage Rapide

### Airflow scheduler/webserver en erreur
```bash
# Vérifier que l'init s'est bien passé
docker compose logs airflow-init | tail -20

# Si vous voyez "ERROR: You need to initialize the database"
docker compose stop airflow-scheduler airflow-webserver
docker compose up airflow-init
docker compose up -d airflow-scheduler airflow-webserver
```

### L'API dit "Model not available"
C'est normal au démarrage ! Le modèle n'existe pas encore.
- Lancez le pipeline dans Airflow
- Attendez que la tâche `train_model` soit ✅
- Redémarrez l'API : `docker compose restart api`

### MinIO : Buckets vides
```bash
# Vérifier que bootstrap s'est exécuté
docker compose logs bootstrap

# Si nécessaire, le relancer
docker compose up bootstrap
```

## 📊 Résultats Attendus

Après l'exécution complète du pipeline :

- **Données** : 400 images dans MinIO (200 pissenlits + 200 herbe)
- **Modèle** : `best_model.pt` dans MinIO bucket `dandelion-models`
- **MLflow** : 1 run avec métriques (accuracy ~0.85-0.90, loss, f1-score)
- **API** : Status "ready" avec 2 classes [dandelion, grass]
- **Temps total** : ~5-7 minutes sur CPU

## 🛑 Arrêter Tout

```bash
# Arrêter tous les services (garde les données)
docker compose stop

# Arrêter et supprimer tout (⚠️ efface les données)
docker compose down -v
```

## 📞 Aide Pendant la Présentation

Si quelque chose ne fonctionne pas pendant votre démo :

1. **Montrez les diagrammes** dans le README (toujours fonctionnel !)
2. **Expliquez l'architecture** avec les screenshots existants dans `docs/screenshots/`
3. **Montrez le code** : pipelines Airflow, modèle PyTorch, API FastAPI
4. **Backup plan** : Avoir des screenshots/vidéos de chaque étape

---

✨ **Bon courage pour votre présentation !** ✨
