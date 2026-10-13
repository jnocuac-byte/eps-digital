#!/usr/bin/env bash
# Genera k8s/evidencias-h16.txt con la evidencia de los criterios H-16.
# Ejecutar dentro del Codespace, con el despliegue ya corriendo (deploy.sh).
set -uo pipefail

cd "$(dirname "$0")/.."
NS=eps-digital
OUT=k8s/evidencias-h16.txt
BASE=http://localhost:8080

seccion() { printf '\n\n==================== %s ====================\n' "$1" | tee -a "$OUT"; }
run() { printf '\n$ %s\n' "$*" | tee -a "$OUT"; "$@" 2>&1 | tee -a "$OUT"; }

: > "$OUT"
echo "Evidencias H-16 - Orquestacion en Kubernetes (Minikube)" | tee -a "$OUT"
echo "Fecha: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee -a "$OUT"

seccion "1. Clúster (criterio 1: plataforma Minikube)"
run kubectl get nodes -o wide
run minikube version
run kubectl get pods -n ingress-nginx

seccion "2. Recursos del namespace (criterios 2, 3 y 5)"
run kubectl get all,ingress,pv,pvc -n $NS
run kubectl get pv

seccion "3. Probes de liveness/readiness (criterio 4)"
for dep in auth-service user-service appointments-service catalog-service ai-nlp-service notifications-service frontend; do
  printf '\n$ kubectl describe deployment/%s (probes)\n' "$dep" | tee -a "$OUT"
  kubectl describe deployment/$dep -n $NS | grep -E "Liveness|Readiness" | tee -a "$OUT"
done
POD=$(kubectl get pod -n $NS -l app=auth-service -o jsonpath='{.items[0].metadata.name}')
run kubectl describe pod "$POD" -n $NS
for r in postgres redis rabbitmq; do
  printf '\n$ probes de %s\n' "$r" | tee -a "$OUT"
  kubectl get pod -n $NS -l app=$r -o jsonpath='{.items[0].spec.containers[0].livenessProbe}{"\n"}{.items[0].spec.containers[0].readinessProbe}{"\n"}' | tee -a "$OUT"
done

seccion "4. URL unica via Ingress (criterio 3)"
run kubectl get ingress -n $NS
printf '\n$ curl %s/ (frontend)\n' "$BASE" | tee -a "$OUT"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$BASE/" | tee -a "$OUT"
for s in auth user citas catalogo ai notifications; do
  for p in health ready; do
    printf '\n$ curl %s/api/%s/%s\n' "$BASE" "$s" "$p" | tee -a "$OUT"
    curl -s -w "\nHTTP %{http_code}\n" "$BASE/api/$s/$p" | tee -a "$OUT"
  done
done

seccion "5. Persistencia de datos (criterio 5): Postgres y Redis"
PG="kubectl exec -n $NS postgres-0 -- psql -U eps_user -d postgres -t -A -c"
STAMP="prueba-$(date +%s)"

echo "--- Antes: escribimos un dato en Postgres y una clave en Redis (valor=$STAMP)" | tee -a "$OUT"
$PG "CREATE TABLE IF NOT EXISTS h16_persistencia (id serial primary key, valor text, creado timestamptz default now())" | tee -a "$OUT"
$PG "INSERT INTO h16_persistencia (valor) VALUES ('$STAMP')" | tee -a "$OUT"
kubectl exec -n $NS deploy/redis -- redis-cli set h16:prueba "$STAMP" | tee -a "$OUT"
kubectl exec -n $NS deploy/redis -- redis-cli bgrewriteaof >/dev/null 2>&1
sleep 3   # appendfsync everysec: dar tiempo a que el AOF llegue a disco
echo "Postgres antes:" | tee -a "$OUT"; $PG "SELECT id, valor FROM h16_persistencia ORDER BY id" | tee -a "$OUT"
echo "Redis antes:" | tee -a "$OUT"; kubectl exec -n $NS deploy/redis -- redis-cli get h16:prueba | tee -a "$OUT"

echo "--- Borrando los pods de Postgres y Redis" | tee -a "$OUT"
run kubectl delete pod postgres-0 -n $NS
REDIS_POD=$(kubectl get pod -n $NS -l app=redis -o jsonpath='{.items[0].metadata.name}')
run kubectl delete pod "$REDIS_POD" -n $NS
sleep 5
kubectl rollout status statefulset/postgres -n $NS --timeout=300s | tee -a "$OUT"
kubectl rollout status deployment/redis -n $NS --timeout=300s | tee -a "$OUT"
kubectl wait --for=condition=Ready pod -l app=postgres -n $NS --timeout=300s | tee -a "$OUT"
kubectl wait --for=condition=Ready pod -l app=redis -n $NS --timeout=300s | tee -a "$OUT"
run kubectl get pods -n $NS -l 'app in (postgres,redis)'

echo "--- Despues: los datos siguen ahi" | tee -a "$OUT"
echo "Postgres despues:" | tee -a "$OUT"; $PG "SELECT id, valor FROM h16_persistencia ORDER BY id" | tee -a "$OUT"
echo "Redis despues:" | tee -a "$OUT"
RESULT=$(kubectl exec -n $NS deploy/redis -- redis-cli get h16:prueba)
echo "$RESULT" | tee -a "$OUT"

if [ "$RESULT" = "$STAMP" ] && $PG "SELECT 1 FROM h16_persistencia WHERE valor='$STAMP'" | grep -q 1; then
  echo "RESULTADO: PERSISTENCIA OK (Postgres y Redis conservaron los datos)" | tee -a "$OUT"
else
  echo "RESULTADO: FALLO DE PERSISTENCIA" | tee -a "$OUT"
fi

seccion "6. Estado final"
run kubectl get pods -n $NS
echo "Evidencias guardadas en $OUT"
