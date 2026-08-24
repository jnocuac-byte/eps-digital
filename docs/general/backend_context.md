# Backend Context — EPS Digital

> Documento de arquitectura generado a partir del análisis directo del código fuente en `services/`.
> Stack transversal: **FastAPI + SQLAlchemy 2.0 (estilo `Mapped`/`mapped_column`) + Pydantic v2 + Alembic + Uvicorn**.
> Despliegue: Docker Compose por servicio (PostgreSQL 15 Alpine) y Render en producción.

---

## 1. Visión General de Microservicios

| Microservicio | Puerto | Base de Datos (docker-compose) | Puerto BD host | Responsabilidad Principal |
|---|---|---|---|---|
| **auth-service** | `8001` | `eps_auth` (`services/auth-service/app/main.py`, título *"EPS Digital - Auth Service"*) | `5432` | Autenticación JWT (access + refresh), registro de credenciales, 2FA opcional, bloqueo por intentos fallidos y recuperación de contraseña. Publica el evento RabbitMQ `cuenta_creada`. |
| **user-service** | `8002` | `eps_user` | `5433` | Gestión del perfil del usuario (`usuarios`), información médica (`informacion_medica`) y afiliación EPS (`afiliaciones`). Fuente de verdad para búsqueda por documento. |
| **appointments-service** | `8003` | `eps_citas` | `5434` | Ciclo de vida de citas médicas: creación con validación de disponibilidad, cancelación, reprogramación, historial de estados, recordatorios y métricas para dashboards (admin/médico). |
| **catalog-service** | `8004` | `eps_catalogo` | `5435` | Catálogo maestro: servicios, especialidades, médicos, relación N:M médico–especialidad, sedes y disponibilidad semanal. Borrado lógico vía campo `activo`. |
| **ai-nlp-service** | `8005` | `eps_ainlp` | `5436` | Chatbot médico con **Groq** (`llama-3.3-70b-versatile`), clasificación de síntomas con JSON estructurado y agendado real de citas mediante *function calling*. |
| **notifications-service** | `8006` | PostgreSQL externo (vía `DATABASE_URL`; sin contenedor propio en su compose) | — | Consumidor RabbitMQ que envía correos transaccionales vía **SendGrid**, además de notificaciones in-app dirigidas a médicos (`notificaciones`). |

**Infraestructura compartida**: RabbitMQ 3.12 (puertos AMQP `5672` / Management UI `15672`) definido en `services/notifications-service/docker-compose.yml`; en producción se usa CloudAMQP (`amqps://...@shark.rmq.cloudamqp.com`). Todos los servicios exponen Swagger en `/docs`.

---

## 2. Modelos de Datos y Capa de Persistencia

### 2.1 auth-service

Archivo: `services/auth-service/app/models.py` — `Base` declarativa desde `app/database.py` (engine leído de `DATABASE_URL`, `pool_pre_ping=True`, fallback SQLite con `check_same_thread=False`).

#### Entidad `Credencial` → tabla `credenciales`
| Columna | Tipo | Restricciones |
|---|---|---|
| `credencial_id` | `UUID` (PK) | `server_default=gen_random_uuid()` |
| `usuario_id` | `UUID` | `unique`, **sin ForeignKey** (referencia lógica al User Service) |
| `correo` | `String(255)` | `unique`, indexado (`ix_credenciales_correo`) |
| `password_hash` | `String(255)` | hash bcrypt, nunca texto plano |
| `rol` | `String(50)` | default `'usuario'` (valores usados: `usuario`, `medico`, `admin`) |
| `activo` | `Boolean` | default `true` |
| `intentos_fallidos` | `SmallInteger` | default `0` (control de bloqueo) |
| `bloqueado_hasta` | `TIMESTAMP` | nullable |
| `tiene_2fa` | `Boolean` | default `false` |
| `medico_id` | `UUID` | nullable, referencia lógica al médico en Catalog Service |
| `creado_en` / `actualizado_en` | `TIMESTAMP` | defaults `utc_now`, `onupdate` |

#### Entidad `TokenRecuperacion` → tabla `token_recuperacion`
- `token_id` UUID PK; `credencial_id` **FK → `credenciales.credencial_id`**; `token_hash` `String(255)` **unique** (SHA256 del token crudo); `expira_en` TIMESTAMP; `usado` Boolean default false; índices `ix_token_recuperacion_credencial_id` y `ix_token_recuperacion_token_hash`.

#### Entidad `Registro2FA` → tabla `registro_2fa`
- `registro_id` UUID PK; `credencial_id` **FK → credenciales**; `codigo_hash` String(255) (OTP hasheado); `expira_en`; `usado`; índice compuesto `ix_registro_2fa_usado_expira_en`.

#### Entidad `LogAutenticacion` → tabla `log_autenticacion`
- Bitácora de auditoría: `log_id` UUID PK; `credencial_id` **FK → credenciales**; `evento` String(50) (`login_exitoso`, `login_fallido`, `login_rechazado_bloqueo`, `2fa_verificacion_exitosa`, `password_reset`, `registro_exitoso`, etc.); `ip_origen` String(45); `agente_usuario` Text.

> Compatibilidad: listeners `@event.listens_for(..., "before_insert")` (`set_sqlite_uuid_defaults*`) generan UUID en Python cuando el dialecto no es PostgreSQL (desarrollo con `auth_dev.db`).

#### Schemas Pydantic (`app/schemas.py`)
Constantes: `TIPOS_DOCUMENTO_VALIDOS = {"CC", "CE", "PA", "TI"}`, `CODIGO_2FA_PATTERN = r"^\d{6}$"`.

| Schema | Rol | Validadores clave |
|---|---|---|
| `UserRegister` | Request `POST /auth/register` | `validar_tipo_documento`, `validar_password_segura` (min 8 + mayúscula + número), `validar_confirm_password` (coincidencia), `validar_acepta_terminos` (debe ser `True`) |
| `UserLogin` | Request login por correo | `correo: EmailStr`, `password` |
| `UserLoginDocumento` | Request login por documento | normaliza `tipo_documento` a mayúsculas |
| `Verify2FARequest` / `Enable2FARequest` | Requests 2FA | `codigo` con patrón OTP de 6 dígitos; `credencial_id: UUID` |
| `RecoverRequest` / `ResetPasswordRequest` | Flujo de recuperación | `new_password` revalidada; confirmación obligatoria |
| `TokenResponse` / `RefreshTokenRequest` | Renovación de access token | `access_token`, `refresh_token`, `token_type="bearer"` |
| `LoginResponse` | Response de login | `usuario_id: UUID`, `requiere_2fa: bool`, `rol: str \| None` (tokens vacíos cuando falta 2FA) |
| `MessageResponse` / `RegisterResponse` / `ErrorResponse` | Responses genéricas | `RegisterResponse` hereda y agrega `usuario_id: str` |

### 2.2 user-service

Archivo: `services/user-service/app/models.py`

#### Entidad `Usuario` → tabla `usuarios`
- `usuario_id` UUID PK (`gen_random_uuid()`); `nombres`, `apellidos` String(100); `tipo_documento` String(20); `numero_documento` String(20) **unique**; `fecha_nacimiento` `Date`; `telefono` String(20) nullable; `correo` String(255) **unique**; auditoría `creado_en`/`actualizado_en`.
- Relaciones **1:1**: `informacion_medica` y `afiliacion` con `uselist=False` y `cascade="all, delete-orphan"`.

#### Entidad `InformacionMedica` → tabla `informacion_medica`
- `info_medica_id` UUID PK; `usuario_id` **FK → `usuarios.usuario_id`** + `unique=True` (materializa la relación 1:1); `tipo_sangre` String(5) nullable; `alergias`, `enfermedades_cronicas`, `medicamentos_actuales` Text nullable; `actualizado_en`.

#### Entidad `Afiliacion` → tabla `afiliaciones`
- `afiliacion_id` UUID PK; `usuario_id` **FK → usuarios** + `unique=True`; `tipo_afiliacion` String(20); `numero_poliza` String(50) **unique**; `estado` String(20) default `'activo'`; `fecha_afiliacion` Date; `medico_asignado_id` UUID nullable (**sin FK**, referencia al catálogo).

#### Schemas Pydantic
Constantes: `TIPOS_SANGRE_VALIDOS = {"A+","A-","B+","B-","O+","O-","AB+","AB-"}`, `TIPOS_AFILIACION_VALIDOS = {"cotizante","beneficiario","subsidiado"}`.

- `UserBase` → `UserCreate` (agrega `usuario_id: UUID` requerido, lo provee Auth Service tras el registro) → `UserResponse` (+ `creado_en`/`actualizado_en`, `from_attributes=True`).
- `UserUpdate`: actualización parcial (todos opcionales).
- `UserLookupResponse`: respuesta ligera (`usuario_id`, `correo`, `nombres`, `apellidos`) usada por Auth Service.
- `MedicalInfoBase/Create/Response` (validador `validar_tipo_sangre`) y `AfiliacionBase/Create/Response` (validador `validar_tipo_afiliacion`).
- `UsuarioCompletoResponse`: agregado `{user, informacion_medica, afiliacion}` para un solo GET.

### 2.3 appointments-service

Archivo: `services/appointments-service/app/models.py`. Todas las referencias a otras bases son **UUID sin FK** (independencia entre microservicios).

#### Entidad `Cita` → tabla `citas`
| Columna | Tipo | Notas |
|---|---|---|
| `cita_id` | UUID PK | default Python `uuid.uuid4` |
| `usuario_id` | UUID NOT NULL | referencia lógica a User Service |
| `medico_id` | UUID NOT NULL | referencia lógica a Catalog Service |
| `especialidad_id` | UUID nullable | referencia lógica a Catalog Service |
| `tipo_servicio` | String(50) | `medicina_general`, `especialista`, `urgencias`, `laboratorio` |
| `fecha_cita` | `Date` | indexada (`ix_citas_fecha_cita`) |
| `hora_inicio` / `hora_fin` | `Time` | franja horaria |
| `sede_id` | UUID NOT NULL | referencia lógica a Catalog Service |
| `descripcion_sintomas` | Text nullable | max 3000 en schema |
| `estado` | String(20) default `'programada'` | `programada`, `cancelada`, `atendida`, `no_asistio`; indexado |
- Índices: `ix_citas_usuario_id`, `ix_citas_medico_id`, `ix_citas_fecha_cita`, `ix_citas_estado`.
- Relaciones 1:N con `historial_estados` y `recordatorios` (`cascade="all, delete-orphan"`, `passive_deletes=True`).

#### Entidad `HistorialEstado` → tabla `historial_estado`
- `historial_id` UUID PK; `cita_id` **FK → `citas.cita_id` `ondelete=CASCADE`**; `estado_anterior` / `estado_nuevo` String(20); `motivo` Text nullable; `realizado_por` UUID NOT NULL.

#### Entidad `Recordatorio` → tabla `recordatorios`
- `recordatorio_id` UUID PK; `cita_id` **FK → citas `ondelete=CASCADE`**; `programado_para` TIMESTAMP (p. ej. cita − 24 h); `enviado` Boolean default False.

#### Schemas Pydantic
Conjuntos: `TIPOS_SERVICIO_VALIDOS`, `ESTADOS_CITA_VALIDOS`.
- `CitaBase`: `tipo_servicio` es `Literal[...]`; validadores de modelo `validar_rango_horas` (`hora_fin > hora_inicio`) y `validar_medico_o_especialidad` (al menos uno); `validar_descripcion_sintomas` normaliza vacíos.
- `CitaCreate`, `CitaUpdate` (parcial, valida estado y rango si ambas horas llegan), `CitaResponse` (+ `cita_id`, `estado`, timestamps, `ConfigDict(from_attributes=True)`).
- `HistorialEstadoResponse`, `RecordatorioResponse`, `CancelarCitaRequest` (`motivo` max 1000), `ReprogramarCitaRequest` (`nueva_fecha`, `nueva_hora_inicio`, `nueva_hora_fin`).

### 2.4 catalog-service

Archivo: `services/catalog-service/app/models.py`. Usa columnas `Uuid` nativas y `TIMESTAMP(timezone=True)`.

#### Diagrama relacional interno
```
Servicio (servicios) 1──N Especialidad (especialidades)
Especialidad N──M Medico (medicos)      vía MedicoEspecialidad (medico_especialidades)
Medico 1──N Disponibilidad (disponibilidades) N──1 Especialidad
Disponibilidad N──1 Sede (sedes)
```

| Entidad | Tabla | Claves y restricciones destacadas |
|---|---|---|
| `Servicio` | `servicios` | `servicio_id` PK; `nombre` **unique** (index `nombre_servicio`); `icono`; `activo` |
| `Especialidad` | `especialidades` | `servicio_id` **FK → servicios.servicio_id**; `duracion_cita_minutos` SmallInteger default 20; `activo` |
| `Medico` | `medicos` | `numero_registro` String(50) **unique** (index `medico_registro`); `correo_institucional` **unique** |
| `MedicoEspecialidad` | `medico_especialidades` | `medico_id` FK → medicos, `especialidad_id` FK → especialidades; `UniqueConstraint("medico_id","especialidad_id", name="uq_medico_especialidad_medico_especialidad")`; `es_principal` Boolean |
| `Sede` | `sedes` | `nombre`, `direccion` String(200), `ciudad`, `telefono`, `activo` |
| `Disponibilidad` | `disponibilidades` | FKs a medicos/especialidades/sedes; `dia_semana` SmallInteger con **CheckConstraint** `"dia_semana BETWEEN 1 AND 7"` (`ck_disponibilidad_dia_semana`); `hora_inicio`/`hora_fin` Time; index compuesto `disponibilidad_medico_fecha (medico_id, dia_semana, hora_inicio)` |

#### Schemas Pydantic
Base común `CatalogSchema` con `model_config = ConfigDict(from_attributes=True)`. Para cada entidad existen `*Base/*Create/*Update/*Response` (`Servicio*`, `Especialidad*` — `duracion_cita_minutos` con `ge=1, le=240` —, `Medico*` con `EmailStr`, `MedicoEspecialidad*`, `Sede*`, `Disponibilidad*`).
Validadores en `DisponibilidadBase` / `DisponibilidadUpdate`: `validar_dia_semana` (1–7, lunes=1) y `validar_hora_fin_mayor_inicio`.

### 2.5 ai-nlp-service

Archivo: `services/ai-nlp-service/app/models.py`. Usa tipos **específicos de PostgreSQL** (`sqlalchemy.dialects.postgresql.UUID` y `ARRAY`); `Base` hereda de `DeclarativeBase`.

| Entidad | Tabla | Detalle |
|---|---|---|
| `Conversacion` | `conversacion` | `conversacion_id` PK; `usuario_id` UUID (sin FK); `estado` String(20) default `"activa"` (`activa`/`cerrada`); `iniciada_en`/`cerrada_en` DateTime(tz). Relaciones: `mensajes` 1:N cascade y `clasificacion_sintomas` 1:1 (`uselist=False`) |
| `Mensaje` | `mensaje` | `conversacion_id` **FK → conversacion.conversacion_id `ondelete=CASCADE`**; `remitente` String(20) (`usuario`/`asistente`); `contenido` Text |
| `ClasificacionSintomas` | `clasificacion_sintomas` | `conversacion_id` **FK unique** (1:1); `terminos_identificados` **`ARRAY(String)`** nullable; `especialidad_sugerida` String(100); `nivel_urgencia` String(20) (`urgente`/`prioritario`/`programable`); `confianza_modelo` `Numeric(5,4)` |

#### Schemas Pydantic
- `ChatRequest { mensaje: str, conversacion_id?: UUID, usuario_id?: UUID }` y `ChatResponse { respuesta, conversacion_id, clasificacion? }` — contratos principales del frontend.
- `ConversacionCreate/Response`, `MensajeCreate/Response` (remitente `Literal["usuario","asistente"]`), `ClasificacionSintomasBase/Response` (`nivel_urgencia: Literal[...]`, `confianza_modelo: float` con `ge=0.0, le=1.0`).

### 2.6 notifications-service

Archivo: `services/notifications-service/app/models.py`.

#### Entidad `Notificacion` → tabla `notificaciones`
- `notif_id` UUID PK (`gen_random_uuid()`, listener `set_sqlite_uuid_defaults` para otros dialectos); `medico_id` UUID NOT NULL (**sin FK**, referencia lógica al Catalog Service); `tipo` String(50); `titulo` String(255); `descripcion` Text; `leida` Boolean default `false`; `enlace` String(500) nullable; `creado_en`.

#### Schemas Pydantic (`app/schemas.py`)
- `NotificacionCreate { medico_id, tipo, titulo, descripcion, enlace? }`
- `NotificacionResponse` (agrega `notif_id`, `leida`, `creado_en`; `from_attributes=True`)
- `MessageResponse { message, success=True }`; `TestEmailRequest { email: EmailStr }` definido en `main.py`.

### 2.7 Migraciones (Alembic y scripts SQL)

Todos los servicios tienen `alembic.ini` + `alembic/env.py` + una revisión inicial en `alembic/versions/`:

| Servicio | Revisión inicial | Tablas creadas |
|---|---|---|
| auth-service | `8d4bf71cb2a4_initial.py` | `credenciales`, `log_autenticacion`, `registro_2fa`, `token_recuperacion` |
| user-service | `dabf49b70012_initial.py` | `usuarios`, `afiliaciones`, `informacion_medica` |
| appointments-service | `9c0f4450dd12_initial.py` | `citas`, `historial_estado`, `recordatorios` |
| catalog-service | `4ff952acbd99_initial.py` | `medicos`, `sedes`, `servicios`, `especialidades`, `disponibilidades`, `medico_especialidades` |
| ai-nlp-service | `aebd3ba94d80_initial.py` | `conversacion`, `clasificacion_sintomas`, `mensaje` |
| notifications-service | `bfdf8aed1c48_initial.py` | `notificaciones` |

Patrones de aplicación:
1. **Docker Compose**: cada servicio arranca con `sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 80XX"`.
2. **Doble red de seguridad**: el `lifespan` de cada FastAPI ejecuta además `Base.metadata.create_all(bind=engine)`.
3. **SQL manual complementario**:
   - `appointments-service/migrations/001_create_initial_tables.sql`: DDL idempotente (`CREATE TABLE IF NOT EXISTS`...) aplicable con `scripts/run_migrations.sh` (itera `*.sql` y ejecuta `psql "$DATABASE_URL" -f`).
   - `catalog-service/migrations/001_add_usuario_id_to_medicos.sql`: `ALTER TABLE medicos ADD COLUMN IF NOT EXISTS usuario_id UUID` (columna presente solo en SQL; el modelo ORM actual de `Medico` no la declara).
   - `auth-service/migrations/` existe pero está vacía (quedó obsoleta frente a Alembic); incluye `auth_dev.db` SQLite para desarrollo local.

> **Regla del repo (AGENTS.md)**: todo cambio de modelo requiere nueva migración en `alembic/versions/` antes de desplegar.

---

## 3. Endpoints y Capa de Servicios

Convención transversal: CORS habilitado para `https://eps-digital-cn2h.onrender.com` y `http://localhost:5173` (+ regex `https://.*\.onrender\.com`); errores de negocio mapeados de `ValueError` a HTTP 400/401/404/503.

### 3.1 auth-service (`app/main.py`, puerto 8001)

| Método | Ruta | Request → Response | Notas |
|---|---|---|---|
| POST | `/auth/register` | `UserRegister` → `RegisterResponse` | Llama `registrar_usuario` y publica evento RabbitMQ `cuenta_creada` |
| POST | `/auth/login` | `UserLogin` → `LoginResponse` | Si `tiene_2fa` retorna tokens vacíos + `requiere_2fa=True` |
| POST | `/auth/login/documento` | `UserLoginDocumento` → `LoginResponse` | Resuelve correo vía User Service (`get_correo_by_documento`); 404→401, caída→503 |
| POST | `/auth/refresh` | `RefreshTokenRequest` → `TokenResponse` | Valida tipo `refresh` y que la credencial esté activa |
| POST | `/auth/verify-2fa` | `Verify2FARequest` → dict tokens + `rol` | Emite par access/refresh tras OTP válido |
| POST | `/auth/enable-2fa` | `Enable2FARequest` (Bearer) → `MessageResponse` | Verifica OTP y activa flag con `configurar_2fa` |
| POST | `/auth/recover` | `RecoverRequest` → `MessageResponse` | Respuesta neutra (no revela existencia del correo) |
| POST | `/auth/reset-password` | `ResetPasswordRequest` → `MessageResponse` | Compara contraseñas y consume token |
| GET | `/auth/me` | Bearer → dict | `credencial_id`, `correo`, `rol`, `activo`, `tiene_2fa` |
| GET | `/auth/perfil` | Bearer → dict | `{usuario_id, rol}` |
| GET | `/auth/medico-id` | Bearer → dict | `{medico_id}`; 404 si no hay médico asociado |

**Lógica de negocio (`app/auth.py`)** — constantes: `BCRYPT_ROUNDS=12`, `JWT_ALGORITHM="HS256"` (python-jose), `ACCESS_TOKEN_EXPIRE_MINUTES=30`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `RECOVERY_TOKEN_EXPIRE_MINUTES=30`, `TWO_FA_CODE_EXPIRE_MINUTES=10`, `MAX_INTENTOS_FALLIDOS=5`, `BLOQUEO_MINUTES=15`, `USER_SERVICE_TIMEOUT_SECONDS=5.0`. Secret leído de `JWT_SECRET_KEY` (`_get_jwt_secret_key`).
Funciones principales:
- **Hashing**: `hash_password` (bcrypt, límite 72 bytes), `verify_password`, `_sha256_hex` (para tokens/OTP temporales).
- **JWT**: `create_jwt_token` (claims `sub`, `iat`, `exp`, `tipo`), `create_access_token`, `create_refresh_token`, `verify_jwt_token(token, expected_tipo)`, `refresh_access_token`.
- **Login**: `autenticar_usuario` aplica bloqueo temporal tras >5 intentos (`verificar_bloqueo`), resetea contadores al éxito y registra `log_evento` en auditoría; `generar_tokens_para_credencial`.
- **Registro**: `registrar_usuario` valida unicidad de correo (normalizado a minúsculas) y audita `registro_exitoso`.
- **Recuperación**: `crear_token_recuperacion` (guarda solo SHA256), `resetear_password` (valida no usado/no expirado, desbloquea cuenta).
- **2FA**: `generar_codigo_2fa` (OTP 6 dígitos hasheado), `verificar_codigo_2fa` (marca `usado`, audita resultado), `configurar_2fa`.
- **Inter-servicio**: `get_correo_by_documento` hace `httpx.get(f"{USER_SERVICE_URL}/usuarios/buscar")`; excepciones de dominio `DocumentoNoEncontradoError` y `UserServiceUnavailableError`.

### 3.2 user-service (`app/main.py`, puerto 8002)

| Método | Ruta | Request → Response |
|---|---|---|
| POST | `/usuarios` | `UserCreate` → `UserResponse` (201) |
| GET | `/usuarios/buscar?tipo_documento&numero_documento` | Query params → `UserLookupResponse` (consumido por Auth Service) |
| GET | `/usuarios/{usuario_id}` | → `UserResponse` |
| PUT | `/usuarios/{usuario_id}` | `UserUpdate` → `UserResponse` (parcial; el frontend usa PUT, no PATCH) |
| DELETE | `/usuarios/{usuario_id}` | → `MessageResponse` (hard delete) |
| GET | `/usuarios/{usuario_id}/medica` | → `MedicalInfoResponse \| None` |
| PUT | `/usuarios/{usuario_id}/medica` | `MedicalInfoCreate` → upsert `MedicalInfoResponse` |
| GET | `/usuarios/{usuario_id}/afiliacion` | → `AfiliacionResponse \| None` |
| POST | `/usuarios/{usuario_id}/afiliacion` | `AfiliacionCreate` → 201 |
| PATCH | `/usuarios/{usuario_id}/afiliacion/estado` | `EstadoAfiliacionUpdate` → `AfiliacionResponse` |
| GET | `/usuarios/{usuario_id}/completo` | → `UsuarioCompletoResponse` |

**CRUD (`app/crud.py`)**: `get_user_by_id`, `get_user_by_documento`, `get_user_by_tipo_y_numero_documento`, `get_user_by_correo`, `create_user` (valida duplicados de id/documento/correo), `update_user` (`exclude_unset` + verificación de unicidad ajena al propio usuario), `delete_user` (hard delete; el cascade borra info médica y afiliación), `get_medical_info`, `create_or_update_medical_info` (upsert), `get_afiliacion`, `create_afiliacion` (rechaza duplicada), `update_afiliacion_estado`. Helper `_status_from_value_error` convierte mensajes "no existe" en HTTP 404.

### 3.3 appointments-service (`app/main.py`, puerto 8003)

Autenticación ligera: header `X-User-ID` parseado por `_parse_user_id_header` (no valida JWT internamente).

| Método | Ruta | Request → Response |
|---|---|---|
| POST | `/citas` | `CitaCreate` → `CitaResponse` |
| GET | `/citas/usuario/{usuario_id}?skip&limit` | → `list[CitaResponse]` |
| GET | `/citas/usuario/{usuario_id}/historial` | → citas con estado ≠ `programada` |
| GET | `/citas/medico/{medico_id}?fecha\|fecha_inicio&fecha_fin` | → agenda del médico |
| GET | `/citas/estado/{estado}` | → `list[CitaResponse]` (valida dominio) |
| GET | `/citas/{cita_id}` | → `CitaResponse` |
| PUT | `/citas/{cita_id}` | `CitaUpdate` → `CitaResponse` |
| POST | `/citas/{cita_id}/cancelar` | `CancelarCitaRequest` + `X-User-ID` → `CitaResponse` |
| POST | `/citas/{cita_id}/reprogramar` | `ReprogramarCitaRequest` + `X-User-ID` → `CitaResponse` |
| DELETE | `/citas/{cita_id}` | → `MessageResponse` |
| GET | `/citas/{cita_id}/historial` | → `list[HistorialEstadoResponse]` |
| POST | `/citas/{cita_id}/recordatorio` | programa recordatorio automático a `fecha_cita + hora_inicio − 24 h` |
| GET | `/recordatorios/pendientes` | → `list[RecordatorioResponse]` |
| GET | `/citas/metricas?dias=7` (tag admin) | métricas agregadas |
| GET | `/citas/medico/{medico_id}/metricas` (tag medico) | dashboard del médico |

**CRUD (`app/crud.py`)** — constante `CATALOG_SERVICE_URL` (default `http://localhost:8004`) y mapa `TIPO_SERVICIO_A_SERVICIO` (`medicina_general→"Medicina General"`, `especialista→"Medicina Especializada"`, `urgencias→"Urgencias"`, `laboratorio→"Laboratorio"`):
- `_obtener_medico_automatico(tipo_servicio, especialidad_id, fecha, hora_inicio, hora_fin)`: consulta `GET /servicios?solo_activos=true` y `GET /medicos/disponibles` del Catálogo y toma el **primer médico disponible** (round-robin simplificado); permite crear citas sin `medico_id`.
- `es_horario_ocupado(...)`: detección de solapamiento `Cita.hora_inicio < hora_fin AND Cita.hora_fin > hora_inicio` filtrando `estado == "programada"`, con `excluir_cita_id` para updates/reprogramaciones.
- `create_cita` (auto-asigna médico + valida disponibilidad), `update_cita` (revalida horario; registra historial si cambia `estado`), `cancelar_cita` (solo desde `programada`), `reprogramar_cita` (devuelve la cita a `programada`, motivo `"Reprogramacion de cita"`), `add_historial_estado`, `get_historial_by_cita`, `create_recordatorio`, `get_recordatorios_pendientes`, `marcar_recordatorio_enviado`.
- Métricas: `get_metricas_citas(db, dias)` → `{total_hoy, total_semana, tasa_cancelacion, canceladas, por_dia[], top_especialidades[], top_medicos[]}`; `get_metricas_medico(db, medico_id)` → `{citas_hoy, proximas_7_dias, atendidas_mes, tiempo_espera_promedio_min, tasa_asistencia_pct, ingresos_mes}`.

### 3.4 catalog-service (`app/main.py`, puerto 8004)

Import dinámico (`import_module`) para soportar ejecución con cwd `app/`.

| Grupo | Endpoints |
|---|---|
| **Servicios** | `POST /servicios` (201), `GET /servicios?skip&limit&solo_activos`, `GET /servicios/{id}`, `PUT /servicios/{id}`, `DELETE /servicios/{id}` (borrado lógico → `{"success": true}`) |
| **Especialidades** | `POST /especialidades` (201), `GET /especialidades?servicio_id&solo_activos`, `GET /especialidades/{id}`, `PUT /especialidades/{id}`, `DELETE /especialidades/{id}` |
| **Médicos** | `POST /medicos` (201), `GET /medicos`, `GET /medicos/disponibles?servicio_id&especialidad_id&fecha&hora_inicio&hora_fin`, `GET /medicos/registro/{numero_registro}`, `GET /medicos/{id}`, `PUT /medicos/{id}`, `DELETE /medicos/{id}`, `GET /medicos/con-especialidades` (médicos con especialidades anidadas) |
| **Médico–Especialidad** | `POST /medicos/{medico_id}/especialidades/{especialidad_id}?es_principal` (201), `DELETE /medico-especialidades/{medico_especialidad_id}`, `GET /medicos/{medico_id}/especialidades`, `GET /especialidades/{especialidad_id}/medicos` ← endpoint usado por el asistente IA |
| **Sedes** | `POST /sedes` (201), `GET /sedes?solo_activas`, `GET /sedes/{id}`, `PUT /sedes/{id}`, `DELETE /sedes/{id}` |
| **Disponibilidad** | `POST /disponibilidades` (201), `GET /disponibilidades/medico/{medico_id}?dia_semana`, `GET /disponibilidades/{id}`, `PUT /disponibilidades/{id}`, `DELETE /disponibilidades/{id}`, `GET /disponibilidades/verificar?medico_id&fecha&hora_inicio&hora_fin` → `{"disponible": bool}` |

**CRUD (`app/crud.py`)**: helpers `_apply_updates` y `_ensure_exists`; operaciones completas por entidad (`create_/get_/update_/delete_servicio|especialidad|medico|sede|disponibilidad`, todas las eliminaciones son **lógicas** salvo `remove_especialidad_from_medico`). Lógica destacada:
- `assign_especialidad_to_medico`: garantiza unicidad y gestiona el flag `es_principal` (desactiva los demás cuando se marca uno nuevo).
- `create_disponibilidad` / `update_disponibilidad`: rechazan cruces de horario por médico/día (`hora_inicio < hora_fin_existente AND hora_fin > hora_inicio_existente`).
- `verificar_disponibilidad(medico_id, fecha, hora_inicio, hora_fin)`: busca franja activa cuyo rango **contenga** el solicitado usando `fecha.isoweekday()`.
- `get_medicos_disponibles(...)`: JOIN `Medico↔MedicoEspecialidad↔Especialidad` con subconsulta de especialidades activas; si llega fecha+horas filtra en memoria con `verificar_disponibilidad`.
- `get_medicos_con_especialidades`: respuesta denormalizada (dicts) con `especialidades[]` anidadas.

### 3.5 ai-nlp-service (`app/main.py`, puerto 8005)

| Método | Ruta | Request → Response |
|---|---|---|
| POST | `/chat` | `ChatRequest` → `ChatResponse` |
| GET | `/chat/conversaciones/{usuario_id}` | → `list[ConversacionResponse]` (últimas 50) |
| GET | `/chat/conversacion/{conversacion_id}/mensajes` | → `list[MensajeResponse]` |
| POST | `/chat/conversacion/{conversacion_id}/cerrar` | → `ConversacionResponse` (estado `cerrada`) |
| GET | `/chat/clasificacion/{conversacion_id}` | → `ClasificacionSintomasResponse \| None` |

**Flujo de `post_chat`** (orquestador principal):
1. Crea conversación (si no viene `conversacion_id`; `usuario_id` por defecto UUID cero) o valida la existente.
2. Persiste mensaje del usuario (`crear_mensaje`, remitente `"usuario"`).
3. Construye historial con los últimos 6 mensajes (`get_mensajes_by_conversacion(limit=6)`) mapeados por `_mapear_historial_a_mensajes_llm` (remitentes `usuario/asistente` → roles `user/assistant`).
4. Inserta mensaje system con el `usuario_id` autenticado para que las tools lo usen.
5. `chat_completion(messages, tools=get_assistant_tools())`; si hay `tool_calls`, itera: `ejecutar_funcion(nombre, args)` → agrega mensajes `assistant.tool_calls` + `role:"tool"` → segunda llamada `chat_completion(messages, tools=None)` para redactar la respuesta final.
6. Guarda respuesta del asistente y, si `_es_mensaje_relevante_para_clasificacion` detecta palabras clave (`dolor`, `fiebre`, `tos`, `sangrado`, ...), llama `clasificar_sintomas` y hace **upsert** 1:1 de la clasificación.

**Driver Groq (`app/groq_client.py`)**:
- Constantes: `GROQ_MODEL = "llama-3.3-70b-versatile"`, `REQUEST_TIMEOUT_SECONDS = 30.0`, `CITAS_TIMEOUT_SECONDS = 10.0`; cliente global `_groq_client` inicializado por `configurar_groq()` con `GROQ_API_KEY`.
- `chat_completion(messages, tools=None)`: `max_tokens=400`, `tool_choice="auto"` cuando hay tools; retorna `(content, tool_calls[{id,name,arguments}])`.
- `clasificar_sintomas(texto)`: `temperature=0` + `response_format={"type":"json_object"}`; parseo tolerante con `_parsear_json_con_rescate` (extrae el objeto aunque venga con texto extra) y normalización defensiva `_normalizar_clasificacion` (fallback `_clasificacion_por_defecto` con nivel `programable`).
- `ejecutar_funcion(tool_name, arguments)`: dispatcher de tools — `obtener_disponibilidad_citas` es **simulada** (cupos fijos `["09:00","10:30","14:00"]`); `obtener_especialidades`, `obtener_medicos`, `obtener_sedes` consultan el **Catalog Service real** vía `_consultar_catalog_service` (`CATALOG_SERVICE_URL` + endpoints `/especialidades`, `/especialidades/{id}/medicos`, `/sedes`); `agendar_cita` exige `confirmado=True` y campos completos antes de llamar `_agendar_cita_en_citas_service` → `POST {CITAS_SERVICE_URL}/citas` con header `X-User-ID` y `hora_fin` calculada con `_sumar_minutos_a_hora(hora_inicio, 30)` (citas de 30 min). Todos los errores se traducen a mensajes naturales en español para el usuario final.

**Prompts (`app/prompts.py`)**:
- `SYSTEM_PROMPT`: rol de asistente médico de EPS colombiana (sin diagnóstico), niveles de urgencia (`urgente/prioritario/programable`), guía paso a paso del flujo de agendamiento (una pregunta a la vez, nunca inventar UUIDs, confirmar antes de `agendar_cita`, no revelar IDs técnicos), salida en Markdown ≤ 600 caracteres y lista de especialidades habilitadas.
- `CLASIFICACION_PROMPT`: fuerza un JSON exacto `{terminos_identificados[], especialidad_sugerida, nivel_urgencia, confianza, explicacion}`.
- `ASSISTANT_TOOLS`: definición OpenAI-style de 5 funciones (`obtener_disponibilidad_citas`, `agendar_cita`, `obtener_especialidades`, `obtener_medicos`, `obtener_sedes`); `get_assistant_tools()` las expone. Constante `MODEL_NAME = "gpt-4o-mini"` queda como referencia histórica (el runtime usa Groq).

**CRUD (`app/crud.py`)**: `crear_conversacion`, `get_conversacion`, `get_conversaciones_by_usuario`, `cerrar_conversacion`, `crear_mensaje`, `get_mensajes_by_conversacion`, `crear_clasificacion` (convierte `confianza_modelo` a `Decimal`), `get_clasificacion_by_conversacion`.

### 3.6 notifications-service (`app/main.py`, puerto 8006)

| Método | Ruta | Request → Response |
|---|---|---|
| GET | `/health` | verifica conexión RabbitMQ → `{"status": "ok", "rabbitmq": "connected\|disconnected"}` |
| GET | `/stats` | snapshot thread-safe de `_email_stats` (`emails_enviados`, `emails_fallidos`, `ultima_fecha_envio`, `ultimo_error`) protegido por `_stats_lock` |
| POST | `/test-email` | `TestEmailRequest` → `MessageResponse` (envía plantilla `bienvenida`) |
| POST | `/notificaciones` | `NotificacionCreate` → `NotificacionResponse` (notificación in-app para un médico) |
| GET | `/notificaciones/medico/{medico_id}` | últimas 50 ordenadas por `creado_en desc` |
| PATCH | `/notificaciones/{notif_id}/leida` | marca individual → `MessageResponse` |
| PATCH | `/notificaciones/medico/{medico_id}/leer-todas` | `UPDATE ... WHERE leida == False` masivo |

**Componentes de soporte**:
- `app/email_client.py`: `configurar_sendgrid()` (cliente global con `SENDGRID_API_KEY`, timeout 30 s) y `enviar_correo(destinatario, asunto, contenido_html) -> bool` usando `sendgrid.helpers.mail.Mail`; remitente desde `SENDGRID_FROM_EMAIL` o `EMAIL_FROM`.
- `app/templates.py`: layout HTML institucional (`_layout_email`, color `COLOR_AZUL_MARINO="#2B3E59"`, escape con `html.escape`) y plantillas `bienvenida(nombre)`, `confirmacion_cita(nombre, fecha, hora, especialidad, sede)`, `cancelacion_cita(...)`, `recordatorio_cita(...)` y `recuperacion_password(nombre, token, link_base)` (esta última aún no integrada al consumer).
- `app/consumer.py`: ver sección 4.

---

## 4. Comunicación Inter-Servicios y Asíncrona

### 4.1 Comunicación síncrona REST/HTTP

```
┌──────────────┐  GET /usuarios/buscar (httpx, timeout 5s)   ┌─────────────┐
│ auth-service │ ───────────────────────────────────────────►│ user-service│
└──────────────┘                                             └─────────────┘
┌────────────────────┐ GET /servicios + /medicos/disponibles ┌──────────────┐
│ appointments-svc   │ ─────────────────────────────────────►│ catalog-svc  │
│ (crud._obtener_    │                                       └──────────────┘
│  medico_automatico)│        ▲
└────────────────────┘        │ POST {CITAS_SERVICE_URL}/citas (header X-User-ID,
                              │ hora_fin = hora + 30 min)
                   ┌──────────┴───────┐  GET /especialidades            ┌──────────────┐
                   │ ai-nlp-service   │────────────────────────────────►│ catalog-svc  │
                   │ (groq_client)    │  GET /especialidades/{id}/medicos
                   └──────────────────┘  GET /sedes                    └──────────────┘
```

| Origen | Destino | Endpoint consumido | Función responsable |
|---|---|---|---|
| auth-service | user-service | `GET {USER_SERVICE_URL}/usuarios/buscar?tipo_documento&numero_documento` | `auth.get_correo_by_documento` |
| appointments-service | catalog-service | `GET {CATALOG_SERVICE_URL}/servicios?solo_activos=true` y `GET {CATALOG_SERVICE_URL}/medicos/disponibles` | `crud._obtener_medico_automatico` |
| ai-nlp-service | catalog-service | `GET /especialidades`, `GET /especialidades/{especialidad_id}/medicos`, `GET /sedes` | `groq_client._consultar_catalog_service` |
| ai-nlp-service | appointments-service | `POST {CITAS_SERVICE_URL}/citas` (+ `X-User-ID`) | `groq_client._agendar_cita_en_citas_service` |

El frontend (React/Vite) consume directamente todos los servicios REST con CORS abierto hacia `localhost:5173` y `*.onrender.com`.

### 4.2 Mensajería asíncrona (RabbitMQ)

**Broker**: CloudAMQP (`RABBITMQ_URL`, amqps) o RabbitMQ local del compose de notifications (`rabbitmq:3.12-management-alpine`, guest/guest, puertos 5672/15672). Mensajes JSON persistentes (`delivery_mode=2`), colas durables, exchange por defecto (`""`) con `routing_key = nombre_del_evento`.

**Productor — auth-service** (`app/rabbitmq_client.py`):
- `publicar_evento(evento, payload)`: abre conexión por publicación (`heartbeat=30`, `blocked_connection_timeout=30`), hace `queue_declare(queue=evento, durable=True)` y publica. Errores solo se loguean (nunca rompen el request).
- Evento emitido: **`cuenta_creada`** en `POST /auth/register`, payload `{"evento": "cuenta_creada", "email": ..., "nombre": ...}`.

**Consumidor — notifications-service** (`app/consumer.py`):
- Constante `COLAS_EVENTOS = ("cita_confirmada", "cita_cancelada", "cita_recordatorio", "cuenta_creada")` — declara y consume las 4 colas durables con `auto_ack=False`.
- `callback(ch, method, properties, body)`: determina el tipo de evento por `payload.evento` (o `payload.tipo_evento`, fallback `routing_key`); obtiene destinatario de `payload.email` (o `payload.destinatario`); enruta a la plantilla correspondiente:

| Evento (routing key) | Asunto | Plantilla (`templates.py`) |
|---|---|---|
| `cita_confirmada` | Confirmación de cita – EPS Digital | `confirmacion_cita(nombre, fecha, hora, especialidad, sede)` |
| `cita_cancelada` | Cancelación de cita – EPS Digital | `cancelacion_cita(nombre, fecha, hora, especialidad)` |
| `cita_recordatorio` | Recordatorio de cita – EPS Digital | `recordatorio_cita(nombre, fecha, hora, especialidad, sede)` |
| `cita_creada` → `cuenta_creada` | Bienvenido a EPS Digital | `bienvenida(nombre)` |

- Envío vía SendGrid (`enviar_correo`); **siempre** hace `basic_ack` en `finally` (los mensajes no se reprocesan aunque falle el correo); eventos desconocidos o sin email se descartan con ack y log.
- `iniciar_consumidor()`: bucle infinito con reconexión automática (sleep 5 s ante `AMQPConnectionError` / `ChannelClosedByBroker`); `start_background_consumer()` lo levanta como **thread daemon** desde el `lifespan` de FastAPI, junto con `configurar_sendgrid()`.
- Configuración de conexión: `heartbeat=30`, `blocked_connection_timeout=30`, `socket_timeout=30`, `connection_attempts=3`, `retry_delay=3`.

### 4.3 Variables de entorno por servicio

| Variable | Servicios que la usan | Propósito |
|---|---|---|
| `DATABASE_URL` | todos | Cadena PostgreSQL (ej. `postgresql://eps_user:eps_password@<db-host>:5432/<bd>`) |
| `JWT_SECRET_KEY` | auth (y presentes en compose de user/citas/catalog/ainlp) | Firma HS256 de tokens |
| `USER_SERVICE_URL` | auth | Login por documento |
| `CATALOG_SERVICE_URL` | appointments, ai-nlp | Médicos disponibles, especialidades, sedes |
| `CITAS_SERVICE_URL` | ai-nlp | Agendado real de citas |
| `GROQ_API_KEY` | ai-nlp | Cliente LLM |
| `RABBITMQ_URL` | auth (productor), notifications (consumer + `/health`) | Broker AMQP |
| `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` / `EMAIL_FROM` | notifications | Envío de correos |

---

## 5. Observaciones de Arquitectura (hallazgos del análisis)

1. **Inconsistencia potencial en métricas**: `appointments-service/app/crud.py::get_metricas_citas` accede a `c.especialidad_nombre` y `c.medico_nombre`, atributos que **no existen** en el modelo `Cita` (solo hay `*_id`); `GET /citas/metricas` fallaría con `AttributeError` hasta que se resuelvan esos nombres vía catálogo.
2. **Referencias cruzadas sin FK intencionales**: `credenciales.usuario_id`, `credenciales.medico_id`, `citas.usuario_id/medico_id/especialidad_id/sede_id`, `afiliaciones.medico_asignado_id` y `notificaciones.medico_id` son referencias lógicas entre bases — la integridad se delega a la capa de aplicación.
3. **Columna huérfana en catálogo**: la migración SQL `001_add_usuario_id_to_medicos.sql` agrega `medicos.usuario_id`, pero el modelo ORM `Medico` no la declara (vinculación prevista médico↔auth no materializada en código).
4. **Eventos sin publicador visible**: `cita_confirmada`, `cita_cancelada` y `cita_recordatorio` se consumen, pero ningún servicio del backend las publica actualmente (el frontend u otro actor debería emitirlas; los recordatorios persistidos en `recordatorios` tampoco disparan la publicación).
5. **Credenciales por defecto en código**: `RABBITMQ_DEFAULT_URL` está hardcodeada (con credenciales CloudAMQP) tanto en `auth-service/app/rabbitmq_client.py` como en `notifications-service/app/consumer.py`; conviene rotar y depender solo de `RABBITMQ_URL`.
6. **Doble estrategia de esquema**: coexisten `Base.metadata.create_all` en el lifespan y Alembic (`alembic upgrade head` en el start command); para producción debe primar Alembic según AGENTS.md.
7. **`max_tokens` del chat**: el código actual de `groq_client.chat_completion` usa `max_tokens=400` (AGENTS.md menciona 800 para tool calls).
8. **Notificaciones in-app vs. email**: `Notificacion` (BD) atiende al rol médico (bandeja + marcar leídas), mientras el consumer atiende correos al paciente; son flujos independientes dentro del mismo servicio.
