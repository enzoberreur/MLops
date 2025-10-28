# GitHub Actions Self-Hosted Runner Setup

Ce document explique comment configurer un self-hosted runner pour GitHub Actions afin de déployer automatiquement sur un cluster Kubernetes local.

## Pourquoi un Self-Hosted Runner ?

Un self-hosted runner est nécessaire car :
1. **Accès au cluster Kubernetes local** : Les runners GitHub hébergés ne peuvent pas accéder à votre cluster K8s local
2. **Accès aux images Docker** : Les images sont construites localement
3. **Performance** : Build plus rapide (pas de téléchargement/upload d'images)
4. **Coût** : Gratuit pour les projets privés

## Prérequis

- **Docker Desktop** avec Kubernetes activé
- **kubectl** installé et configuré
- **Compte GitHub** avec accès au repository
- **macOS/Linux/Windows** avec au moins 4GB RAM disponible

## Installation du Runner

### 1. Créer le Runner dans GitHub

1. Aller dans votre repository GitHub
2. Cliquer sur **Settings** → **Actions** → **Runners**
3. Cliquer sur **New self-hosted runner**
4. Sélectionner votre OS (macOS, Linux, Windows)
5. Suivre les instructions affichées

### 2. Télécharger et Configurer

**macOS / Linux:**
```bash
# Créer un dossier pour le runner
mkdir actions-runner && cd actions-runner

# Télécharger le runner (remplacer par l'URL fournie par GitHub)
curl -o actions-runner-osx-arm64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-osx-arm64-2.311.0.tar.gz

# Extraire
tar xzf ./actions-runner-osx-arm64-2.311.0.tar.gz

# Configurer le runner
./config.sh --url https://github.com/<YOUR_USERNAME>/<YOUR_REPO> --token <YOUR_TOKEN>
```

**Windows:**
```powershell
# Créer un dossier
mkdir actions-runner; cd actions-runner

# Télécharger
Invoke-WebRequest -Uri https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-win-x64-2.311.0.zip -OutFile actions-runner-win-x64-2.311.0.zip

# Extraire
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD/actions-runner-win-x64-2.311.0.zip", "$PWD")

# Configurer
./config.cmd --url https://github.com/<YOUR_USERNAME>/<YOUR_REPO> --token <YOUR_TOKEN>
```

### 3. Configurer le Runner

Pendant la configuration, répondre aux questions :

```bash
Enter the name of the runner group: [Press Enter for Default]
Enter the name of runner: [Press Enter for default or type: k8s-local-runner]
Enter any additional labels: [Press Enter or type: kubernetes,docker]
Enter name of work folder: [Press Enter for default: _work]
```

### 4. Démarrer le Runner

**Mode Interactif (pour tester) :**
```bash
./run.sh  # macOS/Linux
./run.cmd # Windows
```

**Comme Service (production) :**

**macOS:**
```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

**Linux (systemd):**
```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo systemctl status actions.runner.*
```

**Windows (PowerShell en admin):**
```powershell
./svc.cmd install
./svc.cmd start
./svc.cmd status
```

## Configuration Kubernetes

### 1. Vérifier l'Accès au Cluster

```bash
kubectl cluster-info
kubectl get nodes
kubectl get namespaces
```

### 2. Créer un Namespace (optionnel)

```bash
kubectl create namespace plant-classification
kubectl config set-context --current --namespace=plant-classification
```

### 3. Configurer les Permissions (si nécessaire)

Si vous utilisez RBAC, créer un ServiceAccount :

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: github-actions
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: github-actions-admin
subjects:
- kind: ServiceAccount
  name: github-actions
  namespace: default
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
```

Appliquer :
```bash
kubectl apply -f k8s/rbac.yaml
```

## Configuration Docker Desktop Kubernetes

### 1. Activer Kubernetes

1. Ouvrir **Docker Desktop**
2. Aller dans **Settings** → **Kubernetes**
3. Cocher **Enable Kubernetes**
4. Cliquer sur **Apply & Restart**
5. Attendre que le status soit "Kubernetes is running"

### 2. Vérifier la Configuration

```bash
kubectl config get-contexts
kubectl config use-context docker-desktop
```

### 3. Configurer les Ressources

Dans Docker Desktop → **Settings** → **Resources** :
- **CPUs** : Minimum 2, recommandé 4
- **Memory** : Minimum 4GB, recommandé 8GB
- **Disk** : Minimum 20GB

## Variables d'Environnement

Le runner doit avoir accès aux variables suivantes :

```bash
# Docker
DOCKER_HOST=unix:///var/run/docker.sock

# Kubernetes
KUBECONFIG=/Users/<username>/.kube/config

# Python (optionnel)
PYTHONPATH=/path/to/project
```

Ajouter dans `~/.bashrc` ou `~/.zshrc` :

```bash
export PATH=$PATH:/usr/local/bin
export KUBECONFIG=$HOME/.kube/config
```

## Test du Pipeline

### 1. Tester Localement

```bash
# Build Docker image
docker build -t plant-classification-api:latest .

# Test container
docker run -d --name test-api -p 8080:8000 plant-classification-api:latest
curl http://localhost:8080/health
docker stop test-api && docker rm test-api

# Deploy to K8s
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml

# Verify
kubectl get pods
kubectl get svc
```

### 2. Tester le Workflow GitHub Actions

1. Faire un commit et push :
```bash
git add .
git commit -m "test: CI/CD pipeline"
git push origin main
```

2. Vérifier dans GitHub :
   - Aller dans **Actions**
   - Voir le workflow en cours
   - Vérifier les logs de chaque step

## Troubleshooting

### Runner ne démarre pas

```bash
# Vérifier les logs
cat _diag/Runner_*.log

# Redémarrer le service
sudo ./svc.sh stop
sudo ./svc.sh start
```

### Erreur d'accès Docker

```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
newgrp docker

# Ou donner les permissions
sudo chmod 666 /var/run/docker.sock
```

### Erreur kubectl

```bash
# Vérifier la config
kubectl config view
kubectl cluster-info

# Réinitialiser le context
kubectl config use-context docker-desktop
```

### Image Docker non trouvée

```bash
# Vérifier que l'image existe
docker images | grep plant-classification

# Reconstruire si nécessaire
docker build -t plant-classification-api:latest .
```

### Pods en CrashLoopBackOff

```bash
# Vérifier les logs
kubectl logs -l app=plant-api

# Vérifier les événements
kubectl describe pod <pod-name>

# Vérifier les ressources
kubectl top nodes
kubectl top pods
```

## Sécurité

### Bonnes Pratiques

1. **Ne jamais commit** le token du runner
2. **Utiliser des secrets** GitHub pour les credentials
3. **Limiter les permissions** du ServiceAccount K8s
4. **Scanner les images** Docker pour les vulnérabilités
5. **Mettre à jour** régulièrement le runner

### Secrets GitHub

Ajouter dans GitHub → **Settings** → **Secrets and variables** → **Actions** :

- `DOCKER_USERNAME` : Votre username Docker Hub (optionnel)
- `DOCKER_PASSWORD` : Votre password Docker Hub (optionnel)
- `KUBECONFIG` : Contenu de ~/.kube/config (si besoin)

## Maintenance

### Mettre à Jour le Runner

```bash
cd actions-runner
sudo ./svc.sh stop
./config.sh remove --token <NEW_TOKEN>

# Télécharger la nouvelle version
curl -o actions-runner-osx-arm64-latest.tar.gz -L \
  https://github.com/actions/runner/releases/download/vX.X.X/actions-runner-osx-arm64-X.X.X.tar.gz

tar xzf ./actions-runner-osx-arm64-latest.tar.gz
./config.sh --url https://github.com/<USER>/<REPO> --token <TOKEN>
sudo ./svc.sh install
sudo ./svc.sh start
```

### Logs et Monitoring

```bash
# Logs du runner
tail -f _diag/Runner_*.log

# Logs Kubernetes
kubectl logs -f -l app=plant-api

# Métriques
kubectl top nodes
kubectl top pods -n default
```

## Ressources

- [GitHub Actions Documentation](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Kubernetes Documentation](https://kubernetes.io/docs/home/)
- [Docker Desktop Kubernetes](https://docs.docker.com/desktop/kubernetes/)

## Commandes Utiles

```bash
# Runner
./run.sh                    # Démarrer en mode interactif
sudo ./svc.sh status        # Status du service
sudo ./svc.sh stop          # Arrêter
sudo ./svc.sh start         # Démarrer

# Kubernetes
kubectl get all -n default  # Voir toutes les ressources
kubectl logs -f <pod>       # Suivre les logs
kubectl describe pod <pod>  # Détails d'un pod
kubectl delete pod <pod>    # Supprimer et recréer un pod
kubectl rollout restart deployment/plant-api  # Redémarrer le déploiement

# Docker
docker ps                   # Conteneurs en cours
docker images               # Images disponibles
docker logs <container>     # Logs d'un conteneur
docker system prune -a      # Nettoyer (attention !)
```
