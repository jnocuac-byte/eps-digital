# H-16 Orquestación en Kubernetes – Informe de entrega

## 1. URL y Pull Request

- **URL única de la aplicación:** https://eps-h16-6vrjpqp5r49v35q6x-8080.app.github.dev
  (solo responde mientras el Codespace esté encendido; ver sección 4 para encenderlo)
- **Pull Request:** https://github.com/jnocuac-byte/eps-digital/pull/58 (rama `feat/h16-kubernetes` → `develop`)

## 2. Criterios de la H-16

| Criterio | Dónde se hizo | Evidencia |
|---|---|---|
| 1. Arquitectura del clúster y plataforma (Minikube) | `k8s/README.md` (diagrama y justificación), `.devcontainer/devcontainer.json`, `k8s/deploy.sh` | `k8s/evidencias-h16.txt`, sección 1 (nodo del clúster y versión) |
| 2. Deployment y Service de los 6 microservicios | `k8s/services/` (un archivo por servicio), `k8s/frontend.yaml`, `k8s/kustomization.yaml` | Sección 2 (`kubectl get all`): todos los pods `Running 1/1` |
| 3. Ingress con URL única | `k8s/ingress.yaml`, `frontend/src/app/lib/apiClient.ts`, `frontend/Dockerfile.k8s` | Sección 4: `/` y `/api/*/health` responden HTTP 200 por la misma URL |
| 4. Liveness y readiness probes | `/health` y `/ready` en el `main.py` de cada servicio; probes en cada manifiesto | Sección 3: `describe` mostrando `Liveness` y `Readiness` |
| 5. PV y PVC para PostgreSQL y Redis | `k8s/postgres/postgres.yaml`, `k8s/redis/redis.yaml` | Sección 5: se escribió un dato, se borraron los pods y el dato seguía ahí (`PERSISTENCIA OK`) |

## 3. Archivos creados y modificados

**Creados**
- `k8s/00-namespace.yaml` – namespace `eps-digital`.
- `k8s/01-configmap.yaml` – URLs internas entre servicios, RabbitMQ, Redis, nivel de logs.
- `k8s/secret.example.yaml` – plantilla del secreto (sin valores reales).
- `k8s/kustomization.yaml` – permite desplegar todo con `kubectl apply -k k8s/`.
- `k8s/postgres/postgres.yaml` – PostgreSQL con 6 bases, volumen persistente (PV/PVC) y probes.
- `k8s/redis/redis.yaml` – Redis con volumen persistente (PV/PVC) y probes.
- `k8s/rabbitmq/rabbitmq.yaml` – RabbitMQ (cola de mensajes) con probes.
- `k8s/services/auth-service.yaml`, `user-service.yaml`, `appointments-service.yaml`, `catalog-service.yaml`, `ai-nlp-service.yaml`, `notifications-service.yaml` – Deployment + Service de cada microservicio, con probes y límites de recursos.
- `k8s/frontend.yaml` – Deployment + Service de la página web.
- `k8s/ingress.yaml` – la puerta de entrada única (`/` y `/api/<servicio>`).
- `k8s/deploy.sh` – despliega todo dentro del Codespace con un comando.
- `k8s/evidencias.sh` – genera las evidencias, incluida la prueba de persistencia.
- `k8s/evidencias-h16.txt` – resultado real de las evidencias.
- `k8s/README.md` – arquitectura, justificación de Minikube, cómo desplegar, tabla de criterios.
- `frontend/Dockerfile.k8s` – imagen de producción de la web (compila y sirve con nginx).
- `.devcontainer/devcontainer.json` – define el Codespace (Docker, kubectl, minikube, SSH).
- `.gitattributes` – mantiene los `.sh` con saltos de línea de Linux.
- `levantar-demo.ps1` / `levantar-demo.sh` – encienden la demo con un solo comando.
- `H16-PROGRESO.md` – bitácora de avance por fases.
- `H16-ENTREGA.md` – este informe.

**Modificados**
- `services/{auth,user,appointments,catalog,ai-nlp}-service/app/main.py` – agregan `/health` y `/ready` (revisa la base de datos).
- `services/notifications-service/app/main.py` – agrega `/ready` (ya tenía `/health`).
- `frontend/src/app/lib/apiClient.ts` – modo "gateway": con `VITE_API_MODE=gateway` usa rutas `/api/...`; sin esa variable todo funciona como antes.
- `.gitignore` – ignora `k8s/secret.yaml` y `.env`.

## 4. Cómo demostrarlo en la presentación

1. **Antes de exponer (10 min antes):** en PowerShell, dentro de la carpeta del proyecto, ejecuta
   `powershell -ExecutionPolicy Bypass -File .\levantar-demo.ps1`.
   Enciende el Codespace si está apagado, despliega y al final imprime la URL (tarda de 1 a 8 minutos).
2. **Abre la URL** en el navegador. *Decir:* "Toda la aplicación entra por una sola dirección" (criterio 3).
3. **Muestra el clúster** (abre `k8s/evidencias-h16.txt`, o ejecuta
   `gh codespace ssh -c eps-h16-6vrjpqp5r49v35q6x -- "kubectl get pods -n eps-digital"`).
   *Decir:* "Los 6 servicios, la base de datos, Redis y RabbitMQ corren como pods en Minikube" (criterios 1 y 2).
4. **Probes:** abre en el navegador `<URL>/api/auth/health` y `<URL>/api/auth/ready` (cambia `auth` por `user`, `citas`, `catalogo`, `ai`, `notifications`).
   *Decir:* "Kubernetes consulta `/health` para saber si el servicio vive y `/ready` para saber si ya puede recibir tráfico" (criterio 4). Sección 3 del archivo de evidencias muestra la configuración.
5. **Persistencia:** muestra la sección 5 de `k8s/evidencias-h16.txt`, o ejecuta
   `gh codespace ssh -c eps-h16-6vrjpqp5r49v35q6x -- "cd /workspaces/eps-digital && bash k8s/evidencias.sh"`.
   *Decir:* "Guardamos un dato, borramos los pods de Postgres y Redis, y los datos siguen ahí gracias a los volúmenes persistentes" (criterio 5).
6. **Cierre:** muestra el Pull Request #58 con la tabla de criterios. Al terminar, apaga el Codespace:
   `gh codespace stop -c eps-h16-6vrjpqp5r49v35q6x`.

## 5. Comentario para la tarjeta H-16 (GitHub Projects)

```
✅ H-16 Orquestación en Kubernetes – lista para revisión (PR #58 → develop)

- Plataforma: Minikube (gratis, mismo API de Kubernetes que EKS/GKE), corriendo en un Codespace.
- Deployment + Service para los 6 microservicios, más frontend, Postgres, Redis y RabbitMQ.
- Ingress NGINX con URL única: "/" → frontend, "/api/<servicio>" → microservicios.
- Liveness (/health) y readiness (/ready) en todos los servicios; probes también en Postgres, Redis y RabbitMQ.
- PV + PVC para PostgreSQL (2Gi) y Redis (1Gi). Persistencia verificada: se borraron los pods y los datos se conservaron.
- Evidencias: k8s/evidencias-h16.txt. Documentación: k8s/README.md.
- Demo: levantar-demo.ps1 (un solo comando).
Nota: Redis queda aprovisionado pero sin uso en el código todavía.
```

## 6. Advertencias honestas

- **Redis está aprovisionado pero ningún servicio lo usa todavía.** Cumple el criterio (PV/PVC y probes), pero hoy no cumple ninguna función.
- **El chatbot necesita una `GROQ_API_KEY` real** (o las de Gemini/Cerebras/Mistral). Sin ellas la aplicación arranca, pero el asistente no responde. Se ponen en un `.env` en la raíz del Codespace y se vuelve a ejecutar `k8s/deploy.sh`.
- **El Codespace se apaga solo** tras 4 horas sin actividad (o al detenerlo). Para volver a encenderlo: `levantar-demo.ps1`. Los datos se conservan mientras no se borre el Codespace.
- **La URL cambia si se crea otro Codespace.** El script reutiliza el existente (nombre `eps-h16`).
- **Cambios respecto al plan, por problemas reales encontrados:**
  - La imagen `universal:2` llenó el disco de 32 GB; el Codespace usa una base Ubuntu ligera con Docker, kubectl, minikube y SSH.
  - Postgres usa `pgvector/pgvector:pg15` en lugar de `postgres:15-alpine`: la rama `develop` incluye una migración que necesita la extensión `vector`.
  - La rama se basó en `develop` (tenía 13 commits más que `main`) y el PR apunta a `develop`.
  - `LOG_LEVEL` es `INFO` en mayúsculas; con `info` los servicios no arrancaban.
- No se probó el flujo completo de la aplicación (registro, login, agendar cita) en Kubernetes. Se verificó salud de servicios, Ingress, consultas a la base de datos por el Ingress (`/api/catalogo/servicios`, `/api/citas/citas/metricas`) y persistencia. La base de datos está vacía (sin servicios ni especialidades cargados), por eso esas consultas devuelven listas vacías.
- Contraseñas por defecto de RabbitMQ (`guest/guest`) en el ConfigMap, igual que en `docker-compose.yml`: aceptable para demo, no para producción.
