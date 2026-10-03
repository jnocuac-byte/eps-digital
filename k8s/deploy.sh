#!/usr/bin/env bash
# Despliegue idempotente de EPS Digital en Minikube (ejecutar dentro del Codespace).
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
NS=eps-digital

echo "==> [1/7] Minikube"
if ! minikube status >/dev/null 2>&1; then
  minikube start --driver=docker --cpus=3 --memory=8192
fi
minikube status

echo "==> [2/7] Addon ingress"
minikube addons enable ingress
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=300s

echo "==> [3/7] Construyendo imagenes dentro de Minikube"
for svc in auth-service user-service appointments-service catalog-service ai-nlp-service notifications-service; do
  echo "--- $svc"
  minikube image build -t "eps-digital/$svc:latest" "services/$svc"
done
echo "--- frontend"
# -f se resuelve relativo al contexto: hay que construir desde frontend/
(cd frontend && minikube image build -t eps-digital/frontend:latest -f Dockerfile.k8s .)

echo "==> [4/7] Namespace y secreto"
kubectl apply -f k8s/00-namespace.yaml

env_val() { # lee KEY de .env (si existe)
  [ -f .env ] && grep -E "^$1=" .env | tail -n1 | cut -d= -f2- | tr -d '\r"' || true
}
val_or() { # val_or KEY DEFAULT
  local v; v="$(env_val "$1")"; echo "${v:-$2}"
}

if [ -f .env ]; then
  echo "Creando/actualizando eps-secrets desde .env"
  JWT="$(val_or JWT_SECRET_KEY "$(openssl rand -hex 32)")"
  PGPASS="$(val_or POSTGRES_PASSWORD "$(openssl rand -hex 16)")"
elif kubectl -n $NS get secret eps-secrets >/dev/null 2>&1; then
  echo "eps-secrets ya existe y no hay .env: se conserva (la contrasena de Postgres no debe cambiar)"
  JWT=""
else
  echo "Sin .env: generando JWT_SECRET_KEY y POSTGRES_PASSWORD aleatorios, API keys con placeholder"
  JWT="$(openssl rand -hex 32)"
  PGPASS="$(openssl rand -hex 16)"
fi

if [ -n "$JWT" ]; then
  kubectl -n $NS create secret generic eps-secrets \
    --from-literal=JWT_SECRET_KEY="$JWT" \
    --from-literal=POSTGRES_PASSWORD="$PGPASS" \
    --from-literal=GROQ_API_KEY="$(val_or GROQ_API_KEY placeholder)" \
    --from-literal=CEREBRAS_API_KEY="$(val_or CEREBRAS_API_KEY placeholder)" \
    --from-literal=MISTRAL_API_KEY="$(val_or MISTRAL_API_KEY placeholder)" \
    --from-literal=GEMINI_API_KEY_1="$(val_or GEMINI_API_KEY_1 placeholder)" \
    --from-literal=GEMINI_API_KEY_2="$(val_or GEMINI_API_KEY_2 placeholder)" \
    --from-literal=GEMINI_API_KEY_3="$(val_or GEMINI_API_KEY_3 placeholder)" \
    --from-literal=SENDGRID_API_KEY="$(val_or SENDGRID_API_KEY placeholder)" \
    --from-literal=SENDGRID_FROM_EMAIL="$(val_or SENDGRID_FROM_EMAIL no-reply@example.com)" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

echo "==> [5/7] Aplicando manifiestos"
kubectl apply -k k8s/
# Reinicia los deployments para tomar imagenes recien construidas (tag :latest)
kubectl -n $NS rollout restart deployment \
  auth-service user-service appointments-service catalog-service ai-nlp-service notifications-service frontend

echo "==> [6/7] Esperando pods Ready"
kubectl -n $NS rollout status statefulset/postgres --timeout=300s
kubectl -n $NS wait --for=condition=Ready pod --all --timeout=600s
kubectl -n $NS get pods

echo "==> [7/7] Port-forward del Ingress en 8080"
pkill -f "port-forward -n ingress-nginx" 2>/dev/null || true
sleep 1
nohup kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80 --address 0.0.0.0 \
  >/tmp/port-forward.log 2>&1 &
sleep 3
curl -s -o /dev/null -w "Ingress local: HTTP %{http_code}\n" http://localhost:8080/ || true
echo "Listo. Puerto 8080 publicado."
