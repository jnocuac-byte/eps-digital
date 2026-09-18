#!/usr/bin/env bash

# Cargar variables globales de la raíz si existe
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

echo "🚀 Iniciando microservicios de EPS Digital..."

# Liberar puertos zombie de corridas anteriores
liberar_puertos() {
  for puerto in 8001 8002 8003 8004 8005 8006 5173; do
    fuser -k "${puerto}/tcp" 2>/dev/null || true
  done
}
liberar_puertos

# Función auxiliar para correr un servicio ubicándose en su directorio
run_service() {
  local dir=$1
  local port=$2
  
  (
    cd "$dir" || exit
    ENV_FILE_FLAG=""
    if [ -f ".env" ]; then
      ENV_FILE_FLAG="--env-file .env"
    fi
    PYTHONPATH=. uv run uvicorn app.main:app --port "$port" $ENV_FILE_FLAG --reload
  ) &
}

# 1. Auth Service
run_service "services/auth-service" 8001

# 2. User Service
run_service "services/user-service" 8002

# 3. Appointments Service
run_service "services/appointments-service" 8003

# 4. Catalog Service
run_service "services/catalog-service" 8004

# 5. AI/NLP Service
run_service "services/ai-nlp-service" 8005

# 6. Notification Service
run_service "services/notifications-service" 8006

# 7. Frontend
(cd frontend && npm run dev) &

echo ""
echo "=================================================="
echo "✅ SERVICIOS EN EJECUCIÓN:"
echo "   - Auth:         http://localhost:8001"
echo "   - User:         http://localhost:8002"
echo "   - Appointments: http://localhost:8003"
echo "   - Catalog:      http://localhost:8004"
echo "   - AI/NLP:       http://localhost:8005"
echo "   - Notification: http://localhost:8006"
echo "   - Frontend:     http://localhost:5173"
echo "=================================================="
echo "Presiona Ctrl+C para apagar todos los servicios."
echo ""

# Capturar señal para cerrar todos los subprocesos al presionar Ctrl+C
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT
wait