# CI/CD avec GitHub Actions - Guide Rapide

Ce projet utilise GitHub Actions avec un **self-hosted runner** pour automatiser le build, les tests et le déploiement sur Kubernetes.

## 📋 Aperçu du Pipeline

Le pipeline CI/CD se déclenche automatiquement à chaque push sur `main` ou `develop` :

```
1. Build & Test
   ├── Checkout code
   ├── Install dependencies  
   ├── Lint code (flake8)
   ├── Build Docker image
   └── Test container

2. Deploy to Kubernetes (main only)
   ├── Check K8s cluster
   ├── Apply ConfigMap
   ├── Deploy application
   ├── Apply HPA
   └── Wait for rollout

3. Integration Tests
   ├── Wait for API ready
   ├── Test endpoints
   └── Verify deployment
```

## 🚀 Configuration du Runner (Déjà fait !)

Le runner self-hosted est déjà configuré et actif. Voici ce qui a été fait :

### 1. Installation
```bash
cd actions-runner
curl -o actions-runner-osx-arm64-2.329.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.329.0/actions-runner-osx-arm64-2.329.0.tar.gz
tar xzf ./actions-runner-osx-arm64-2.329.0.tar.gz
```

### 2. Configuration
```bash
./config.sh --url https://github.com/enzoberreur/MLops --token <TOKEN>
```

### 3. Démarrage
```bash
./run.sh &
```

### 4. Vérification
```bash
ps aux | grep "Runner.Listener"
```

## 🔄 Utilisation du Pipeline

### Déclencher le Pipeline

**1. Push automatique :**
```bash
git add .
git commit -m "feat: new feature"
git push origin main
```

**2. Déclenchement manuel :**
- Aller sur GitHub → Actions
- Sélectionner "CI/CD Pipeline"  
- Cliquer sur "Run workflow"

### Voir les Logs

1. Aller sur https://github.com/enzoberreur/MLops
2. Cliquer sur l'onglet **Actions**
3. Sélectionner le workflow en cours
4. Cliquer sur un job pour voir les logs

## 📊 Statut du Runner

### Vérifier si le runner est actif

```bash
# Vérifier le processus
ps aux | grep "Runner.Listener"

# Voir les logs
cd actions-runner
tail -f _diag/Runner_*.log
```

### Redémarrer le runner

```bash
cd actions-runner
pkill -f "Runner.Listener"
./run.sh &
```

### Installer comme service (recommandé pour production)

```bash
cd actions-runner
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

## 🐳 Build Manuel (sans CI/CD)

Si vous voulez tester localement sans passer par le CI/CD :

```bash
# Build l'image
docker build -t plant-classification-api:latest .

# Test local
docker run -d --name test-api -p 8080:8000 plant-classification-api:latest
curl http://localhost:8080/health
docker stop test-api && docker rm test-api
```

## ☸️ Déploiement Manuel sur K8s

```bash
# Avec le script automatique
./deploy_k8s.sh

# Ou manuellement
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml

# Vérifier
kubectl get pods -l app=plant-api
kubectl get svc plant-api-service
```

## 🔍 Monitoring du Déploiement

### Voir les pods

```bash
kubectl get pods -l app=plant-api -w
```

### Voir les logs

```bash
kubectl logs -f -l app=plant-api
```

### Voir le status du HPA

```bash
kubectl get hpa plant-api-hpa -w
```

### Tester l'API déployée

```bash
# Health check
curl http://localhost:30080/health

# API docs
open http://localhost:30080/docs
```

## 🛠️ Troubleshooting

### Le workflow ne se déclenche pas

1. **Vérifier que le runner est actif :**
   ```bash
   ps aux | grep "Runner.Listener"
   ```

2. **Vérifier les logs du runner :**
   ```bash
   cd actions-runner
   tail -f _diag/Runner_*.log
   ```

3. **Redémarrer le runner :**
   ```bash
   pkill -f "Runner.Listener"
   ./run.sh &
   ```

### Le build Docker échoue

1. **Vérifier que le modèle existe :**
   ```bash
   ls -lh models/best_model.pth
   ```

2. **Copier depuis checkpoints si nécessaire :**
   ```bash
   cp models/checkpoints/best_model.pth models/best_model.pth
   ```

### Le déploiement K8s échoue

1. **Vérifier que K8s est actif :**
   ```bash
   kubectl cluster-info
   ```

2. **Activer Kubernetes dans Docker Desktop :**
   - Docker Desktop → Settings → Kubernetes → Enable

3. **Voir les événements :**
   ```bash
   kubectl get events --sort-by='.lastTimestamp'
   ```

### Les pods crashent

```bash
# Voir les logs
kubectl logs -l app=plant-api

# Voir les détails
kubectl describe pod <pod-name>

# Supprimer et redéployer
kubectl delete -f k8s/
kubectl apply -f k8s/
```

## 🔐 Sécurité

### Secrets GitHub (si nécessaire)

Pour ajouter des secrets (Docker Hub, cloud credentials, etc.) :

1. GitHub → Settings → Secrets and variables → Actions
2. Cliquer sur "New repository secret"
3. Ajouter le nom et la valeur

Utilisation dans le workflow :
```yaml
env:
  DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
```

### Token du Runner

⚠️ **Ne jamais commit le token du runner !**

Le token est généré lors de la configuration et n'est valable qu'une fois. Si vous devez reconfigurer :

1. GitHub → Settings → Actions → Runners
2. Supprimer l'ancien runner
3. Créer un nouveau runner
4. Utiliser le nouveau token

## 📈 Optimisations

### Cache Docker Layers

Le workflow utilise déjà le cache Docker local pour accélérer les builds.

### Nettoyage Automatique

Les vieilles images Docker sont automatiquement supprimées après 72h :
```yaml
- name: Cleanup old images
  run: docker image prune -f --filter "until=72h"
```

## 📚 Commandes Utiles

```bash
# Runner
cd actions-runner
./run.sh                    # Démarrer
pkill -f "Runner.Listener"  # Arrêter
tail -f _diag/Runner_*.log  # Logs

# Docker
docker images | grep plant  # Voir les images
docker ps                   # Conteneurs actifs
docker system prune -a      # Nettoyer tout

# Kubernetes
kubectl get all             # Toutes les ressources
kubectl delete -f k8s/      # Supprimer le déploiement
kubectl rollout restart deployment/plant-api  # Restart

# Git
git status                  # Status
git log --oneline -5        # Derniers commits
git push origin main        # Déclencher le CI/CD
```

## ✅ Checklist de Déploiement

Avant de push :

- [ ] Le modèle `models/best_model.pth` existe
- [ ] Les tests locaux passent
- [ ] Le runner est actif
- [ ] Kubernetes est démarré
- [ ] Les manifests K8s sont à jour
- [ ] Le `.gitignore` exclut les données sensibles

## 🎯 Prochaines Étapes

- [ ] Ajouter des tests unitaires automatisés
- [ ] Configurer des environnements (dev/staging/prod)
- [ ] Ajouter des notifications (Slack, email)
- [ ] Implémenter le versioning sémantique
- [ ] Ajouter des gates de qualité (coverage, security scan)

---

**Status du Runner** : ✅ Actif et configuré
**Cluster K8s** : Docker Desktop (local)
**URL API** : http://localhost:30080
