# AGENTS.md - EPS Digital Development Guide

Plataforma de EPS colombiana para agendamiento de citas médicas con asistente virtual IA.
Monorepo con dos mundos: microservicios Python/FastAPI (`services/`) y SPA React (`frontend/`).
Este archivo prioriza visión general, reglas globales y gotchas. Los detalles de implementación
se resuelven en el contexto de cada sesión leyendo el código fuente.

---

## Documentación profunda del repo

Documentos generados a partir del código (regenerar si la arquitectura cambia mucho):

| Archivo | Contenido |
|---|---|
| `backend_context.md` | Modelos SQLAlchemy, schemas Pydantic, endpoints, lógica de negocio y migraciones por servicio |
| `frontend_context.md` | Enrutamiento, layouts/guards, tipos TS, stores, cliente API y páginas |
| `e2e_integration_context.md` | Mapeo Front → Endpoint → Tabla BD, flujos críticos (auth, citas, IA) y Docker/despliegue |

Si un documento contradice el código, gana el código.

## Estructura del repositorio

```
services/            # 6 microservicios FastAPI, cada uno autónomo (Dockerfile + compose + alembic)
frontend/            # SPA React + Vite + TypeScript + Tailwind
docs/                # documentación adicional del proyecto
docker-compose.yml   # stack completo raíz (5 Postgres + RabbitMQ + 6 servicios)
backend_context.md / frontend_context.md / e2e_integration_context.md
AGENTS.md            # este archivo
```

Estructura interna estándar de cada servicio:

```
services/<svc>/
├── app/
│   ├── main.py       # endpoints FastAPI + CORS + lifespan
│   ├── models.py     # modelos SQLAlchemy (Mapped/mapped_column)
│   ├── schemas.py    # schemas Pydantic v2 (requests/responses)
│   ├── crud.py       # lógica de negocio y acceso a datos
│   └── database.py   # engine/session desde DATABASE_URL (.env)
├── alembic/          # migraciones (versions/)
├── tests/            # scripts manuales, sin runner configurado
├── Dockerfile        # python:3.12-slim, CMD: alembic upgrade head && uvicorn
└── docker-compose.yml
```

Frontend (`frontend/src/`): `main.tsx` → `app/App.tsx` (QueryClientProvider + RouterProvider)
→ `app/routes.tsx`, con `components/` (layouts, guards, ui/shadcn), `lib/` (apiClient,
queryClient), `stores/` (authStore), `types/`, `pages/` (raíz + `admin/` + `medico/`).

---

## Comandos rápidos

| Contexto | Comando |
|---|---|
| Frontend dev | `cd frontend && npm run dev` (localhost:5173) |
| Frontend build | `cd frontend && npm run build` (única verificación disponible) |
| Backend por servicio | `cd services/<svc> && uvicorn app.main:app --reload --port 800X` |
| Swagger | `http://localhost:800X/docs` |
| Validar Python | `python3 -m py_compile <archivo>` |
| Docker completo | `docker compose up --build` (raíz) |
| Docker aislado | `cd services/<svc> && docker compose up` |
| Smoke test rutas | `python3 -c "from app.main import app; print([(m, r.path) for r in app.routes for m in getattr(r,'methods',[])])"` |

---

## Arquitectura de servicios

| Servicio | Puerto | BD PostgreSQL | Responsabilidad |
|---|---|---|---|
| auth-service | 8001 | `eps_auth` (host 5432) | Credenciales, JWT access/refresh, 2FA opcional, bloqueo por intentos, recuperación. Publica evento RabbitMQ `cuenta_creada` |
| user-service | 8002 | `eps_user` (host 5433) | Perfiles `usuarios`, `informacion_medica`, `afiliaciones`. Fuente de búsqueda por documento |
| appointments-service | 8003 | `eps_citas` (host 5434) | Citas, historial de estados, recordatorios, métricas y slots disponibles (zona `America/Bogota`) |
| catalog-service | 8004 | `eps_catalogo` (host 5435) | Servicios, especialidades, médicos, sedes, disponibilidad semanal. Borrado lógico (`activo=false`) |
| ai-nlp-service | 8005 | `eps_ainlp` (host 5436) | Chatbot Groq, clasificación de síntomas, agendado por function calling |
| notifications-service | 8006 | externa vía `DATABASE_URL` | Consumer RabbitMQ → emails SendGrid; notificaciones in-app para médicos (HTTP API) |

- Cada servicio = su propia BD. **Sin Foreign Keys entre bases**: las referencias cruzadas son
  UUIDs lógicos (ej. `credenciales.usuario_id`, `citas.medico_id/sede_id/especialidad_id`,
  `notificaciones.medico_id`). La integridad la aplica la capa de aplicación.
- Comunicación síncrona REST con `httpx`: auth→user, citas→catálogo, ai-nlp→catálogo/citas.
- Comunicación asíncrona RabbitMQ: ver sección "Mensajería".

---

## Stack

### Backend común (todos los servicios)
- FastAPI + Uvicorn + SQLAlchemy 2.0 estilo declarativo (`Mapped`, `mapped_column`)
- Pydantic v2 (schemas con validadores `field_validator` / `model_validator`)
- Alembic para migraciones; `psycopg2-binary`; `httpx` para llamadas inter-servicio
- auth: `bcrypt` (12 rounds) + `python-jose` (JWT HS256); pika (RabbitMQ)
- ai-nlp: SDK `groq` + `tzdata` (zonas horarias); notifications: `sendgrid` + `pika`

### Frontend
- React 18 + Vite 6 + TypeScript + Tailwind CSS 4 (`@tailwindcss/vite`)
- react-router 7 (`createBrowserRouter`), TanStack Query 5, Zustand 5 (middleware `persist`)
- Axios (6 instancias), `sonner` (toasts), `recharts`, `react-markdown`, lucide-react
- Componentes shadcn/ui sobre Radix en `app/components/ui/` (poco usados aún)

---

## Reglas globales del backend

- Patrón por capas en cada servicio: `main.py` (HTTP) → `crud.py` (negocio/datos) → `models.py`.
- Los endpoints traducen `ValueError` de negocio a HTTP 400 (404 cuando el mensaje contiene
  "No existe"); los errores de validación de Pydantic producen 422 — revisar `schemas.py` primero.
- CORS fijo en todos: `https://eps-digital-cn2h.onrender.com` + `http://localhost:5173`
  (+ regex `https://.*\.onrender\.com`). `allow_headers` incluye
  `["Authorization", "Content-Type", "Accept", "X-User-ID"]` en auth y notifications.
- Solo auth-service firma/valida JWT (`HS256`, claim `tipo: access|refresh`). Los demás
  servicios confían en headers; appointments usa además `X-User-ID` (cancelar/reprogramar).
- Auth-service provee `GET /auth/medico-id` (requiere Bearer) que retorna `credencial.medico_id`.
  Este campo **debe estar poblado** en la tabla `credenciales` para que el portal médico funcione.
- Catálogo: eliminaciones **lógicas** (`activo=false`); usuarios/citas: hard delete.
- Auditoría de autenticación en tabla `log_autenticacion` (login exitoso/fallido, bloqueos, 2FA).
- Bloqueo de cuenta: >5 intentos fallidos → 15 minutos (`auth.py`).

### Regla de zona horaria (crítica en citas)
- Toda lógica de fechas/horas de citas usa los helpers `hoy_bogota()` / `ahora_bogota()`
  (`ZoneInfo("America/Bogota")` en `appointments-service/app/crud.py`).
- **Prohibido** `date.today()` o `datetime.now()` desnudos para decisiones de negocio:
  Render corre en UTC y desfasa 5 horas respecto a Colombia.
- Anticipación mínima para citas del mismo día: 60 minutos (constante
  `ANTELACION_MINIMA_MINUTOS`), aplicada en `POST /citas` y en slots.

### Gotcha FastAPI: orden de declaración de rutas
FastAPI casa rutas en orden de declaración. Las rutas **fijas deben declararse ANTES** que las
dinámicas con parámetro UUID: `/citas/slots-disponibles`, `/citas/metricas` y
`/citas/medico/{id}/metricas` van antes de `/citas/{cita_id}`. Si se declara después,
FastAPI intenta parsear el literal como UUID → 422 silencioso. Verificar con el smoke test
de rutas al añadir endpoints bajo `/citas/`.

---

## Base de datos y migraciones

- Los 6 servicios tienen Alembic configurado (`alembic.ini` + `alembic/env.py` + revisión
  inicial en `alembic/versions/`). El arranque (compose y Render) ejecuta
  `alembic upgrade head && uvicorn ...`.
- Red de seguridad doble: cada `lifespan` FastAPI ejecuta además `Base.metadata.create_all`.
  Para producción debe primar Alembic.
- **CRÍTICO**: cualquier cambio de modelo (columnas, nullables, índices) exige nueva migración
  en `alembic/versions/` antes de desplegar. Crear manualmente o con
  `alembic revision --autogenerate` (revisar el diff generado).
- appointments-service conserva además SQL manual idempotente:
  `migrations/*.sql` + `scripts/run_migrations.sh` (aplica con `psql "$DATABASE_URL"`).
- catalog-service tiene `migrations/001_add_usuario_id_to_medicos.sql` cuya columna
  NO existe en el modelo ORM `Medico` (conocido, no romper).

---

## Mensajería asíncrona (RabbitMQ)

| Rol | Servicio | Detalle |
|---|---|---|
| Productor | auth-service | `rabbitmq_client.publicar_evento(evento, payload)` — colas durables, JSON persistente (`delivery_mode=2`). Emite `cuenta_creada` en el registro |
| Consumidor | notifications-service | Escucha `cita_confirmada`, `cita_cancelada`, `cita_recordatorio`, `cuenta_creada` → plantilla HTML → SendGrid |

- Ack manual siempre (`finally`); reconexión automática cada 5 s; consumer corre como thread
  daemon iniciado en el `lifespan`.
- Notificaciones internas (campana web) van por HTTP: `POST {NOTIFICATIONS_SERVICE_URL}/notificaciones`
  con `{ medico_id, tipo, titulo, descripcion }`. RabbitMQ/SendGrid son solo para emails externos.
- Las colas `cita_*` están preparadas pero hoy NINGÚN servicio las publica (no hay emails de
  confirmación/cancelación de citas por esa vía).
- ⚠ `RABBITMQ_DEFAULT_URL` tiene credenciales CloudAMQP hardcodeadas como fallback en
  `rabbitmq_client.py` y `consumer.py` — depender siempre de `RABBITMQ_URL`.

---

## Frontend: patrones y reglas

- Estado de sesión: `app/stores/authStore.ts` (Zustand + persist) — guarda tokens JWT,
  userId, user, rol y medicoId en `localStorage` bajo la clave `'eps-auth-storage'`.
  `logout()` resetea todo.
- Cliente API único: `app/lib/apiClient.ts`. Define 6 instancias Axios (auth/user/citas/
  catálogo/ai/notificaciones), **todas con interceptor** que inyecta `Authorization: Bearer` +
  header `X-User-ID`. Un 401 dispara `logout()` + redirect duro a `/login`.
- ⚠ Las URLs base se eligen por hostname dentro de `apiClient.ts` (localhost vs `*.onrender.com`).
  El archivo `frontend/.env` define `VITE_*_URL` pero **nadie las lee**: cambiar el .env no
  tiene efecto.
- Actualización de perfil de usuario usa **PUT**, no PATCH: `userClient.put('/usuarios/${id}', data)`.
- Disponibilidad de servicios del catálogo usa campo **`activo`** (backend); el tipo TS
  `Servicio.disponible` existe pero el backend nunca lo envía.
- TanStack Query: invalidar queryKeys tras toda mutación (create/update/delete).
  Convención de keys observada: `['citas', userId]`, `['user-completo', userId]`,
  `['slots', medicoId, especialidadId, servicioId, fechaISO]`, `['notificaciones', medicoId]`.
- Slots de citas: el cálculo vive en el backend (`GET /citas/slots-disponibles`, formato
  `"HH:MM"` 24h). No recalcular franjas en el frontend.
- Guards de ruta: `ProtectedRoute` (paciente), `MedicoProtectedRoute` (rol `medico`).
  `RoleRoute` existe pero no está cableado en `routes.tsx`.
- ⚠ `pages/admin/*` NO está registrado en `routes.tsx` y llama funciones/tipos inexistentes
  en `apiClient.ts`/`types/index.ts`. Compila por casts `as any`; no darlo por funcional.
- Login real del frontend: `POST /auth/login/documento` (por documento, no por correo).
  LoginPage.tsx extrae `rol` de la respuesta y redirige a `/medico/dashboard` si
  `userRol?.toLowerCase() === 'medico'`. MedicoLoginPage usa la misma comparación
  case-insensitive. El `rol` se normaliza a minúsculas en la store (`setRol(rol.toLowerCase())`).
  2FA y recuperación de contraseña existen en backend sin UI.
- Chat IA: respuestas en Markdown renderizadas con `react-markdown`;
  `ChatResponse.clasificacion` llega como **objeto** en `msg.action` (no string);
  pasar `userId` del store a `aiApi.chat(mensaje, conversacion_id?, usuario_id?)`.

---

## Chatbot AI-NLP: contrato de tools

Flujo de agendado conversacional (function calling contra servicios reales):
`obtener_especialidades()` → usuario elige → `obtener_medicos(especialidad_id)` →
`obtener_sedes()` → fecha/hora → confirmar → `agendar_cita(...)`.

Endpoints correctos del Catalog Service para las tools:
- `/especialidades`
- `/especialidades/{especialidad_id}/medicos` (NO `/medicos?especialidad_id=`)
- `/sedes`

Y para agendar: `POST {CITAS_SERVICE_URL}/citas` con header `X-User-ID`.

Notas:
- Modelo Groq `llama-3.3-70b-versatile`; `chat_completion` usa `max_tokens=400`.
- Errores y confirmaciones SIEMPRE en lenguaje natural, sin UUIDs ni tecnicismos
  (`groq_client.py` ya formatea; `prompts.py` controla estilo y longitud).
- `obtener_disponibilidad_citas` es simulada (cupos fijos); el resto consulta servicios reales.

---

## Variables de entorno (consumidas realmente por el código)

| Variable | Servicios | Uso |
|---|---|---|
| `DATABASE_URL` | todos | engine SQLAlchemy (`load_dotenv()` lee `.env` local) |
| `JWT_SECRET_KEY` | auth | firma HS256 (único punto de verdad) |
| `USER_SERVICE_URL` | auth | login por documento (`/usuarios/buscar`) |
| `CATALOG_SERVICE_URL` | citas, ai-nlp | médicos disponibles, especialidades, sedes |
| `NOTIFICATIONS_SERVICE_URL` | citas | notificaciones internas al agendar (`POST /notificaciones`) |
| `CITAS_SERVICE_URL` | ai-nlp | agendado real desde el chat |
| `GROQ_API_KEY` | ai-nlp | cliente LLM |
| `RABBITMQ_URL` | auth, notifications | broker AMQP (fallback hardcodeado: rotar credenciales) |
| `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`/`EMAIL_FROM` | notifications | envío de correos |

---

## Despliegue (Render + Docker)

- Frontend producción: https://eps-digital-cn2h.onrender.com
- SPA fallback: se requiere `frontend/public/_redirects` con `/* /index.html 200`
  (el archivo NO existe aún — crearlo antes de servir builds de producción).
- **Render Start Command** de cada backend debe incluir `$PORT`:
  `alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Tras deployar, revisar logs para confirmar que uvicorn escucha en el puerto correcto.
- Gotchas de Dockerfile conocidos (no romper más): frontend sirve el **dev server** de Vite
  (sin build/nginx); Dockerfile de ai-nlp tiene `EXPOSE 8003` erróneo (real: 8005).
- URLs de servicios en producción están hardcodeadas en `frontend/src/app/lib/apiClient.ts`.

---

## Convenciones de trabajo del agente

- Commits convencionales con descripción en español:
  `feat(citas): mejorar flujo de agendamiento de citas médicas`
- Al pedir un commit: **mostrar el comando primero sin ejecutarlo**.
- Siempre validar sintaxis Python tras editar: `python3 -m py_compile <archivo>`.
- El frontend no tiene lint/typecheck configurados: verificar cambios con `npm run build`.
- Tests: carpetas `tests/` por servicio son scripts manuales sin runner; no asumir pytest CI.
- Cambios de modelo ⇒ migración Alembic en la misma PR, nunca después.
- Desacoples conocidos aceptados (no "corregir" sin consultar): columna `notif_id`
  vs `notificacion_id` en frontend; campos `*_nombre` de `Cita` esperados por la UI que el
  backend aún no retorna.

---

## Archivos críticos (empezar por aquí al diagnosticar)

| Archivo | Por qué importa |
|---|---|
| `frontend/src/app/lib/apiClient.ts` | Único punto de URLs base, interceptores y namespaces `*Api` |
| `frontend/src/app/types/index.ts` | Contratos TS; fuente de desacoples con schemas del backend |
| `frontend/src/app/stores/authStore.ts` | Sesión persistida (tokens, rol, medicoId) |
| `frontend/src/app/pages/RegisterPage.tsx` | Validación de contraseña duplicada front/back |
| `frontend/src/app/pages/AgendarCitaPage.tsx` | Flujo de slots y creación de citas |
| `services/*/app/schemas.py` | Validaciones Pydantic (origen típico de errores 422) |
| `services/auth-service/app/auth.py` | JWT, bcrypt, bloqueos, 2FA, recuperación |
| `services/appointments-service/app/crud.py` | Citas, slots, zona horaria Bogotá, métricas |
| `services/catalog-service/app/crud.py` | Disponibilidad de médicos y borrado lógico |
| `services/ai-nlp-service/app/groq_client.py` | Tools del asistente y llamadas inter-servicio |
| `services/ai-nlp-service/app/prompts.py` | SYSTEM_PROMPT: tono, formato Markdown, límites |
| `services/notifications-service/app/consumer.py` | Colas RabbitMQ y despacho de plantillas |
