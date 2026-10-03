#!/usr/bin/env bash
# Levanta la demo de EPS Digital (H-16) con un solo comando:  bash levantar-demo.sh
# Requiere GitHub CLI (gh) autenticado con scope codespace.
set -euo pipefail

REPO="jnocuac-byte/eps-digital"
BRANCH="feat/h16-kubernetes"
NAME="${CODESPACE_NAME:-}"

command -v gh >/dev/null || { echo "Falta GitHub CLI (gh)"; exit 1; }

# 1) Buscar el Codespace (repo + nombre eps-h16); crearlo si no existe.
if [ -z "$NAME" ]; then
  NAME="$(gh codespace list --json name,displayName,repository -q ".[] | select(.repository==\"$REPO\" and .displayName==\"eps-h16\") | .name" | head -n1)"
  if [ -z "$NAME" ]; then
    echo "No hay Codespace: creandolo..."
    NAME="$(gh codespace create -R "$REPO" -b "$BRANCH" -m standardLinux32gb --idle-timeout 240m --display-name eps-h16 | tail -n1)"
  fi
fi
echo "Codespace: $NAME"

# 2) Encenderlo si esta detenido (ssh lo arranca) y esperar.
for _ in $(seq 1 60); do
  estado="$(gh codespace view -c "$NAME" --json state -q .state)"
  [ "$estado" = "Available" ] && break
  echo "Estado: $estado ..."
  [ "$estado" = "Shutdown" ] && gh codespace ssh -c "$NAME" -- true >/dev/null 2>&1 || true
  sleep 10
done

# 3) Desplegar (idempotente).
gh codespace ssh -c "$NAME" -- "cd /workspaces/eps-digital && git pull -q --ff-only; bash k8s/deploy.sh"

# 4) Puerto publico y URL.
gh codespace ports visibility 8080:public -c "$NAME"
URL="https://${NAME}-8080.app.github.dev"
echo
echo "=========================================="
echo " DEMO LISTA: $URL"
echo "=========================================="
echo "Al terminar: gh codespace stop -c $NAME"
