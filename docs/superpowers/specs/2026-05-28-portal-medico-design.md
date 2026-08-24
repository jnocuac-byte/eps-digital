# Design Spec: Portal Médico EPS Digital

**Fecha:** 2026-05-28
**Estado:** Aprobado
**Alcance:** Interfaz completa para médicos — login separado, dashboard, agenda, consultas, HCE, notificaciones, perfil

---

## 1. Resumen Ejecutivo

Implementar un portal médico completo para EPS Digital que permita a los médicos gestionar su agenda, consultar citas del día, buscar historias clínicas de pacientes, y recibir notificaciones. El portal tendrá una ruta de login separada (`/medico/login`) y un layout propio con sidebar y header independiente al módulo de pacientes.

**Enfoque:** Híbrido — compartir auth store y API client con pacientes, pero UI completamente separada.

---

## 2. Arquitectura de Login Médico

### 2.1 Ruta

- **URL:** `/medico/login`
- **Componente:** `MedicoLoginPage.tsx`
- **Ubicación:** Fuera del `MedicoLayout` (página completa centrada, sin sidebar)

### 2.2 Flujo

1. Médico accede a `/medico/login`
2. Formulario: tipo documento + número documento + contraseña (mismo que login paciente)
3. POST a `POST /auth/login/documento` (mismo backend)
4. Backend devuelve `{ access_token, refresh_token, usuario_id, rol }`
5. Frontend guarda token, userId, y rol en auth store
6. Si `rol === 'medico'`, redirige a `/medico/dashboard`
7. Si el usuario ya está autenticado y es médico, `/medico/login` redirige a `/medico/dashboard`

### 2.3 Branding

- Color primario: `#2B3E59`
- Logo EPS Digital con icono HeartPulse
- Título: "EPS Digital"
- Subtítulo: "Portal Médico"
- Fondo: `#F5F5F5`

### 2.4 Componentes

| Archivo | Descripción |
|---------|-------------|
| `MedicoLoginPage.tsx` | Página de login completa con formulario |

---

## 3. Auth Store — Cambios

### 3.1 Interfaz Actual

```typescript
interface AuthState {
  token: string | null;
  refreshToken: string | null;
  userId: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (token, refreshToken, userId) => void;
  logout: () => void;
  setUser: (user) => void;
}
```

### 3.2 Interfaz Nueva

```typescript
interface AuthState {
  token: string | null;
  refreshToken: string | null;
  userId: string | null;
  user: User | null;
  isAuthenticated: boolean;
  rol: string | null;           // NUEVO: 'paciente' | 'medico' | 'admin'
  medicoId: string | null;      // NUEVO: ID del médico (solo si rol=medico)
  
  login: (token, refreshToken, userId) => void;
  logout: () => void;
  setUser: (user) => void;
  setRol: (rol: string) => void;       // NUEVO
  setMedicoId: (medicoId: string) => void; // NUEVO
}
```

### 3.3 Persistencia

- Clave de localStorage: `eps-auth-storage` (sin cambios)
- El `rol` y `medicoId` se persisten automáticamente con el resto del estado

---

## 4. MedicoLayout — Sidebar + Header

### 4.1 Estructura Visual

```
┌─────────────────────────────────────────────┐
│ Sidebar (224px)          │ Header (flex-1)  │
│                          │                  │
│ ┌──────────────────┐     │ ┌──────────────┐ │
│ │ Logo EPS Digital │     │ │ 🔔 badge 3   │ │
│ │ Panel Médico     │     │ └──────────────┘ │
│ ├──────────────────┤     ├──────────────────┤
│ │ 📊 Dashboard     │     │                  │
│ │ 📅 Mi Agenda     │     │  Contenido de    │
│ │ 📋 Consultas     │     │  la página       │
│ │ 🏥 Hist. Clínicas│     │                  │
│ │ 🔔 Notificaciones│     │                  │
│ ├──────────────────┤     │                  │
│ │                  │     │                  │
│ │ [espacio libre]  │     │                  │
│ │                  │     │                  │
│ ├──────────────────┤     │                  │
│ │ [Foto] Dr. X [v] │     │                  │
│ └──────────────────┘     │                  │
└──────────────────────────┴──────────────────┘
```

### 4.2 Sidebar

- **Ancho:** 224px (`w-56`)
- **Color de fondo:** `#2B3E59`
- **Logo:** Icono HeartPulse + "EPS Digital" + "Panel Médico"
- **Navegación:** 5 items con iconos Lucide
- **Perfil:** Avatar circular + nombre + chevron → dropdown

### 4.3 Header del Contenido

- **Fondo:** Blanco
- **Altura:** 64px
- **Contenido:** Solo icono de campana (NotificationBell) con badge
- **Sombra:** `shadow-sm` en la parte inferior

### 4.4 Componentes

| Archivo | Descripción |
|---------|-------------|
| `MedicoLayout.tsx` | Layout principal con sidebar + header + outlet |
| `MedicoProfileDropdown.tsx` | Avatar + chevron + dropdown (Configuración, Mi Perfil, Cerrar sesión) |
| `NotificationBell.tsx` | Icono campana + badge + popover con últimas 5 notificaciones |

### 4.5 Rutas Hijas

| Ruta | Componente | Protegida |
|------|------------|-----------|
| `/medico` | Navigate → `/medico/dashboard` | No |
| `/medico/dashboard` | `MedicoDashboardPage` | Sí (rol=medico) |
| `/medico/agenda` | `MedicoAgendaPage` | Sí (rol=medico) |
| `/medico/consultas` | `MedicoCitasPage` | Sí (rol=medico) |
| `/medico/hce` | `MedicoHCEPage` | Sí (rol=medico) |
| `/medico/notificaciones` | `MedicoNotificacionesPage` | Sí (rol=medico) |
| `/medico/perfil` | `MedicoPerfilPage` | Sí (rol=medico) |

---

## 5. Protección de Rutas

### 5.1 MedicoProtectedRoute

Nuevo componente que extiende `ProtectedRoute`:

```typescript
// Verifica:
// 1. isAuthenticated === true (igual que ProtectedRoute)
// 2. rol === 'medico'
// Si no cumple → redirige a '/' (paciente) o '/medico/login' (no autenticado)
```

### 5.2 Reglas de Redirección

| Situación | Redirección |
|-----------|-------------|
| No autenticado accede a `/medico/*` | `/medico/login` |
| Paciente accede a `/medico/*` | `/` |
| Médico accede a `/login` (paciente) | `/medico/dashboard` |
| Médico ya autenticado accede a `/medico/login` | `/medico/dashboard` |

---

## 6. Dashboard Médico

### 6.1 Métricas (6 tarjetas)

| Métrica | Icono | Color | Fuente |
|---------|-------|-------|--------|
| Citas hoy | Calendar | `#2B3E59` | `citasApi.getCitasMedico()` filtradas por hoy |
| Próximas 7 días | Clock | `#f59e0b` | Filtradas fecha > hoy y <= +7 días |
| Atendidas este mes | CheckCircle | `#10b981` | Filtradas estado=atendida y mes actual |
| Tiempo prom. espera | Timer | `#8b5cf6` | Endpoint `GET /citas/medico/{id}/metricas` |
| Tasa de asistencia | TrendingUp | `#06b6d4` | (atendidas / programadas) * 100 |
| Ingresos del mes | DollarSign | `#22c55e` | Endpoint `GET /citas/medico/{id}/metricas` |

### 6.2 Layout

```
[Grid 3x2 de métricas]
[Card: Próxima cita destacada]
[Grid 2 columnas:
  - Lista: Citas de hoy
  - Lista: Próximas 7 días]
```

### 6.3 Datos Iniciales

El componente `MedicoDashboardPage` existente (`frontend/src/app/pages/medico/MedicoDashboardPage.tsx`) tiene las 3 primeras métricas. Se amplía con las 3 restantes y el layout mejorado.

---

## 7. Mi Agenda (Calendario Mensual)

### 7.1 Vista Principal

- Calendario tipo grid mensual (7 columnas × 5-6 filas)
- Días clickeables — al hacer clic se abre panel lateral (drawer)
- Días con citas marcados con puntos de color:
  - Azul = programadas
  - Verde = atendidas
  - Rojo = canceladas
- Header: título "Mi Agenda" + mes/año actual + navegación ← →
- Botón: "Configurar disponibilidad"

### 7.2 Panel Lateral del Día (Drawer)

Al hacer clic en un día del calendario:

- Fecha seleccionada
- Lista de citas de ese día
- Botón "Agregar disponibilidad" para ese día
- Horarios configurados como bloques visuales

### 7.3 Configuración de Disponibilidad

- Formulario: día de la semana, hora inicio, hora fin, especialidad, sede
- Checkbox: "Repetir semanalmente"
- Lista de disponibilidades existentes con botón eliminar
- Usa endpoints existentes: `GET /disponibilidades/medico/{medicoId}`, `POST /disponibilidades`, `DELETE /disponibilidades/{id}`

### 7.4 Componentes

| Archivo | Descripción |
|---------|-------------|
| `MedicoAgendaPage.tsx` | Página principal de agenda |
| `CalendarioMensual.tsx` | Componente reutilizable de calendario |
| `DrawerDia.tsx` | Panel lateral con detalles del día |

### 7.5 Estado Local

- `mesActual: Date` — Mes/año visible en el calendario
- `diaSeleccionado: Date | null` — Día clickeado
- `mostrarDrawer: boolean` — Controla visibilidad del panel lateral

---

## 8. Consultas (Citas del Día)

### 8.1 Estado Actual

El componente `MedicoCitasPage.tsx` ya existe con:
- Selector de fecha
- Lista de citas programadas con acciones (atendida, no asistió, cancelar)
- Historial del día

### 8.2 Mejoras a Implementar

1. **Header mejorado:**
   - Selector de fecha con navegación (← día actual →)
   - Indicador de "Hoy" resaltado

2. **Tarjeta de cita mejorada:**
   - Foto del paciente (placeholder si no tiene)
   - Nombre + documento del paciente
   - UUID de HCE (identificador interoperable)
   - Modalidad: badge "Telemedicina" 🟢 o "Presencial" 🔵
   - Estado: badge de color
   - **Botón "Iniciar Consulta"** → abre modal o redirige a HCE del paciente

3. **Panel de acciones rápido:**
   - Botones: Atendida ✅ | No asistió ❌ | Cancelar 🚫
   - Confirmación con toast antes de cada acción

### 8.3 Componentes

| Archivo | Descripción |
|---------|-------------|
| `MedicoCitasPage.tsx` | Página principal (modificar existente) |

---

## 9. Historias Clínicas (HCE)

### 9.1 Propósito

Buscar pacientes por documento y ver su historial clínico básico. Solo búsqueda, sin edición.

### 9.2 Layout

```
[Barra de búsqueda avanzada]
  Tipo documento [dropdown] + Número [input] + [Botón Buscar]

[Resultados]
  - Info del paciente: nombre, documento, UUID HCE
  - Resumen de historial: citas previas, diagnósticos, alergias

[Pacientes recientes]
  - Últimos 10 pacientes consultados
  - Click para reabrir rápidamente
```

### 9.3 Persistencia Local

- Pacientes recientes en `localStorage` con key `eps-medico-pacientes-recientes`
- Máximo 10 registros
- Formato: `{ usuario_id, nombres, apellidos, tipo_documento, numero_documento, fecha_acceso }`

### 9.4 Componentes

| Archivo | Descripción |
|---------|-------------|
| `MedicoHCEPage.tsx` | Página principal |
| `BuscadorPacientes.tsx` | Barra de búsqueda |
| `ResultadoPaciente.tsx` | Card con info del paciente |
| `PacientesRecientes.tsx` | Lista de accesos recientes |

---

## 10. Notificaciones

### 10.1 Doble Acceso

#### Icono campana en header
- Badge rojo con número de notificaciones no leídas
- Click → popover con últimas 5 notificaciones
- Cada notificación: icono + título + tiempo relativo
- Click → marca como leída + navega al destino
- Link "Ver todas" → `/medico/notificaciones`

#### Página completa `/medico/notificaciones`
- Lista cronológica de todas las notificaciones
- Filtros: Todas | No leídas | Citas | Sistema
- Cada notificación: icono tipo + título + descripción + timestamp + badge "Nuevo"
- Botón "Marcar todas como leídas"
- Paginación o scroll infinito

### 10.2 Tipos de Notificaciones

| Tipo | Icono | Descripción |
|------|-------|-------------|
| `cita_nueva` | 📅 | Nueva cita agendada por un paciente |
| `cita_cancelada` | ❌ | Cancelación de cita |
| `recordatorio` | ⏰ | Recordatorio de cita (1 hora antes) |
| `sistema` | ⚙️ | Actualización del sistema |

### 10.3 Componentes

| Archivo | Descripción |
|---------|-------------|
| `NotificationBell.tsx` | Icono + popover en header |
| `MedicoNotificacionesPage.tsx` | Página completa |
| `NotificacionItem.tsx` | Fila individual de notificación |

---

## 11. Perfil del Médico

### 11.1 Dropdown en Header del Sidebar

- **Avatar circular:** Foto del usuario (placeholder si no tiene)
- **Click en avatar:** Redirige a `/medico/perfil`
- **Chevron (v):** Abre dropdown con opciones
- **Opciones del dropdown:**
  - Configuración
  - Mi Perfil
  - Cerrar sesión

### 11.2 Página de Perfil `/medico/perfil`

- Información personal del médico (nombre, documento, especialidad)
- Foto de perfil (con opción de cambiar)
- Información de contacto
- Horarios de atención configurados

### 11.3 Componentes

| Archivo | Descripción |
|---------|-------------|
| `MedicoProfileDropdown.tsx` | Avatar + chevron + dropdown |
| `MedicoPerfilPage.tsx` | Página de perfil completa |

---

## 12. Types — Nuevos Tipos

```typescript
// Dashboard médico
export interface MetricasMedico {
  citas_hoy: number;
  proximas_7_dias: number;
  atendidas_mes: number;
  tiempo_espera_promedio_min: number;
  tasa_asistencia_pct: number;
  ingresos_mes: number;
}

// Cita extendida para médico
export interface CitaMedico extends Cita {
  modalidad: 'telemedicina' | 'presencial';
  paciente_nombre?: string;
  paciente_documento?: string;
  paciente_uuid_hce?: string;
}

// Notificación
export interface Notificacion {
  notificacion_id: string;
  medico_id: string;
  tipo: 'cita_nueva' | 'cita_cancelada' | 'recordatorio' | 'sistema';
  titulo: string;
  descripcion: string;
  leida: boolean;
  enlace?: string;
  creado_en: string;
}

// Disponibilidad extendida
export interface DisponibilidadMedico extends Disponibilidad {
  especialidad_nombre?: string;
  sede_nombre?: string;
}
```

---

## 13. API Client — Nuevos Endpoints

```typescript
// Auth
authApi.getMedicoId()                    // GET /auth/medico-id → { medico_id }

// Citas
citasApi.getCitasMedico(medicoId, filters)  // GET /citas/medico/{medicoId}
citasApi.getMetricasMedico(medicoId)        // GET /citas/medico/{medicoId}/metricas

// Usuarios
userApi.buscarPorDocumento(tipo, numero)    // GET /usuarios/buscar?tipo_documento=X&numero_documento=Y

// Notificaciones
notificacionesApi.getByMedico(medicoId)     // GET /notificaciones/medico/{medicoId}
notificacionesApi.marcarLeida(id)           // PATCH /notificaciones/{id}/leida
notificacionesApi.marcarTodasLeidas(medicoId) // PATCH /notificaciones/medico/{medicoId}/leer-todas
```

---

## 14. Routing

### 14.1 Estructura

```typescript
// Rutas médico (NUEVAS)
{
  path: '/medico/login',
  Component: MedicoLoginPage  // Sin sidebar, página completa
},
{
  path: '/medico',
  Component: MedicoLayout,  // Con sidebar
  children: [
    { index: true, element: <Navigate to="dashboard" replace /> },
    {
      path: 'dashboard',
      element: <MedicoProtectedRoute><MedicoDashboardPage /></MedicoProtectedRoute>
    },
    {
      path: 'agenda',
      element: <MedicoProtectedRoute><MedicoAgendaPage /></MedicoProtectedRoute>
    },
    {
      path: 'consultas',
      element: <MedicoProtectedRoute><MedicoCitasPage /></MedicoProtectedRoute>
    },
    {
      path: 'hce',
      element: <MedicoProtectedRoute><MedicoHCEPage /></MedicoProtectedRoute>
    },
    {
      path: 'notificaciones',
      element: <MedicoProtectedRoute><MedicoNotificacionesPage /></MedicoProtectedRoute>
    },
    {
      path: 'perfil',
      element: <MedicoProtectedRoute><MedicoPerfilPage /></MedicoProtectedRoute>
    },
    { path: '*', Component: NotFoundPage }
  ]
}
```

### 14.2 Protección

- `MedicoProtectedRoute` verifica `isAuthenticated` + `rol === 'medico'`
- Redirecciones según reglas en sección 5.2

---

## 15. Backend — Endpoints Nuevos

| Service | Endpoint | Método | Descripción |
|---------|----------|--------|-------------|
| auth-service | `/auth/medico-id` | GET | Devuelve medico_id del usuario logueado |
| auth-service | Login response | - | Agregar campo `rol` en respuesta |
| appointments | `/citas/medico/{id}/metricas` | GET | Métricas del dashboard |
| appointments | `/citas/medico/{id}/hoy` | GET | Citas del día (optimización) |
| user-service | `/usuarios/buscar` | GET | Búsqueda por documento |
| notifications | `/notificaciones/medico/{id}` | GET | Lista notificaciones |
| notifications | `/notificaciones/{id}/leida` | PATCH | Marcar leída |
| notifications | `/notificaciones/medico/{id}/leer-todas` | PATCH | Marcar todas leídas |

---

## 16. Archivos a Crear

| Archivo | Descripción |
|---------|-------------|
| `MedicoLoginPage.tsx` | Página de login médico |
| `MedicoLayout.tsx` | Reemplazar existente — sidebar + header |
| `MedicoProfileDropdown.tsx` | Avatar + dropdown |
| `NotificationBell.tsx` | Campana + badge + popover |
| `MedicoAgendaPage.tsx` | Calendario + disponibilidad |
| `CalendarioMensual.tsx` | Componente calendario |
| `DrawerDia.tsx` | Panel lateral del día |
| `MedicoHCEPage.tsx` | Búsqueda HCE |
| `BuscadorPacientes.tsx` | Barra de búsqueda |
| `ResultadoPaciente.tsx` | Card de resultado |
| `PacientesRecientes.tsx` | Lista de recientes |
| `MedicoNotificacionesPage.tsx` | Página de notificaciones |
| `NotificacionItem.tsx` | Fila de notificación |
| `MedicoPerfilPage.tsx` | Página de perfil |
| `MedicoProtectedRoute.tsx` | Guard de rutas médicas |

## 17. Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `authStore.ts` | Agregar `rol`, `medicoId`, `setRol`, `setMedicoId` |
| `types/index.ts` | Agregar `MetricasMedico`, `CitaMedico`, `Notificacion`, `DisponibilidadMedico` |
| `apiClient.ts` | Agregar ~10 endpoints nuevos |
| `routes.tsx` | Agregar árbol de rutas `/medico/*` |
| `MedicoDashboardPage.tsx` | Mejorar con 6 métricas + layout mejorado |
| `MedicoCitasPage.tsx` | Agregar modalidad, UUID HCE, botón iniciar consulta |

---

## 18. Dependencias Externas

No se agregan dependencias nuevas. Se usa:
- React 18 + Vite + TypeScript
- TanStack Query (data fetching)
- Zustand (state management)
- React Router v7 (navegación)
- Lucide React (iconos)
- Tailwind CSS (estilos)
- Sonner (toasts)

---

## 19. Criterios de Aceptación

1. ✅ Login médico accesible en `/medico/login` con diseño propio
2. ✅ Auth store maneja `rol` y `medicoId` correctamente
3. ✅ MedicoLayout muestra sidebar con 5 secciones + perfil
4. ✅ Dashboard muestra 6 métricas con datos reales
5. ✅ Mi Agenda muestra calendario mensual interactivo
6. ✅ Calendario permite configurar disponibilidad por día
7. ✅ Consultas muestra citas del día con modalidad y acciones
8. ✅ HCE permite buscar pacientes por documento
9. ✅ HCE muestra lista de pacientes recientes
10. ✅ Notificaciones accesibles desde header (dropdown) y página completa
11. ✅ Perfil con avatar dropdown en header del sidebar
12. ✅ Rutas protegidas — solo médicos acceden a `/medico/*`
13. ✅ No se rompe funcionalidad existente de pacientes

---

## 20. Fuera de Alcance (Fase Futura)

- Edición de historias clínicas
- Subida de archivos médicos (imágenes, laboratorios)
- Telemedicina (videoconsulta)
- Chat con pacientes
- Gestión de recetas médicas
- Reportes y analytics avanzados
- Multi-idioma
