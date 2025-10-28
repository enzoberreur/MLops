# Step 7: Kubernetes Deployment & CI/CD 🚀

## Overview

Déploiement de l'API Plant Classification sur un cluster Kubernetes local avec automatisation CI/CD via GitHub Actions et un self-hosted runner.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Repository                      │
│  - Push to main branch                                  │
│  - Workflow: build → test → deploy                      │
└──────────────────┬──────────────────────────────────────┘
                   │ Trigger
┌──────────────────▼──────────────────────────────────────┐
│            GitHub Actions Runner                         │
│            (Self-Hosted on macOS)                        │
│                                                           │
│  1. Build Docker Image                                   │
│  2. Run Tests                                            │
│  3. Deploy to K8s                                        │
└──────────────────┬──────────────────────────────────────┘
                   │ kubectl apply
┌──────────────────▼──────────────────────────────────────┐
│         Kubernetes Cluster (Docker Desktop)              │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Pod 1     │  │   Pod 2     │  │   Pod N     │    │
│  │  plant-api  │  │  plant-api  │  │  plant-api  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│         ▲                ▲                ▲              │
│         └────────────────┴────────────────┘              │
│                          │                                │
│              ┌───────────▼──────────┐                    │
│              │  LoadBalancer Service │                    │
│              │    (NodePort 30080)   │                    │
│              └───────────┬──────────┘                    │
└──────────────────────────┼──────────────────────────────┘
                           │
                    http://localhost:30080
```

## Composants

### 1. Docker Image
- **Base** : `python:3.9-slim`
- **Size** : ~2.2 GB
- **Layers** : Multi-stage optimized
- **User** : Non-root (apiuser:1000)
- **Health Check** : Intégré

### 2. Kubernetes Manifests

#### ConfigMap (`k8s/configmap.yaml`)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: plant-api-config
data:
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  LOG_LEVEL: "info"
  MLFLOW_TRACKING_URI: "http://mlflow-service:5001"
```

#### Deployment (`k8s/deployment.yaml`)
- **Replicas** : 2 (minimum)
- **Strategy** : RollingUpdate
- **Resources** :
  - Requests : 512Mi RAM, 250m CPU
  - Limits : 1Gi RAM, 500m CPU
- **Probes** :
  - Liveness : `/health` every 30s
  - Readiness : `/health` every 10s

#### Service
- **Type** : LoadBalancer
- **Port** : 80 → 8000
- **NodePort** : 30080
- **Selector** : `app=plant-api`

#### HorizontalPodAutoscaler (`k8s/hpa.yaml`)
- **Min Replicas** : 2
- **Max Replicas** : 5
- **Target CPU** : 70%
- **Target Memory** : 80%
- **Scale Up** : Max 2 pods per 30s
- **Scale Down** : 50% per 60s (stable 5min)

### 3. CI/CD Pipeline

**Workflow** : `.github/workflows/deploy.yml`

#### Job 1: Build and Test
```yaml
- Checkout code
- Setup Python 3.9
- Install dependencies
- Lint code (flake8)
- Run unit tests
- Build Docker image
- Test Docker container
- Save image as artifact
```

#### Job 2: Deploy to K8s
```yaml
- Download Docker image
- Load image
- Configure kubectl
- Apply ConfigMap
- Deploy/Update deployment
- Apply HPA
- Wait for rollout
- Verify deployment
- Test deployed API
- Cleanup old images
```

#### Job 3: Integration Tests
```yaml
- Run integration tests
- Generate test report
```

**Triggers** :
- `push` to `main` or `develop`
- `pull_request` to `main` or `develop`
- Manual `workflow_dispatch`

## Déploiement

### Prérequis

1. **Docker Desktop** avec Kubernetes activé
2. **kubectl** installé et configuré
3. **GitHub** repository avec Actions activé
4. **Self-hosted runner** configuré

### Installation Manuelle

#### 1. Construire l'Image Docker

```bash
# S'assurer que le modèle existe
cp models/checkpoints/best_model.pth models/best_model.pth

# Build
docker build -t plant-classification-api:latest .

# Vérifier
docker images | grep plant-classification
```

#### 2. Tester l'Image Localement

```bash
# Lancer le conteneur
docker run -d --name test-api -p 8080:8000 plant-classification-api:latest

# Tester
curl http://localhost:8080/health

# Arrêter
docker stop test-api && docker rm test-api
```

#### 3. Déployer sur Kubernetes

```bash
# Vérifier l'accès au cluster
kubectl cluster-info
kubectl get nodes

# Appliquer les manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml

# Vérifier le déploiement
kubectl get pods
kubectl get svc
kubectl get hpa
```

#### 4. Accéder à l'API

```bash
# Via LoadBalancer
kubectl get svc plant-api-service

# Via NodePort (Docker Desktop)
open http://localhost:30080/docs
```

### Déploiement via CI/CD

#### 1. Configurer le Self-Hosted Runner

Voir le guide détaillé : [.github/RUNNER_SETUP.md](.github/RUNNER_SETUP.md)

**Résumé** :
```bash
# Télécharger et configurer
mkdir actions-runner && cd actions-runner
curl -o actions-runner.tar.gz -L <URL_FROM_GITHUB>
tar xzf actions-runner.tar.gz
./config.sh --url https://github.com/<USER>/<REPO> --token <TOKEN>

# Démarrer comme service
sudo ./svc.sh install
sudo ./svc.sh start
```

#### 2. Push pour Déclench

er le Pipeline

```bash
git add .
git commit -m "feat: deploy to kubernetes"
git push origin main
```

#### 3. Monitorer le Workflow

1. Aller sur GitHub → **Actions**
2. Voir le workflow "Build, Test and Deploy to K8s"
3. Suivre les logs de chaque job

## Commandes Utiles

### Docker

```bash
# Build
docker build -t plant-classification-api:latest .

# Run
docker run -d -p 8080:8000 --name plant-api plant-classification-api:latest

# Logs
docker logs -f plant-api

# Stop & Remove
docker stop plant-api && docker rm plant-api

# Cleanup
docker system prune -a
```

### Kubernetes

```bash
# Déploiement
kubectl apply -f k8s/

# Status
kubectl get all -n default
kubectl get pods -l app=plant-api
kubectl get svc plant-api-service
kubectl get hpa plant-api-hpa

# Logs
kubectl logs -f -l app=plant-api
kubectl logs -f <pod-name>

# Describe
kubectl describe pod <pod-name>
kubectl describe svc plant-api-service
kubectl describe hpa plant-api-hpa

# Scaling manuel
kubectl scale deployment plant-api --replicas=3

# Rolling restart
kubectl rollout restart deployment/plant-api
kubectl rollout status deployment/plant-api

# Rollback
kubectl rollout undo deployment/plant-api

# Delete
kubectl delete -f k8s/
kubectl delete deployment plant-api
kubectl delete svc plant-api-service
kubectl delete hpa plant-api-hpa
```

### Test de Charge (pour HPA)

```bash
# Installer hey (load testing tool)
# macOS: brew install hey
# Linux: go install github.com/rakyll/hey@latest

# Générer du trafic
hey -z 2m -c 50 -m GET http://localhost:30080/health

# Observer l'autoscaling
watch kubectl get hpa plant-api-hpa
watch kubectl get pods -l app=plant-api
```

## Monitoring

### Pods

```bash
# Voir les pods
kubectl get pods -w

# Logs en temps réel
kubectl logs -f -l app=plant-api --tail=100

# Events
kubectl get events --sort-by='.lastTimestamp'
```

### Métriques

```bash
# Installer metrics-server (si pas déjà fait)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Voir les métriques
kubectl top nodes
kubectl top pods -n default
kubectl top pods -l app=plant-api
```

### HPA Status

```bash
kubectl get hpa plant-api-hpa -w

# Output example:
# NAME            REFERENCE              TARGETS   MINPODS   MAXPODS   REPLICAS
# plant-api-hpa   Deployment/plant-api   45%/70%   2         5         2
```

## Troubleshooting

### Image Pull Errors

```bash
# Vérifier que l'image existe localement
docker images | grep plant-classification

# Si nécessaire, rebuild
docker build -t plant-classification-api:latest .

# Utiliser imagePullPolicy: IfNotPresent dans le deployment
```

### Pods en CrashLoopBackOff

```bash
# Voir les logs
kubectl logs <pod-name>

# Voir les events
kubectl describe pod <pod-name>

# Causes communes:
# - Modèle manquant
# - Dépendances manquantes
# - Port déjà utilisé
# - Ressources insuffisantes
```

### Service non accessible

```bash
# Vérifier le service
kubectl get svc plant-api-service

# Vérifier les endpoints
kubectl get endpoints plant-api-service

# Tester depuis un pod
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://plant-api-service/health
```

### HPA ne scale pas

```bash
# Vérifier metrics-server
kubectl get deployment metrics-server -n kube-system

# Vérifier les métriques
kubectl top pods

# Générer de la charge
hey -z 2m -c 100 http://localhost:30080/predict
```

## Tests

### Test Local (Sans K8s)

```bash
# Build et run Docker
docker build -t plant-classification-api:latest .
docker run -d -p 8080:8000 plant-classification-api:latest

# Test
curl http://localhost:8080/health
curl http://localhost:8080/docs
```

### Test sur Kubernetes

```bash
# Deploy
kubectl apply -f k8s/

# Wait for ready
kubectl wait --for=condition=ready pod -l app=plant-api --timeout=120s

# Test via NodePort
curl http://localhost:30080/health

# Test depuis un pod
kubectl run -it --rm curl --image=curlimages/curl --restart=Never -- \
  curl http://plant-api-service/health
```

### Test de Performance

```bash
# Single request
time curl -X POST http://localhost:30080/predict \
  -F "file=@test_image.jpg"

# Load test
hey -n 1000 -c 50 http://localhost:30080/health

# Watch autoscaling
watch kubectl get pods -l app=plant-api
```

## Sécurité

### Best Practices Appliquées

- ✅ **Non-root user** dans le conteneur
- ✅ **Image optimisée** (multi-stage build)
- ✅ **Health checks** (liveness + readiness)
- ✅ **Resource limits** (CPU + Memory)
- ✅ **Rolling updates** (zero-downtime)
- ✅ **HPA** (auto-scaling)

### À Améliorer

- [ ] Network Policies
- [ ] Pod Security Policies
- [ ] Secrets management (Vault)
- [ ] Image scanning (Trivy)
- [ ] TLS/HTTPS
- [ ] Authentication

## Performance

### Ressources par Pod

- **Requests** : 512Mi RAM, 0.25 CPU
- **Limits** : 1Gi RAM, 0.5 CPU
- **Inference** : ~30-50ms par image

### Scalabilité

- **Min** : 2 pods (High Availability)
- **Max** : 5 pods (Cost control)
- **Trigger** : CPU > 70% ou Memory > 80%

### Throughput Estimé

- **Par pod** : ~20-30 req/s
- **2 pods** : ~40-60 req/s
- **5 pods** : ~100-150 req/s

## Next Steps

### Step 8 : CI/CD Avancé
- [ ] Multi-environment (dev/staging/prod)
- [ ] Blue-Green deployments
- [ ] Canary releases
- [ ] Automated rollbacks

### Step 9 : Monitoring Avancé
- [ ] Prometheus + Grafana
- [ ] Jaeger (tracing)
- [ ] ELK Stack (logging)
- [ ] Alerting

### Step 10 : Production Hardening
- [ ] TLS certificates
- [ ] Ingress controller
- [ ] Rate limiting
- [ ] WAF

## Résumé

✅ **Dockerisation complète**
- Dockerfile optimisé
- Image testée et fonctionnelle
- Health checks intégrés

✅ **Kubernetes deployment**
- 2 replicas minimum
- Auto-scaling (HPA)
- LoadBalancer service
- Rolling updates

✅ **CI/CD pipeline**
- GitHub Actions workflow
- Self-hosted runner setup
- Automated testing
- Automated deployment

✅ **Production-ready**
- High availability
- Auto-scaling
- Health monitoring
- Zero-downtime deployments

**Step 7 : COMPLÉTÉ** ✅

## Ressources

- **Docker Image** : `plant-classification-api:latest`
- **K8s Namespace** : `default`
- **Service URL** : http://localhost:30080
- **Docs** : http://localhost:30080/docs
- **GitHub Workflow** : `.github/workflows/deploy.yml`
- **Runner Setup** : `.github/RUNNER_SETUP.md`
