# Frontend Context — EPS Digital

> Documento de arquitectura generado a partir del análisis directo del código en `frontend/src/`.
> Stack: **React 18.3 + TypeScript + Vite 6 + Tailwind CSS 4** (`@tailwindcss/vite`) **+ react-router 7** (`createBrowserRouter`) **+ TanStack Query 5 + Zustand 5** (con `persist`) **+ Axios**.
> UI: componentes estilo shadcn/ui sobre Radix (`app/components/ui/*`), `lucide-react` para iconos, `sonner` para toasts, `recharts` para gráficos, `react-markdown` para el chat, `react-hook-form` para formularios. Color institucional `PRIMARY = '#2B3E59'`.

---

## 1. Arquitectura del Frontend

### 1.1 Estructura de carpetas

```
frontend/src/
├── main.tsx                  # Entry point → createRoot → <App/>
├── styles/                   # index.css, tailwind.css, theme.css, fonts.css
└── app/
    ├── App.tsx               # <QueryClientProvider><RouterProvider/></QueryClientProvider>
    ├── routes.tsx            # createBrowserRouter (árbol completo de rutas)
    ├── components/
    │   ├── Layout.tsx        # Layout público (Navbar + Outlet + Footer + Toaster)
    │   ├── Navbar.tsx        # Navbar fija con dropdown "Citas Médicas" y menú móvil
    │   ├── Footer.tsx
    │   ├── ProtectedRoute.tsx    # Guard de autenticación (paciente)
    │   ├── RoleRoute.tsx         # Guard por rol (admin|medico) — ⚠ NO usado en routes.tsx
    │   ├── MedicoProtectedRoute.tsx  # Guard del portal médico
    │   ├── MedicoLayout.tsx      # Sidebar médico + header con NotificationBell
    │   ├── AdminLayout.tsx       # Sidebar admin — ⚠ NO cableado en routes.tsx
    │   ├── medico/               # NotificationBell, MedicoProfileDropdown
    │   ├── figma/ImageWithFallback.tsx
    │   └── ui/*              # Biblioteca shadcn/Radix (button, card, dialog, table, …)
    ├── lib/
    │   ├── apiClient.ts      # Instancias Axios + interceptores + namespaces *Api
    │   └── queryClient.ts    # QueryClient global (staleTime 5 min, retry 1)
    ├── stores/
    │   └── authStore.ts      # Zustand persistido en localStorage ('eps-auth-storage')
    ├── types/
    │   └── index.ts          # Interfaces del dominio
    └── pages/                # 13 páginas paciente + admin/ (5) + medico/ (7)
```

### 1.2 Enrutamiento (`app/routes.tsx`)

`router = createBrowserRouter([...])` con **dos ramas raíz** más una ruta suelta:

**Rama `/medico` (Portal Médico):**
- `/medico/login` → `MedicoLoginPage` (fuera del layout, pública).
- `/medico` → `MedicoLayout`, children:
  - `index` → `<Navigate to="dashboard" replace />`
  - `dashboard`, `agenda`, `consultas`, `hce`, `notificaciones`, `perfil` — cada uno envuelto en `<MedicoProtectedRoute>`
  - `*` → `NotFoundPage`

**Rama `/` (Portal Paciente/Público) con `Layout`:**
- Públicas: `/` (`HomePage`), `/login`, `/register`, `/servicios`, `/ayuda`.
- Protegidas con `<ProtectedRoute>`:
  - `/perfil` → `ProfilePage`
  - `/citas` → `CitasPage` (contenedor de pestañas con `<Outlet/>`) y children:
    - `index` → `<Navigate to="agendar" replace />`
    - `agendar` → `AgendarCitaPage`
    - `ver` → `VerCitasPage`
    - `cancelar` → `CancelarCitaPage`
    - `historial` → `HistorialCitasPage`
  - `/asistente` → `AsistentePage`
- `*` → `NotFoundPage`

### 1.3 Layouts

| Layout | Archivo | Estructura |
|---|---|---|
| **Layout** | `components/Layout.tsx` | `div.min-h-screen.flex.flex-col.bg-[#F5F5F5]` → `<Navbar/>` (fija, `h-16`) → `<main className="flex-1 pt-16"><Outlet/></main>` → `<Footer/>` → `<Toaster position="top-right" richColors/>` (sonner) |
| **MedicoLayout** | `components/MedicoLayout.tsx` | Flex horizontal: `<aside className="w-56">` con fondo `#2B3E59`, logo "EPS Digital / Panel Médico", `navItems = [dashboard, agenda, consultas, hce, notificaciones]` (iconos lucide), `<MedicoProfileDropdown/>` al pie; columna derecha con `<header className="h-16">` que contiene `<NotificationBell/>` y `<main className="flex-1 overflow-auto"><Outlet/></main>`. Resalta la ruta activa comparando `location.pathname === item.to`. |
| **AdminLayout** | `components/AdminLayout.tsx` | ⚠ Recibe `{ children }: { children: React.ReactNode }` (**no usa `Outlet`**, patrón distinto). Sidebar `w-64` `#2B3E59` con `navItems = [/admin, /admin/medicos, /admin/servicios, /admin/reportes]`, enlace condicional "Gestión Admins" (`/admin/admins`) visible solo si `esSuperAdmin`, botón `logout`. **No está referenciado desde `routes.tsx`** — código preparado pero sin activar. |

### 1.4 Guards (componentes protegidos)

| Componente | Props | Lógica |
|---|---|---|
| `ProtectedRoute` | `{ children: ReactNode }` | Lee `isAuthenticated` de `useAuthStore()`; si es falso → `<Navigate to="/login" state={{ from: location }} replace />` (LoginPage vuelve al `from` tras loguear). |
| `RoleRoute` | `{ children: ReactNode; allowedRoles: ('admin' \| 'medico')[] }` | Sin sesión → `/login`; con sesión pero `rol` fuera de `allowedRoles` → `/`. **Definido pero no usado en ninguna ruta actual** (reservado para el portal admin). |
| `MedicoProtectedRoute` | `{ children: React.ReactNode }` | Sin sesión → `/medico/login`; si `rol !== 'medico'` → `/`. |

> Nota: los guards son **client-side only**: la validez real del JWT la aplica cada microservicio; aquí se confía en el estado persistido de Zustand.

---

## 2. Tipos e Interfaces (`types/index.ts`)

### 2.1 Inventario de interfaces

| Interfaz | Campos clave | Uso principal |
|---|---|---|
| `User` | `usuario_id, nombres, apellidos, tipo_documento, numero_documento, fecha_nacimiento, correo, telefono: string`, `creado_en?, actualizado_en?: string` | Perfil y navbar (`user?.nombres`) |
| `InformacionMedica` | `tipo_sangre?, alergias?, enfermedades_cronicas?, medico_asignado?` | Sección médica de ProfilePage |
| `Afiliacion` | `numero_poliza?, fecha_afiliacion?, estado?, tipo_afiliacion?` | Tarjeta "Mi EPS" de ProfilePage |
| `UserCompleto` | `{ user: User; informacion_medica: InformacionMedica; afiliacion: Afiliacion }` | Respuesta de `GET /usuarios/{id}/completo` |
| `Cita` | `cita_id, usuario_id, medico_id?, especialidad_id?, tipo_servicio, fecha_cita, hora_inicio, hora_fin?, sede_id?, descripcion_sintomas?, estado: 'programada' \| 'cancelada' \| 'atendida' \| 'no_asistio'`, campos de presentación `especialidad_nombre?, medico_nombre?, sede_nombre?, creado_en?` | Todas las vistas de citas |
| `Servicio` | `servicio_id, nombre, descripcion, activo?, disponible?, icono?` | ServiciosPage / Agendar |
| `Especialidad` | `especialidad_id, nombre, servicio_id, duracion_cita_minutos?` | Cálculo de duración al agendar |
| `Medico` | `medico_id, nombres, apellidos, especialidad_id, especialidad_nombre?` | Select de médicos |
| `AuthCredentials` | `access_token, refresh_token, token_type, usuario_id, requiere_2fa?` | Respuesta de login |
| `ChatMessage` | `id, role: 'user' \| 'assistant', content, timestamp: Date, action?: string` | Estado local del chat IA |
| `Sede` | `sede_id, nombre, direccion, ciudad, telefono?, activo?` | Select de sedes |
| `Disponibilidad` | `disponibilidad_id, medico_id, especialidad_id, sede_id, dia_semana: number, hora_inicio, hora_fin, activo?` | Filtrado de horas al agendar |
| `MetricasMedico` | `citas_hoy, proximas_7_dias, atendidas_mes, tiempo_espera_promedio_min, tasa_asistencia_pct, ingresos_mes` | Dashboard médico |
| `CitaMedico extends Cita` | `modalidad: 'telemedicina' \| 'presencial'; paciente_nombre?, paciente_documento?, paciente_uuid_hce?` | Vista de citas del médico (futura) |
| `Notificacion` | `notificacion_id, medico_id, tipo: 'cita_nueva' \| 'cita_cancelada' \| 'recordatorio' \| 'sistema', titulo, descripcion, leida, enlace?, creado_en` | Campana y bandeja del médico |
| `DisponibilidadMedico extends Disponibilidad` | `especialidad_nombre?, sede_nombre?` | Presentación de horarios |

### 2.2 Coincidencias y desacoples vs. Schemas del backend

**Coincidencias correctas**
- `UserCompleto` ↔ backend `UsuarioCompletoResponse` (`{user, informacion_medica, afiliacion}`).
- `Sede` ↔ `SedeResponse`; `Disponibilidad` ↔ `DisponibilidadResponse` (mismo contrato de `dia_semana` ISO 1–7).
- `MetricasMedico` coincide 1:1 con el dict que devuelve `GET /citas/medico/{id}/metricas`.
- `estado` de `Cita` replica exactamente el dominio del backend (`ESTADOS_CITA_VALIDOS`).

**Desacoples detectados**

1. **`Cita.especialidad_nombre / medico_nombre / sede_nombre` no existen en el backend.** `CitaResponse` solo retorna IDs; las páginas del paciente/médico leen esos campos (`cita.medico_nombre`, `cita.sede_nombre`) y mostrarán vacío salvo que el backend enriquezca la respuesta.
2. **`Notificacion.notificacion_id` vs backend `notif_id`.** El modelo/columna del notifications-service es `notif_id` (`models.py`), mientras el frontend usa `n.notificacion_id` como `key` y como argumento de `PATCH /notificaciones/{id}/leida` → claves duplicadas e id `undefined` en producción.
3. **`InformacionMedica.medico_asignado` no existe en el backend** (`MedicalInfoResponse` tiene `tipo_sangre/alergias/enfermedades_cronicas/medicamentos_actuales` + IDs). El campo mostrado en ProfilePage quedará siempre `—`; además faltan `info_medica_id`, `usuario_id`, `actualizado_en` y `medicamentos_actuales`.
4. **`ChatMessage.action?: string` vs backend `clasificacion: objeto`.** `ChatResponse.clasificacion` es un `ClasificacionSintomasResponse` (objeto); AsistentePage lo asigna a `action` y luego lee `msg.action.especialidad_sugerida` (funciona en runtime, pero el tipo declara `string`). Coincide con la nota de AGENTS.md: "`msg.action` guarda un objeto".
5. **`Servicio.disponible?: boolean`**: el backend solo expone `activo` (AGENTS.md ya lo advierte); `disponible` nunca llegará poblado.
6. **`Medico.especialidad_id / especialidad_nombre`**: `MedicoResponse` del catálogo no incluye especialidades (viven en `medico_especialidades`); solo `get_medicos_con_especialidades` las anida.
7. **Tipos fantasma usados por módulos admin**: `MetricasCitas` y `MedicoConEspecialidades` se importan en `pages/admin/*` pero **no están definidos** en `types/index.ts` (ver §4.3).
8. Menores: `User.telefono` requerido en FE (backend lo permite `null`); `Cita.hora_fin/sede_id` opcionales en FE pero obligatorios en `CitaResponse`; falta `actualizado_en` en `Cita`.

---

## 3. Manejo de Estado Global y Cliente API

### 3.1 `stores/authStore.ts` (Zustand + `persist`)

```ts
interface AuthState {
  token: string | null;        // access_token JWT
  refreshToken: string | null; // refresh_token JWT
  userId: string | null;       // UUID del usuario autenticado
  user: User | null;           // perfil completo (para Navbar/Home/perfil médico)
  isAuthenticated: boolean;
  rol: string | null;          // 'usuario' | 'medico' | 'paciente' | 'admin'
  medicoId: string | null;     // UUID del médico asociado (portal médico)

  login: (token, refreshToken, userId) => void; // setea tokens + isAuthenticated
  logout: () => void;                           // reset total del estado
  setUser: (user: User) => void;
  setRol: (rol: string) => void;
  setMedicoId: (medicoId: string) => void;
}
export const useAuthStore = create<AuthState>()(persist((set) => ({...}), { name: 'eps-auth-storage' }));
```

- **Persistencia**: middleware `persist` de Zustand → **todo el estado se serializa en `localStorage` bajo la clave `'eps-auth-storage'`** (incluye tokens JWT y perfil). No hay cifrado ni expiración automática.
- `logout()` limpia token/refresh/userId/user/isAuthenticated/rol/medicoId.
- Consumo típico: `useAuthStore()` completo en guards/páginas; selector atómico `useAuthStore((s) => s.userId)` en AsistentePage; lectura imperativa `useAuthStore.getState().token` dentro de los interceptores de Axios (evita dependencia reactiva).
- ⚠ `AdminLayout` y `AdminDashboardPage` leen `esSuperAdmin` del store, pero **ese campo no existe en `AuthState`** (siempre `undefined`).

### 3.2 `lib/apiClient.ts` (Axios multi-servicio)

**URLs base** — resueltas por hostname (`window.location.hostname === 'localhost' || '127.0.0.1'`):

| Cliente | Local | Producción |
|---|---|---|
| `authClient` | `http://localhost:8001` | `https://eps-digital.onrender.com` |
| `userClient` | `http://localhost:8002` | `https://eps-user-service.onrender.com` |
| `citasClient` | `http://localhost:8003` | `https://eps-appointments-service.onrender.com` |
| `catalogoClient` | `http://localhost:8004` | `https://eps-catalog-service.onrender.com` |
| `aiClient` | `http://localhost:8005` | `https://eps-ainlp-service.onrender.com` |
| `notificacionesClient` | `http://localhost:8006` | `https://eps-notification-service.onrender.com` |

**Factory `createClient(baseURL, requiresAuth = false)`**:
- Instancia Axios con `headers: {'Content-Type': 'application/json'}` y `timeout: 15000`.
- Si `requiresAuth`:
  - **Request interceptor**: inyecta `Authorization: Bearer ${token}` y header custom **`X-User-ID: ${userId}`** (el appointments-service usa este header en cancelar/reprogramar).
  - **Response interceptor**: ante `error.response?.status === 401` ejecuta `useAuthStore.getState().logout()` y redirección dura `window.location.href = '/login'` (no intenta refresh automático pese a guardar `refreshToken`).
- Solo `authClient` se crea **sin** interceptores; los otros cinco llevan auth.

**Namespaces de API**:

```ts
authApi = {
  login({tipo_documento, numero_documento, password})  // POST /auth/login/documento
  register(data)                                        // POST /auth/register
  me()                                                  // GET /auth/me
  getMedicoId()                                         // GET /auth/medico-id
}
userApi = {
  create(data)                                          // POST /usuarios
  getById(userId)                                       // GET /usuarios/{id}
  update(userId, data)                                  // PUT /usuarios/{id}   ← PUT, no PATCH
  getCompleto(userId)                                   // GET /usuarios/{id}/completo
  buscarPorDocumento(tipoDocumento, numeroDocumento)    // GET /usuarios/buscar
}
citasApi = {
  create(data)                                          // POST /citas
  getByUser(userId)                                     // GET /citas/usuario/{userId}
  getHistorial(userId)                                  // GET /citas/usuario/{userId}/historial
  cancel(citaId, motivo)                                // POST /citas/{citaId}/cancelar  body {motivo}
  getCitasMedico(medicoId, filters?)                    // GET /citas/medico/{medicoId}?fecha|fecha_inicio|fecha_fin
  getMetricasMedico(medicoId)                           // GET /citas/medico/{medicoId}/metricas
  updateEstado(citaId, estado)                          // PATCH /citas/{citaId}/estado  ⚠ endpoint inexistente en backend
}
catalogoApi = {
  getServicios()                                        // GET /servicios
  getEspecialidades(servicioId?)                        // GET /especialidades?servicio_id
  getMedicos(especialidadId?)                           // GET /medicos?especialidad_id ⚠ el backend /medicos ignora ese query param
  getMedicosDisponibles(servicioId?, especialidadId?, fecha?, horaInicio?, horaFin?)
                                                        // GET /medicos/disponibles (params condicionales)
  getDisponibilidadesMedico(medicoId)                   // GET /disponibilidades/medico/{medicoId}
  getSedes()                                            // GET /sedes
}
aiApi = {
  chat(mensaje, conversacion_id?, usuario_id?)          // POST /chat  (spread condicional de ids)
}
notificacionesApi = {
  getByMedico(medicoId)                                 // GET /notificaciones/medico/{medicoId}
  marcarLeida(id)                                       // PATCH /notificaciones/{id}/leida
  marcarTodasLeidas(medicoId)                           // PATCH /notificaciones/medico/{medicoId}/leer-todas
}
```

> Los payloads viajan mayormente como `Record<string, unknown>` (sin tipado fuerte por endpoint); el tipado fuerte vive en `types/index.ts` aplicado a las respuestas vía `useQuery<T>`.

### 3.3 `lib/queryClient.ts` (TanStack Query)

```ts
export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
});
```

Convenciones de `queryKey` observadas: `['sedes']`, `['servicios']`, `['especialidades', servicioId]`, `['medicos', servicioId, especialidadId]`, `['disponibilidades', medicoId]`, `['citas', userId]`, `['citas-historial', userId]`, `['user-completo', userId]`, `['citas-medico', medicoId, 'dashboard']`, `['citas-medico-dia', medicoId, fecha]`, `['notificaciones', medicoId]`, `['metricas-citas']`, `['medicos-con-especialidades']`.
Tras mutaciones se invalidan las llaves afectadas (`qc.invalidateQueries`) — requisito también documentado en AGENTS.md. `NotificationBell` añade polling con `refetchInterval: 30000`.

---

## 4. Flujos de Páginas y Vistas Principales

### 4.1 Usuario / Paciente

| Página | Propósito y lógica principal |
|---|---|
| **HomePage** (`/`) | Hero con gradiente institucional; tarjeta "Bienvenido de vuelta" si hay sesión; **redirige a médicos** (`rol === 'medico'`) a `/medico/dashboard`; consulta `['citas', userId]` para mostrar la próxima cita programada. CTAs a agendar/servicios/perfil/citas. |
| **LoginPage** (`/login`) | Formulario `LoginForm {tipo_documento, numero_documento, password}` con `react-hook-form` (select CC/CE/PA/TI). Llama `authApi.login` (**flujo documento**, no correo), hace `login(access_token, refresh_token, usuario_id)` en el store, intenta `userApi.getById(usuario_id)` → `setUser` (error no bloqueante), navega a `location.state.from.pathname \|\| '/'`. Errores leídos de `response.data.detail/message`. |
| **RegisterPage** (`/register`) | Wizard de 2 pasos: `Step1Form` (documento, nombres, apellidos, fecha_nacimiento, `acepta_terminos` obligatorio) y `Step2Form` (teléfono con pattern `[0-9+\-\s]{7,15}`, correo con regex, password con validación idéntica al backend: ≥8 chars + mayúscula + número, confirmación). Ejecuta `authApi.register` → obtiene `usuario_id` → `userApi.create({...perfil, usuario_id})` (patrón registro distribuido Auth+User) → redirige a `/login`. Maneja `detail` string o array de errores Pydantic (`detail[0].msg`). |
| **ProfilePage** (`/perfil`) | `useQuery<UserCompleto>` con `getCompleto`; tres tarjetas (Personal / Médica / EPS) y modal de edición controlado (`editData: Record<string,string>` con nombres, apellidos, teléfono, correo) que llama `userApi.update` (**PUT**) → `setUser(res.data)` + invalidación de `['user-completo', userId]`. |
| **CitasPage** (`/citas`) | Contenedor de pestañas `NavLink` (Agendar / Ver / Cancelar-Reprogramar / Historial) + `<Outlet/>`. |
| **AgendarCitaPage** (`/citas/agendar`) | Núcleo del agendamiento. Estados locales encadenados: `servicioId → especialidadId → medicoId → fecha → hora`. Queries en cascada (`enabled:` condicional) sobre `catalogoApi`. Componentes propios: `MiniCalendar` (calendario mensual con días pasados deshabilitados) y generación de franjas de 30 min desde `Disponibilidad` del médico (convierte `getDay()` a ISO domingo=7). Utilidades: `mapTipoServicio` (heurística nombre→`medicina_general/especialista/urgencias/laboratorio`), `convertToTimeFormat` (12h AM/PM → `HH:MM:00`), `sumarMinutos` (`hora_fin = hora_inicio + duracion_cita_minutos`, default 20). Constante `SEDE_DEFAULT = "4bf0500a-e23a-4f57-a8e8-ce4c20223695"` preselecciona sede. Mutation `citasApi.create({usuario_id, medico_id?, especialidad_id?, tipo_servicio, fecha_cita, hora_inicio, hora_fin, sede_id, descripcion_sintomas?})` → toast + invalidate `['citas']`/`['citas-historial']` + navigate `/citas/ver`. Tarjeta lateral "Resumen de Cita". |
| **VerCitasPage** (`/citas/ver`) | Lista de `estado === 'programada'` con `CitaCard({ cita }: { cita: Cita })` (badge de estado, médico, fecha `toLocaleDateString('es-CO')`, sede, síntomas). Botón "Modificar" navega a `/citas/cancelar` con `state={{ citaId }}`. |
| **CancelarCitaPage** (`/citas/cancelar`) | Master-detail: citas programadas → panel de acción con select de motivos predefinidos ("No puedo asistir", "Mejoré de salud", "Conflicto de horario", "Cambio de médico", "Otro"), modal de confirmación propio (overlay fixed) y mutation `citasApi.cancel(cita.cita_id, motivo \|\| 'Sin motivo especificado')`. El botón "Reprogramar cita" solo enlaza a `/citas/agendar` (no usa el endpoint de reprogramación del backend). |
| **HistorialCitasPage** (`/citas/historial`) | `getHistorial` + filtros locales (estado y mes `YYYY-MM`), tabla responsive con badges de estado (`statusConfig`). Re-filtra `estado !== 'programada'` por si la API devuelve programadas. |
| **AsistentePage** (`/asistente`) | Chat "EPSIA". Estado local `messages: ChatMessage[]` + `conversacionId`; `sendMessage` llama `aiApi.chat(texto, conversacionId, userId)` (pasa `userId` desde `useAuthStore`, según AGENTS.md), guarda el `conversacion_id` retornado y adjunta `clasificacion` al mensaje como `action`. Renderiza respuestas con `ReactMarkdown`; muestra chip "Buscar disponibilidad" cuando `msg.action.especialidad_sugerida` existe; sugerencias rápidas clickeables; fallback offline `getFallbackResponse(input)` con respuestas heurísticas si la API falla. Accesos rápidos a `/citas/agendar`, `/citas/ver`, `/ayuda`. |
| **ServiciosPage** (`/servicios`) | Grid de tarjetas de servicios; para cada servicio una sub-query de `getEspecialidades(servicio.servicio_id)` (lista desplegable por tarjeta). |
| **AyudaPage** (`/ayuda`) | FAQ estática (acordeón con `useState`), sin llamadas API. |

### 4.2 Médico (prefijo `/medico`, layout propio)

| Página | Propósito |
|---|---|
| **MedicoLoginPage** (`/medico/login`) | Mismo formulario de login por documento; tras autenticar guarda `rol` desde `LoginResponse`; si `rol === 'medico'` → `/medico/dashboard`, si no fuerza `setRol('paciente')` y va a `/`. Redirige automáticamente si ya está autenticado como médico (`useEffect`). |
| **MedicoDashboardPage** (`/medico/dashboard`) | Resuelve `medicoId` una sola vez con `authApi.getMedicoId()` (`GET /auth/medico-id`) y lo persiste en el store (`setMedicoId`). Consulta `getCitasMedico(medicoId, { fecha_inicio: inicioMes, fecha_fin: en7Dias })` y calcula client-side 3 `MetricCard` (Citas hoy / Próximas 7 días / Atendidas este mes) + listados "Citas de hoy" y "Próximas citas · 7 días". |
| **MedicoAgendaPage** (`/medico/agenda`) | Calendario mensual navegable (lunes primero) con selección de día; panel inferior placeholder "Sin citas programadas para este día"; botón "Configurar disponibilidad" **sin handler** (WIP, no consume `disponibilidades`). |
| **MedicoCitasPage** (`/medico/consultas`) | Gestión del día: componente interno `SelectorFecha` (input date + avanzar/retroceder días). Lista citas programadas con acciones `confirm()` + `cambiarEstado.mutate({id, estado})` → `citasApi.updateEstado` (`PATCH /citas/{id}/estado`) hacia `atendida` / `no_asistio` / `cancelada`; sección "Historial del día". ⚠ Depende del endpoint PATCH que el backend aún no expone (el backend solo ofrece `PUT /citas/{cita_id}`). |
| **MedicoHCEPage** (`/medico/hce`) | Buscador de historias clínicas por documento (tipo + número) **sin handler aún**; lista "Pacientes recientes" alimentada por `PACIENTES_MOCK` (hardcoded). WIP. |
| **MedicoNotificacionesPage** (`/medico/notificaciones`) | Bandeja completa: queries `notificacionesApi.getByMedico(medicoId)`, filtros locales (`todas/no_leidas/citas/sistema`), click marca leída (`marcarLeida`) y botón "Marcar todas como leídas"; iconos emoji por `tipo` y `tiempoRelativo()` (ahora/Xm/Xh/Xd). Usa `n.notificacion_id` (desacople con `notif_id` del backend, ver §2.2). |
| **MedicoPerfilPage** (`/medico/perfil`) | Solo lectura desde `useAuthStore().user` (nombre, documento, correo, teléfono) con avatar externo `ui-avatars.com`. No editable. |

Componentes de apoyo: `NotificationBell` (campana en el header del MedicoLayout, polling cada 30 s, dropdown con últimas 5, badge de no leídas, navega a `/medico/notificaciones`) y `MedicoProfileDropdown` (avatar/iniciales, "Mi Perfil", "Configuración" (stub), logout → `/medico/login`).

### 4.3 Admin (`pages/admin/*`) — código NO enrutado (WIP/dead code)

⚠ **Ninguna página admin está registrada en `routes.tsx`** (no existe rama `/admin`), `AdminLayout` y `RoleRoute` no se importan ahí, y estas páginas invocan APIs y tipos **que no existen todavía** en `apiClient.ts` / `types/index.ts`:

| Página | Intención | Dependencias faltantes |
|---|---|---|
| `AdminDashboardPage` | KPIs + `BarChart` (recharts) de `por_dia`, top 5 especialidades/médicos, accesos rápidos si `esSuperAdmin` | `citasApi.getMetricas(7)` (no existe; sí existe `getMetricasMedico`), tipo `MetricasCitas`, `esSuperAdmin` en el store |
| `AdminMedicosPage` | CRUD de médicos + asignación de especialidades + modal de horarios + creación de credencial | `catalogoApi.getMedicosConEspecialidades/createMedico/updateMedico/deleteMedico/asignarEspecialidad/createDisponibilidad/deleteDisponibilidad` y `authApi.createMedicoCredencial` (ninguno exportado hoy); tipos `MedicoConEspecialidades` |
| `AdminServiciosPage` | CRUD servicios y especialidades anidadas | `catalogoApi.createServicio/updateServicio/deleteServicio/createEspecialidad/updateEspecialidad/deleteEspecialidad` |
| `AdminReportesPage` | Reporte de citas canceladas por rango de fechas con export | `citasApi.getCanceladas({fecha_inicio, fecha_fin})` |
| `AdminAdminsPage` | Gestión de administradores (crear/eliminar con corona 👑) | `authApi.getAdmins/createAdmin/deleteAdmin` |

Estos módulos compilan parcialmente gracias a casts `as any` / `as Parameters<typeof useQuery>[0]` (Vite/esbuild no type-checka en build), pero romperían en `tsc --noEmit` y en runtime al ejecutarse.

---

## 5. Observaciones transversales

1. **Tokens en localStorage**: `persist` guarda `token` y `refreshToken` sin cifrado; vulnerable a XSS. El interceptor de 401 hace logout duro sin intentar renovar con el `refresh_token` almacenado.
2. **Autenticación dual**: además del `Bearer`, el frontend envía siempre `X-User-ID` (consumido por appointments-service en cancelar/reprogramar y aceptado por CORS en varios servicios).
3. **Login exclusivo por documento**: `authApi.login` apunta a `/auth/login/documento`; el flujo por correo (`POST /auth/login`) y todo el ciclo 2FA/recuperación del backend carecen de UI.
4. **Reprogramación incompleta**: el backend expone `POST /citas/{id}/reprogramar`, pero la UI solo enlaza a "agendar nueva cita"; y el cambio de estado del médico usa un `PATCH /citas/{id}/estado` inexistente.
5. **Campos de presentación (`*_nombre`) esperados por la UI pero no provistos por `CitaResponse`**: conviene enriquecer el response del appointments-service o resolver nombres en frontend con los IDs.
6. **Duplicación de constantes**: opciones de documento (`TIPO_DOC_OPTIONS`) y colores de estado (`statusConfig`/`estadoColor`) se repiten en varias páginas; candidatos a extraer a `lib/constants`.
7. **UI kit shadcn/ui presente pero poco usado**: la mayoría de páginas estilizan con clases Tailwind directas; los componentes de `components/ui/*` apenas se consumen.
