# E2E Integration Context — EPS Digital

> **Mapa de carreteras definitivo** de la integración Frontend → Microservicios → Bases de Datos.
> Elaborado leyendo directamente `frontend/src/` y `services/`. Complementa a `backend_context.md` y `frontend_context.md`.
>
> Leyenda de estado: ✅ integración completa · ⚠ desacople o endpoint faltante · 🔶 parcial / WIP.

---

## 0. Vista General del Sistema

```
                          ┌──────────────────────────────────────────────────┐
                          │        FRONTEND (React 18 + Vite, :5173)         │
                          │  apiClient.ts → 6 instancias Axios (puertos      │
                          │  8001–8006) + authStore (Zustand/localStorage)   │
                          └───┬──────┬──────┬──────┬──────┬──────┬───────────┘
                              │8001  │8002  │8003  │8004  │8005  │8006
        ┌─────────────────────▼┐ ┌───▼────┐ ┌▼────────────┐ ┌▼──────────┐ ┌▼──────────────────┐
        │ auth-service   :8001 │ │ user-  │ │ appointments│ │ catalog-  │ │ notifications:8006│
        │ JWT/2FA/bloqueos     │ │service │ │ -service    │ │ service   │ │ SendGrid + Rabbit │
        │ (eps_auth)           │ │ :8002  │ │ :8003       │ │ :8004     │ │ consumer (:8006)  │
        └─────────┬────────────┘ │(eps_   │ │ (eps_citas) │ │(eps_      │ └────────┬──────────┘
                  │ REST httpx   │ user)  │ │             │ │ catalogo) │          │ AMQP consume
                  ▼              └───┬────┘ └──────┬──────┘ └────┬──────┘          ▼
        ┌──────────────┐             │             │REST httpx   │REST httpx   ┌────────────┐
        │ user-service │             ▼             ▼             ▼             │ RabbitMQ   │
        │ GET /usuarios│        ┌────────┐   ┌─────────┐   ┌──────────┐       │ (CloudAMQP)│
        │ /buscar      │        │Postgres│   │Postgres │   │ Postgres │       │ 4 colas    │
        └──────────────┘        └────────┘   └─────────┘   └──────────┘       └─────┬──────┘
                                                                                    │ emails
        ai-nlp-service :8005 (eps_ainlp) ──► Groq Cloud API (llama-3.3-70b)         ▼
        ├──► catalog-service (/especialidades, /medicos, /sedes)               SendGrid API
        └──► appointments-service (POST /citas)
```

Reglas transversales de la integración:
- **Autenticación**: el frontend envía `Authorization: Bearer <JWT>` **y** el header `X-User-ID` en cada cliente autenticado (`apiClient.ts`). Solo `appointments-service` consume `X-User-ID`; ningún servicio valida aún el JWT en requests del frontend.
- **CORS**: todos los backends permiten `http://localhost:5173` y `https://eps-digital-cn2h.onrender.com` (+ regex `https://.*\.onrender\.com`).
- **Errores**: los servicios traducen `ValueError` de negocio a HTTP 400/401/404; el frontend lee `response.data.detail`.

---

## 1. Mapeo de Rutas Front vs Endpoint Backend

Tabla maestra: `Página/Componente Frontend` → `Acción/Frontend (función)` → `Endpoint HTTP / Puerto` → `Función CRUD backend / Tabla BD impactada`.

### 1.1 Autenticación y Registro — auth-service (`:8001`, BD `eps_auth`)

| Página Front | Acción Front | Endpoint / Puerto | Backend → Tabla BD |
|---|---|---|---|
| `LoginPage.tsx` | `authApi.login({tipo_documento, numero_documento, password})` | `POST :8001/auth/login/documento` | `get_correo_by_documento` → **httpx** `GET :8002/usuarios/buscar` (tabla `usuarios`) → `autenticar_usuario()` (SELECT `credenciales`, UPDATE `intentos_fallidos`/`bloqueado_hasta`) + INSERT `log_autenticacion` → `generar_tokens_para_credencial()` (JWT HS256) |
| `MedicoLoginPage.tsx` | mismo `authApi.login` + guarda `rol` con `setRol()` | `POST :8001/auth/login/documento` | Ídem anterior; `LoginResponse.rol` decide navegación `/medico/dashboard` vs `/` |
| `RegisterPage.tsx` (paso 1) | `authApi.register(payload)` | `POST :8001/auth/register` | `registrar_usuario()` → INSERT `credenciales` (hash bcrypt rounds=12) + INSERT `log_autenticacion`(`registro_exitoso`) → luego `publicar_evento("cuenta_creada", {email, nombre})` a RabbitMQ (cola durable `cuenta_creada`) ✅ |
| `RegisterPage.tsx` (paso 2) | `userApi.create({usuario_id, ...perfil})` | `POST :8002/usuarios` | `crud.create_user()` → SELECT anti-duplicados + INSERT tabla `usuarios` (BD `eps_user`) ✅ patrón *distributed registration* |
| — (sin UI aún 🔶) | — | `POST :8001/auth/login`, `verify-2fa`, `enable-2fa`, `recover`, `reset-password`, `refresh` | `generar_codigo_2fa`/INSERT `registro_2fa`; `crear_token_recuperacion`/INSERT `token_recuperacion`; `resetear_password`/UPDATE `credenciales.password_hash` |
| `MedicoDashboardPage`, `MedicoCitasPage` | `authApi.getMedicoId()` | `GET :8001/auth/medico-id` (Bearer) | `verify_jwt_token` → SELECT `credenciales.medico_id` |

### 1.2 Perfil de Usuario — user-service (`:8002`, BD `eps_user`)

| Página Front | Acción Front | Endpoint / Puerto | Backend → Tabla BD |
|---|---|---|---|
| `LoginPage` / `MedicoLoginPage` | `userApi.getById(usuario_id)` → `setUser()` | `GET :8002/usuarios/{id}` | `crud.get_user_by_id()` → SELECT `usuarios` |
| `ProfilePage.tsx` | `userApi.getCompleto(userId)` (`useQuery ['user-completo']`) | `GET :8002/usuarios/{id}/completo` | 3 SELECTs: `usuarios` + `informacion_medica` + `afiliaciones` → `UsuarioCompletoResponse` |
| `ProfilePage.tsx` (modal edición) | `userApi.update(userId, editData)` (**PUT**) | `PUT :8002/usuarios/{id}` | `crud.update_user()` (`exclude_unset`) + validación unicidad correo/documento → UPDATE `usuarios`; al éxito front hace `setUser(res.data)` |
| HomePage / Navbar | lectura de `useAuthStore().user` | *(sin HTTP extra)* | — |
| Admin pages 🔶 | `authApi.getAdmins/createAdmin/deleteAdmin` | **no existen** ⚠ | Sin implementación backend ni tabla asociada |

### 1.3 Citas — appointments-service (`:8003`, BD `eps_citas`)

| Página Front | Acción Front | Endpoint / Puerto | Backend → Tabla BD |
|---|---|---|---|
| **AgendarCitaPage** | `citasApi.create({...})` (mutation) | `POST :8003/citas` | `create_cita()`: si no hay `medico_id` → `_obtener_medico_automatico()` (**httpx** `GET :8004/servicios` + `GET :8004/medicos/disponibles`, tablas `servicios`/`disponibilidades`/`medico_especialidades` de `eps_catalogo`) → `es_horario_ocupado()` (SELECT solapamiento en `citas`) → INSERT `citas` |
| **VerCitasPage** | `citasApi.getByUser(userId)` (`['citas', userId]`) | `GET :8003/citas/usuario/{id}` | `get_citas_by_usuario()` → SELECT `citas WHERE usuario_id` ORDER BY fecha/hora (paginación skip/limit) |
| **HistorialCitasPage** | `citasApi.getHistorial(userId)` | `GET :8003/citas/usuario/{id}/historial` | `get_citas_historicas_by_usuario()` → SELECT `citas WHERE estado != 'programada'` |
| **CancelarCitaPage** | `citasApi.cancel(citaId, motivo)` | `POST :8003/citas/{cita_id}/cancelar` (+ header `X-User-ID`) | `_parse_user_id_header` → `cancelar_cita()`: valida estado `'programada'` → UPDATE `citas.estado='cancelada'` → `add_historial_estado()` INSERT `historial_estado` |
| **HomePage** | `citasApi.getByUser` para "próxima cita" | `GET :8003/citas/usuario/{id}` | Ídem VerCitasPage |
| MedicoDashboardPage | `citasApi.getCitasMedico(medicoId, {fecha_inicio, fecha_fin})` | `GET :8003/citas/medico/{id}?fecha_inicio&fecha_fin` | `get_citas_by_medico()` → SELECT `citas WHERE medico_id` filtrado por rango |
| MedicoCitasPage | `getCitasMedico(medicoId, {fecha})` y `updateEstado(id, estado)` | `GET ...?fecha=` y **`PATCH :8003/citas/{cita_id}/estado`** ⚠ | El GET existe (`get_citas_by_medico(fecha=...)`). **El PATCH no existe en el backend** — solo hay `PUT /citas/{cita_id}` (`update_cita`). La acción Atendida/No asistió fallará con 405 |
| AgendarCitaPage (post-create) | invalidación `['citas']`, navigate `/citas/ver` | — | — |
| — (sin UI 🔶) | — | `PUT /citas/{id}`, `DELETE /citas/{id}`, `POST /citas/{id}/reprogramar`, `GET /citas/{id}/historial`, `POST /citas/{id}/recordatorio`, `GET /recordatorios/pendientes`, `GET /citas/metricas` | `reprogramar_cita`→UPDATE+INSERT historial; `delete_cita`→DELETE cascada a `historial_estado`/`recordatorios`; `create_recordatorio`→INSERT `recordatorios` (−24 h) |

### 1.4 Catálogo (lecturas) — catalog-service (`:8004`, BD `eps_catalogo`)

| Página Front | Acción Front | Endpoint / Puerto | Backend → Tabla BD |
|---|---|---|---|
| **AgendarCitaPage** | `catalogoApi.getSedes()` | `GET :8004/sedes` | `crud.get_sedes(solo_activas=True)` → SELECT `sedes` |
| **AgendarCitaPage** | `catalogoApi.getServicios()` | `GET :8004/servicios?solo_activos=true` | SELECT `servicios WHERE activo` |
| **AgendarCitaPage** | `catalogoApi.getEspecialidades(servicioId)` | `GET :8004/especialidades?servicio_id=…` | SELECT `especialidades WHERE servicio_id AND activo` |
| **AgendarCitaPage** | `catalogoApi.getMedicosDisponibles(servicioId, especialidadId)` | `GET :8004/medicos/disponibles?servicio_id&especialidad_id` | `get_medicos_disponibles()` → JOIN `medicos ↔ medico_especialidades ↔ especialidades`; si llega fecha/horas filtra con `verificar_disponibilidad()` (SELECT `disponibilidades` conteniendo la franja) |
| **AgendarCitaPage** | `catalogoApi.getDisponibilidadesMedico(medicoId)` (al elegir médico) | `GET :8004/disponibilidades/medico/{id}` | SELECT `disponibilidades WHERE medico_id AND activo` → alimenta el grid de horas de 30 min |
| **ServiciosPage** | `getServicios()` + `getEspecialidades(id)` por tarjeta | `GET /servicios`, `GET /especialidades?servicio_id` | Ídem anterior |
| MedicoCitasPage 🔶 | `citasApi.updateEstado` (ver §1.3) | — | — |
| Admin pages 🔶 | CRUD catálogo completo | endpoints **sí existen** (`POST/PUT/DELETE /servicios`, `/especialidades`, `/medicos`, `/medicos/{m}/especialidades/{e}`, `/disponibilidades`) pero las funciones exportadas en `apiClient.ts` **no** ⚠ | Escrituras lógicas (`activo=false`) sobre las tablas correspondientes |

> ⚠ Nota: `catalogoApi.getMedicos(especialidadId?)` pasa `especialidad_id` como query param a `GET /medicos`, pero ese endpoint solo acepta `skip/limit/solo_activos` — el filtro se ignora (el frontend real usa `getMedicosDisponibles`).

### 1.5 Asistente IA — ai-nlp-service (`:8005`, BD `eps_ainlp`)

| Página Front | Acción Front | Endpoint / Puerto | Backend → Tabla BD / Externo |
|---|---|---|---|
| **AsistentePage** | `aiApi.chat(mensaje, conversacion_id?, userId)` | `POST :8005/chat` | `post_chat()`: INSERT `conversacion` (si nueva) + INSERT `mensaje`(remitente=`usuario`) → loop Groq/tools (ver §2.3) → INSERT `mensaje`(remitente=`asistente`) → opcionalmente UPSERT `clasificacion_sintomas` |
| AsistentePage | conserva `conversacion_id` retornado en estado local | — | Reutiliza la misma fila de `conversacion` en siguientes mensajes |
| — (sin UI 🔶) | — | `GET /chat/conversaciones/{uid}`, `GET /chat/conversacion/{cid}/mensajes`, `POST .../cerrar`, `GET /chat/clasificacion/{cid}` | SELECTs/cerrado sobre `conversacion`, `mensaje`, `clasificacion_sintomas` |

### 1.6 Notificaciones — notifications-service (`:8006`)

| Página Front | Acción Front | Endpoint / Puerto | Backend → Tabla BD |
|---|---|---|---|
| **NotificationBell** (polling 30 s) y **MedicoNotificacionesPage** | `notificacionesApi.getByMedico(medicoId)` | `GET :8006/notificaciones/medico/{id}` | SELECT `notificaciones WHERE medico_id ORDER BY creado_en DESC LIMIT 50` ⚠ el front lee `n.notificacion_id` pero la columna es `notif_id` |
| MedicoNotificacionesPage | `marcarLeida(n.notificacion_id)` | `PATCH :8006/notificaciones/{notif_id}/leida` ⚠ id llegaría `undefined` por el desacople de nombre | UPDATE `notificaciones.leida = true` |
| MedicoNotificacionesPage | `marcarTodasLeidas(medicoId)` | `PATCH :8006/notificaciones/medico/{id}/leer-todas` ✅ | `UPDATE notificaciones SET leida=true WHERE medico_id AND leida=false` |
| — (interno) | consumidor RabbitMQ | colas `cuenta_creada`, `cita_confirmada`, `cita_cancelada`, `cita_recordatorio` | `callback()` → plantilla HTML → SendGrid (sin escritura en BD); eventos in-app para médicos se crearían vía `POST /notificaciones` (sin publicador hoy 🔶) |

---

## 2. Flujos Críticos de la Aplicación

### 2.1 Flujo de Autenticación y Sesión (login por documento)

```
LoginPage.tsx                auth-service :8001              user-service :8002           Browser
─────────────                ──────────────────              ──────────────────           ───────
1. submit (react-hook-form)
   LoginForm{tipo_documento,
   numero_documento, password}
        │
2. authApi.login() ─────────► POST /auth/login/documento
                              │ get_correo_by_documento()
                              │   └──httpx GET /usuarios/buscar ────────► SELECT usuarios
                              │       (timeout 5 s; 404→401,             (numero_documento unique)
                              │        caída→503)
                              │ autenticar_usuario():
                              │   • SELECT credenciales BY correo
                              │   • verificar_bloqueo(bloqueado_hasta)
                              │   • bcrypt.checkpw(password_hash)
                              │   • fallos++ / bloqueo 15 min tras >5 intentos
                              │   • log_evento → INSERT log_autenticacion
                              │ create_access_token (30 min, HS256, claim tipo="access")
                              │ create_refresh_token (7 días, tipo="refresh")
        ◄────────────────────┘ LoginResponse{access_token, refresh_token,
                                            token_type, usuario_id, requiere_2fa, rol}
3. login(token, refreshToken, userId) ──► Zustand set() ──► persist middleware ──► localStorage["eps-auth-storage"]
        │
4. userApi.getById(usuario_id) ─────────────────────────────────────────────► GET :8002/usuarios/{id}
   setUser(res.data)  (error tolerado, no bloqueante)                          SELECT usuarios
        │
5. toast.success → navigate(location.state.from.pathname || '/')
```

**Sesión posterior**: cada request de `userClient/citasClient/catalogoClient/aiClient/notificacionesClient` pasa por el interceptor:
- Request: `Authorization: Bearer <token>` + `X-User-ID: <userId>` leídos con `useAuthStore.getState()` (lectura imperativa fuera de React).
- Response: si `status === 401` → `logout()` (resetea todo el store incluido localStorage) + `window.location.href = '/login'`. **No hay refresh automático** pese a que `refreshToken` está persistido (el endpoint `POST :8001/auth/refresh` existe pero sin cliente front).

**Guards**: `ProtectedRoute` (paciente) y `MedicoProtectedRoute` (rol `medico`) consultan `isAuthenticated`/`rol` del store; HomePage además redirige médicos a `/medico/dashboard`.

**Ramas no conectadas**: 2FA (`requiere_2fa` llega en la respuesta pero LoginPage lo ignora), recuperación de contraseña ("¿Olvidaste tu contraseña?" es un botón sin handler), logout desde Navbar/MedicoProfileDropdown/AdminLayout.

### 2.2 Flujo de Agendamiento de Citas

```
AgendarCitaPage.tsx                 catalog-service :8004            appointments-service :8003            BD eps_citas
───────────────────                 ─────────────────────            ──────────────────────────            ───────────
A. CARGA EN CASCADA (useQuery con enabled condicional)
   getSedes() ────────────────────► GET /sedes ────────────────────► SELECT sedes (activas)
   getServicios() ────────────────► GET /servicios ─────────────────► SELECT servicios
   [al elegir servicio]
   getEspecialidades(servicioId) ─► GET /especialidades?servicio_id ► SELECT especialidades
   getMedicosDisponibles(...) ────► GET /medicos/disponibles ───────► JOIN medicos↔medico_especialidades↔especialidades
                                     [+ filtro verificar_disponibilidad si fecha+horas] → SELECT disponibilidades
   [al elegir médico]
   getDisponibilidadesMedico(id) ─► GET /disponibilidades/medico/{id}► SELECT disponibilidades (activo)
        │
B. CÁLCULO LOCAL DE HORARIOS
   useEffect: filtra disponibilidad.dia_semana == ISO(día seleccionado, domingo=7)
   genera franjas de 30 min entre hora_inicio y hora_fin (formato 12h AM/PM)
   duracion = especialidad.duracion_cita_minutos || 20
   mapTipoServicio(nombre) → 'medicina_general'|'especialista'|'urgencias'|'laboratorio'
   convertToTimeFormat('09:30 AM') → '09:30:00';  sumarMinutos(hora, duracion) → hora_fin
        │
C. CONFIRMAR CITA (useMutation)
   canSubmit = servicioId && fecha && hora
   citasApi.create({
     usuario_id,                    ← useAuthStore().userId
     medico_id?: medicoId||undefined,
     especialidad_id?,
     tipo_servicio, fecha_cita (ISO date), hora_inicio ('HH:MM:00'), hora_fin,
     sede_id (default SEDE_DEFAULT='4bf0500a-…'), descripcion_sintomas?
   }) ─────────────────────────────────────────────────────────────► POST /citas
                                    │ create_cita():
                                    │   si medico_id es None:
                                    │     _obtener_medico_automatico() ──httpx──► GET :8004/servicios
                                    │                                             GET :8004/medicos/disponibles
                                    │     toma el PRIMER médico disponible (round-robin simple)
                                    │   es_horario_ocupado(): SELECT citas WHERE medico_id
                                    │     AND fecha AND estado='programada'
                                    │     AND hora_inicio < hora_fin_nueva AND hora_fin > hora_inicio_nueva
                                    │   conflicto → ValueError → HTTP 400 → toast.error
                                    │   OK → INSERT citas (estado='programada')
        ◄───────────────────────────┘ CitaResponse{cita_id, estado, …}
D. POST-ÉXITO
   qc.invalidateQueries(['citas', userId]) + (['citas-historial', userId])
   toast.success('¡Cita agendada exitosamente!') → navigate('/citas/ver')
```

**Interacciones asíncronas reales tras agendar — estado actual:**
- ❌ El appointments-service **no publica** `cita_confirmada` a RabbitMQ (no tiene productor). La cola existe y el consumer de notifications-service está listo, pero nadie emite el evento → el paciente no recibe email de confirmación por esta vía.
- 🔶 `POST /citas/{id}/recordatorio` crea filas en `recordatorios` (programado_para = cita − 24 h) y `GET /recordatorios/pendientes` las lista, pero **no hay scheduler** que las dispare ni publicador de `cita_recordatorio`.
- ✅ Vía alternativa real: el asistente IA puede agendar (ver §2.3); su confirmación es textual en el chat, también sin evento asíncrono.

**Cancelación (complemento)**: CancelarCitaPage → `POST /citas/{id}/cancelar` con header `X-User-ID` → UPDATE `citas` + INSERT `historial_estado` con motivo. Tampoco publica `cita_cancelada`.

### 2.3 Flujo del Asistente de IA (NLP)

```
AsistentePage.tsx                     ai-nlp-service :8005                       Externos / otras BDs
─────────────────                     ─────────────────────                      ─────────────────────
1. Usuario escribe → sendMessage(texto)
   push ChatMessage{role:'user'} + loading=true
        │
2. aiApi.chat(texto.trim(), conversacionId, userId) ──► POST /chat
   (userId viene de useAuthStore; si no hay conversación previa
    el backend crea una con usuario_id o UUID cero)
        │
3. post_chat() en app/main.py:
   a. crear_conversacion()/get_conversacion()          → INSERT/SELECT eps_ainlp.conversacion
   b. crear_mensaje(remitente='usuario')               → INSERT mensaje
   c. historial = últimos 6 mensajes                   → SELECT mensaje ORDER BY creado_en
      _mapear_historial_a_mensajes_llm() (usuario→user, asistente→assistant)
   d. inserta system message con usuario_id autenticado
   e. chat_completion(messages, tools=get_assistant_tools())  ──HTTPS──► Groq Cloud
      modelo llama-3.3-70b-versatile, max_tokens=400, tool_choice='auto'      (GROQ_API_KEY)
        │
4. SI el modelo devuelve tool_calls (p.ej. flujo de agendado):
   por cada tool_call → ejecutar_funcion(name, args):
     • obtener_disponibilidad_citas   → SIMULADA (cupos fijos ["09:00","10:30","14:00"]) 🔶
     • obtener_especialidades         → httpx GET :8004/especialidades ────► SELECT eps_catalogo.especialidades
     • obtener_medicos(esp_id)        → httpx GET :8004/especialidades/{id}/medicos ─► JOIN medico_especialidades
     • obtener_sedes                  → httpx GET :8004/sedes ─────────────► SELECT sedes
     • agendar_cita(confirmado=true)  → httpx POST :8003/citas (header X-User-ID,
                                        hora_fin = hora + 30 min) ─────────► INSERT eps_citas.citas
       (si confirmado≠true → responde pidiendo confirmación, NUNCA agenda)
   agrega mensajes assistant.tool_calls + role:'tool' al thread
   segunda llamada chat_completion(tools=None) ──► Groq redacta respuesta final
        │
5. crear_mensaje(remitente='asistente')               → INSERT mensaje
6. Si _es_mensaje_relevante_para_clasificacion(palabras clave: dolor, fiebre, tos…):
   clasificar_sintomas() → Groq con response_format json_object, temperature 0
   _normalizar_clasificacion() → UPSERT clasificacion_sintomas (nivel urgente/prioritario/programable,
                                confianza Numeric(5,4), ARRAY terminos)
        │
7. ChatResponse{respuesta (Markdown), conversacion_id, clasificacion}
        ◄────────────────────────────────────────────┘
8. Front: setConversacionId(conversacion_id) (persistente en sesión de chat)
   push ChatMessage{role:'assistant', content, action: clasificacion}
   ReactMarkdown renderiza; si action?.especialidad_sugerida → chip "Buscar disponibilidad" → /citas/agendar
9. onError → getFallbackResponse(texto): respuestas heurísticas locales (sin IA)
```

Puntos clave de integración: el chat **no requiere login técnico adicional** (hereda `Bearer`+`X-User-ID` del interceptor de `aiClient`); el agendado conversacional termina siendo un `POST /citas` normal al appointments-service con las mismas validaciones de disponibilidad.

---

## 3. Variables de Entorno, Docker y Despliegue

### 3.1 Matriz de variables de entorno (consumidas realmente por el código)

| Variable | auth | user | citas | catalog | ai-nlp | notif | Consumida en código por |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `DATABASE_URL` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `app/database.py` de cada servicio (engine SQLAlchemy) |
| `JWT_SECRET_KEY` | ✅ | — | — | — | — | — | `auth.py::_get_jwt_secret_key()` (único firmante/verificador real) |
| `USER_SERVICE_URL` | ✅ | — | — | — | — | — | `auth.py::get_correo_by_documento()` |
| `CATALOG_SERVICE_URL` | — | — | ✅ (default `http://localhost:8004`) | — | ✅ | — | `appointments/crud.py::_obtener_medico_automatico`, `groq_client.py::_consultar_catalog_service` |
| `CITAS_SERVICE_URL` | — | — | — | — | ✅ | — | `groq_client.py::_agendar_cita_en_citas_service` |
| `GROQ_API_KEY` | — | — | — | — | ✅ | — | `groq_client.py::configurar_groq()` |
| `RABBITMQ_URL` | ✅ (fallback URL CloudAMQP hardcodeada ⚠) | — | — | — | — | ✅ (fallback hardcodeado ⚠) | `rabbitmq_client.py`, `consumer.py` |
| `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL`\|`EMAIL_FROM` | — | — | — | — | — | ✅ | `email_client.py` |

Archivos `.env` presentes en disco (git-local): uno por servicio en `services/<svc>/.env` y `frontend/.env`.
⚠ **`frontend/.env` define `VITE_AUTH_URL … VITE_NOTIFICACIONES_URL`, pero `apiClient.ts` NO las lee**: las URLs están hardcodeadas según hostname (`isLocal ? localhost:800X : https://eps-*-service.onrender.com`). Cambiar el `.env` del front no tiene efecto.

### 3.2 Docker — composición de red

**Compose raíz (`/docker-compose.yml`, stack completo)** — red bridge implícita; los servicios se resuelven por nombre de contenedor:

| Contenedor | Imagen | Puertos host | Notas |
|---|---|---|---|
| `eps-auth-db` … `eps-ainlp-db` (×5) | `postgres:15-alpine` | `5432–5436 → 5432` | usuario/pass común `eps_user/eps_password`, BDs `eps_auth`, `eps_user`, `eps_citas`, `eps_catalogo`, `eps_ainlp`; healthcheck `pg_isready` |
| `eps-rabbitmq` | `rabbitmq:3.12-management-alpine` | `5672` (AMQP), `15672` (UI) | guest/guest, volumen `eps-rabbitmq-data` |
| `eps-auth-service` | build `services/auth-service` | `8001` | `DATABASE_URL=postgresql://…@eps-auth-db:5432/eps_auth`; `depends_on` con `condition: service_healthy` |
| `eps-user-service` | ídem | `8002` | apunta a `eps-user-db` |
| `eps-citas-service` | ídem | `8003` | + `CATALOG_SERVICE_URL` (inyectada desde `.env` raíz; **sin default interno** — si falta, `_obtener_medico_automatico` usa `http://localhost:8004` y fallaría en contenedor ⚠) |
| `eps-catalogo-service` | ídem | `8004` | — |
| `eps-ainlp-service` | ídem | `8005` | + `GROQ_API_KEY`, `CITAS_SERVICE_URL`, `CATALOG_SERVICE_URL` |
| `eps-notifications-service` | ídem | `8006` | solo `RABBITMQ_URL` + SendGrid; **sin `DATABASE_URL`** aunque tiene modelos/Alembic ⚠; monta `.env` propio vía `env_file` en su compose individual |

Volúmenes montados: `alembic/` y `alembic.ini` de cada servicio se montan dentro del contenedor para ejecutar `alembic upgrade head` en el arranque.

**Composes individuales** (`services/<svc>/docker-compose.yml`): cada servicio trae su propio Postgres (mismas credenciales, puertos host 5432/5433/5434/5435/5436 respectivamente); notifications incluye él solo el RabbitMQ local. Útiles para desarrollo aislado; el raíz es el orquestador integral.

### 3.3 Dockerfiles — detalles y hallazgos

| Servicio | Base | CMD | Observaciones |
|---|---|---|---|
| Todos los backend | `python:3.12-slim` | `sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port <N>"` | Patrón uniforme; migración antes de servir |
| auth/user/appointments/catalog | — | puertos fijos 8001–8004, `EXPOSE` correctos | — |
| ai-nlp | — | puerto fijo 8005 | ⚠ `EXPOSE 8003` (copy-paste incorrecto; documentación de red engañosa, no afecta runtime) |
| notifications | — | `uvicorn … --port $PORT` | Sin `EXPOSE`; compatible con Render (usa `$PORT`) |
| **frontend** | `node:20-alpine` | `npm run dev -- --host 0.0.0.0` en `EXPOSE 5173` | ⚠ Sirve el **dev server de Vite** incluso en producción (sin `vite build`/nginx); no hay stage multi-build |

⚠ **SPA fallback ausente**: AGENTS.md exige `frontend/public/_redirects` con `/* /index.html 200` para Render, pero **el archivo/directorio no existe** → refrescar rutas como `/citas/agendar` en producción devolverá 404.

### 3.4 Topología de despliegue (Render, según URLs de `apiClient.ts`)

| Componente | URL producción |
|---|---|
| Frontend SPA | `https://eps-digital-cn2h.onrender.com` (referenciada en CORS de todos los backends) |
| auth | `https://eps-digital.onrender.com` |
| user | `https://eps-user-service.onrender.com` |
| citas | `https://eps-appointments-service.onrender.com` |
| catálogo | `https://eps-catalog-service.onrender.com` |
| ai-nlp | `https://eps-ainlp-service.onrender.com` |
| notifications | `https://eps-notification-service.onrender.com` |
| Broker | CloudAMQP `amqps://…@shark.rmq.cloudamqp.com/jyzkesmj` (hardcodeado como fallback) |

Flujo de red en producción: el navegador del usuario llama **directamente** a cada servicio Render (no hay gateway/BFF ni proxy de Vite); todas las llamadas son cross-origin y dependen del CORS configurado. En local todo va a `localhost:800X` con el stack levantado vía `docker compose up` (raíz) + `npm run dev` en `frontend/`.

### 3.5 Checklist de riesgos de integración (resumen accionable)

1. ⚠ `PATCH /citas/{id}/estado`: acción principal de `MedicoCitasPage` contra un endpoint inexistente (usar `PUT /citas/{id}`).
2. ⚠ `notif_id` vs `notificacion_id`: rompe keys React y marcar-leída del portal médico.
3. ⚠ Eventos `cita_confirmada/cancelada/recordatorio` sin publicador: emails transaccionales de citas nunca se disparan.
4. ⚠ Falta `_redirects` + frontend servido con dev server en Docker.
5. ⚠ `frontend/.env` muerto; URLs duplicadas hardcodeadas en `apiClient.ts`.
6. ⚠ `CATALOG_SERVICE_URL`/`CITAS_SERVICE_URL` sin defaults seguros en compose raíz (dependen del `.env` raíz).
7. 🔶 Campos `*_nombre` de `Cita` esperados por la UI pero no retornados por `CitaResponse`.
8. 🔶 Portal admin completo sin rutear y con APIs/tipos fantasma; 2FA y recuperación de contraseña sin UI.
