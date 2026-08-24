# Plan de Implementación: Portal Médico EPS Digital

**Fecha:** 2026-05-28
**Dependencias del spec:** `2026-05-28-portal-medico-design.md`

---

## Fase 0: Fundamentos (Sin dependencias)

### Tarea 0.1: Extender Auth Store
**Archivos:** `frontend/src/app/stores/authStore.ts`
**Cambios:**
- Agregar `rol: string | null` al estado
- Agregar `medicoId: string | null` al estado
- Agregar acción `setRol(rol: string)`
- Agregar acción `setMedicoId(medicoId: string)`
- Actualizar `login()` para aceptar `rol` opcional
- Actualizar `logout()` para limpiar `rol` y `medicoId`

### Tarea 0.2: Agregar Nuevos Types
**Archivos:** `frontend/src/app/types/index.ts`
**Cambios:**
- Agregar interfaz `MetricasMedico`
- Agregar interfaz `CitaMedico` (extiende `Cita`)
- Agregar interfaz `Notificacion`
- Agregar interfaz `DisponibilidadMedico` (extiende `Disponibilidad`)

### Tarea 0.3: Agregar Endpoints al API Client
**Archivos:** `frontend/src/app/lib/apiClient.ts`
**Cambios:**
- Crear cliente `notificacionesClient` con `createClient(NOTIFICATIONS_URL, true)`
- Agregar objeto `notificacionesApi` con métodos:
  - `getByMedico(medicoId)` → GET `/notificaciones/medico/{medicoId}`
  - `marcarLeida(id)` → PATCH `/notificaciones/{id}/leida`
  - `marcarTodasLeidas(medicoId)` → PATCH `/notificaciones/medico/{medicoId}/leer-todas`
- Agregar a `citasApi`:
  - `getMetricasMedico(medicoId)` → GET `/citas/medico/{medicoId}/metricas`
- Agregar a `userApi`:
  - `buscarPorDocumento(tipo, numero)` → GET `/usuarios/buscar?tipo_documento=X&numero_documento=Y`

---

## Fase 1: Login Médico

### Tarea 1.1: Crear MedicoLoginPage
**Archivos:** `frontend/src/app/pages/medico/MedicoLoginPage.tsx`
**Dependencias:** Fase 0 (auth store con `rol`)
**Descripción:**
- Página completa centrada (sin sidebar)
- Mismo formulario que LoginPage actual (tipo_doc, número_doc, password)
- Branding médico: logo HeartPulse, título "EPS Digital", subtítulo "Portal Médico"
- Color primario: `#2B3E59`
- Fondo: `#F5F5F5`
- Al hacer submit:
  - POST a `authApi.login(data)` (mismo endpoint)
  - Guardar `rol` en auth store (del response o default 'paciente')
  - Si `rol === 'medico'`, redirigir a `/medico/dashboard`
  - Si no, redirigir a `/` (paciente)
- Si ya autenticado y es médico, redirigir a `/medico/dashboard`
- Link a `/login` para pacientes

### Tarea 1.2: Crear MedicoProtectedRoute
**Archivos:** `frontend/src/app/components/MedicoProtectedRoute.tsx`
**Dependencias:** Fase 0 (auth store con `rol`)
**Descripción:**
- Verificar `isAuthenticated === true`
- Verificar `rol === 'medico'`
- Si no autenticado → redirigir a `/medico/login`
- Si autenticado pero no es médico → redirigir a `/`
- Wrapper para componentes protegidos

---

## Fase 2: Layout y Navegación

### Tarea 2.1: Crear MedicoProfileDropdown
**Archivos:** `frontend/src/app/components/medico/MedicoProfileDropdown.tsx`
**Dependencias:** Fase 0 (auth store)
**Descripción:**
- Avatar circular con foto del usuario (placeholder si no tiene)
- Click en avatar → navegar a `/medico/perfil`
- Chevron (v) → abrir dropdown
- Dropdown opciones: Configuración, Mi Perfil, Cerrar sesión
- Click en "Cerrar sesión" → `logout()` + redirigir a `/medico/login`

### Tarea 2.2: Crear NotificationBell
**Archivos:** `frontend/src/app/components/medico/NotificationBell.tsx`
**Dependencias:** Fase 0 (apiClient con notificacionesApi)
**Descripción:**
- Icono campana (Lucide Bell)
- Badge rojo con número de no leídas
- Click → popover con últimas 5 notificaciones
- Cada notificación: icono tipo + título + tiempo relativo
- Click en notificación → marcar leída + navegar
- Link "Ver todas" → `/medico/notificaciones`
- Fetch: `notificacionesApi.getByMedico(medicoId)`

### Tarea 2.3: Reemplazar MedicoLayout
**Archivos:** `frontend/src/app/components/MedicoLayout.tsx`
**Dependencias:** Tareas 2.1, 2.2
**Descripción:**
- Sidebar izquierdo (224px, `#2B3E59`)
  - Logo: HeartPulse + "EPS Digital" + "Panel Médico"
  - Nav: Dashboard, Mi Agenda, Consultas, Historias Clínicas, Notificaciones
  - Perfil: MedicoProfileDropdown (abajo)
- Header derecho (64px, blanco, `shadow-sm`)
  - NotificationBell (derecha)
- Main content: `{children}` con `<Outlet />`
- Active link highlighting

### Tarea 2.4: Actualizar Routes
**Archivos:** `frontend/src/app/routes.tsx`
**Dependencias:** Tareas 1.1, 1.2, 2.3
**Descripción:**
- Agregar ruta `/medico/login` (fuera del layout)
- Agregar ruta `/medico` con `MedicoLayout` como componente
- Agregar children protegidos con `MedicoProtectedRoute`
- Rutas: dashboard, agenda, consultas, hce, notificaciones, perfil
- Redirect index a `/medico/dashboard`

---

## Fase 3: Dashboard Médico

### Tarea 3.1: Mejorar MedicoDashboardPage
**Archivos:** `frontend/src/app/pages/medico/MedicoDashboardPage.tsx`
**Dependencias:** Fase 0 (types, apiClient)
**Descripción:**
- Grid 3x2 de métricas (6 cards)
- Cada card: icono + label + valor
- Colores según spec (sección 6.1)
- Card de "Próxima cita destacada"
- Grid 2 columnas: "Citas de hoy" + "Próximas 7 días"
- Fetch de métricas: `citasApi.getMetricasMedico(medicoId)`
- Loading state con spinner
- Empty states informativos

---

## Fase 4: Mi Agenda (Calendario)

### Tarea 4.1: Crear CalendarioMensual
**Archivos:** `frontend/src/app/components/medico/CalendarioMensual.tsx`
**Dependencias:** Ninguna (componente puro)
**Descripción:**
- Grid 7 columnas (Lun-Dom)
- 5-6 filas según el mes
- Navegación ← → para cambiar mes
- Display de mes/año actual
- Días clickeables
- Días con puntos de color (citas)
- Highlight en día actual
- Días fuera del mes atenuados

### Tarea 4.2: Crear DrawerDia
**Archivos:** `frontend/src/app/components/medico/DrawerDia.tsx`
**Dependencias:** Fase 0 (apiClient)
**Descripción:**
- Panel lateral derecho (320px)
- Header con fecha seleccionada + botón cerrar (X)
- Lista de citas del día
- Botón "Agregar disponibilidad"
- Bloques visuales de horarios
- Close on escape o click outside

### Tarea 4.3: Crear MedicoAgendaPage
**Archivos:** `frontend/src/app/pages/medico/MedicoAgendaPage.tsx`
**Dependencias:** Tareas 4.1, 4.2
**Descripción:**
- Header: "Mi Agenda" + mes/año + navegación
- Botón "Configurar disponibilidad"
- CalendarioMensual
- DrawerDia (condicional)
- Estado: mesActual, diaSeleccionado, mostrarDrawer
- Fetch disponibilidades: `catalogoApi.getDisponibilidadesMedico(medicoId)`

---

## Fase 5: Consultas (Citas del Día)

### Tarea 5.1: Mejorar MedicoCitasPage
**Archivos:** `frontend/src/app/pages/medico/MedicoCitasPage.tsx`
**Dependencias:** Fase 0 (types, apiClient)
**Descripción:**
- Header mejorado con navegación de fecha
- Indicador "Hoy" resaltado
- Tarjeta de cita mejorada:
  - Foto placeholder del paciente
  - Nombre + documento
  - UUID HCE (badge)
  - Modalidad badge (Telemedicina/Presencial)
  - Estado badge
  - Botón "Iniciar Consulta"
- Panel de acciones rápido
- Confirmación con toast

---

## Fase 6: Historias Clínicas (HCE)

### Tarea 6.1: Crear BuscadorPacientes
**Archivos:** `frontend/src/app/components/medico/BuscadorPacientes.tsx`
**Dependencias:** Fase 0 (apiClient)
**Descripción:**
- Dropdown tipo documento (CC, CE, PA, TI)
- Input número de documento
- Botón "Buscar"
- Loading state
- Resultado: info del paciente

### Tarea 6.2: Crear ResultadoPaciente
**Archivos:** `frontend/src/app/components/medico/ResultadoPaciente.tsx`
**Dependencias:** Fase 0 (types)
**Descripción:**
- Card con info del paciente
- Nombre, apellidos, documento
- UUID HCE
- Resumen: citas previas, alergias, enfermedades
- Botón "Ver historial completo"

### Tarea 6.3: Crear PacientesRecientes
**Archivos:** `frontend/src/app/components/medico/PacientesRecientes.tsx`
**Dependencias:** Ninguna (localStorage)
**Descripción:**
- Lista de últimos 10 pacientes
- Cada uno: nombre + documento + fecha de acceso
- Click para reabrir
- Botón "Limpiar historial"

### Tarea 6.4: Crear MedicoHCEPage
**Archivos:** `frontend/src/app/pages/medico/MedicoHCEPage.tsx`
**Dependencias:** Tareas 6.1, 6.2, 6.3
**Descripción:**
- Header: "Historias Clínicas"
- BuscadorPacientes
- ResultadoPaciente (condicional)
- PacientesRecientes

---

## Fase 7: Notificaciones

### Tarea 7.1: Crear NotificacionItem
**Archivos:** `frontend/src/app/components/medico/NotificacionItem.tsx`
**Dependencias:** Fase 0 (types)
**Descripción:**
- Fila de notificación
- Icono según tipo
- Título + descripción
- Timestamp relativo
- Badge "Nuevo" si no leída
- Click → marcar leída

### Tarea 7.2: Crear MedicoNotificacionesPage
**Archivos:** `frontend/src/app/pages/medico/MedicoNotificacionesPage.tsx`
**Dependencias:** Tareas 7.1, Fase 0 (apiClient)
**Descripción:**
- Header: "Notificaciones"
- Filtros: Todas | No leídas | Citas | Sistema
- Lista de NotificacionItem
- Botón "Marcar todas como leídas"
- Paginación o scroll infinito
- Empty state

---

## Fase 8: Perfil

### Tarea 8.1: Crear MedicoPerfilPage
**Archivos:** `frontend/src/app/pages/medico/MedicoPerfilPage.tsx`
**Dependencias:** Fase 0 (apiClient, types)
**Descripción:**
- Header: "Mi Perfil"
- Sección info personal: nombre, documento, especialidad
- Foto de perfil (placeholder + botón cambiar)
- Info de contacto: email, teléfono
- Horarios de atención configurados
- Botón "Guardar cambios"

---

## Orden de Ejecución Recomendado

```
Fase 0 (Fundamentos) → Sin dependencias, hacer primero
  ↓
Fase 1 (Login) → Depende de Fase 0
  ↓
Fase 2 (Layout) → Depende de Fase 1
  ↓
Fases 3-8 → Independientes entre sí, pueden hacerse en paralelo
  - Fase 3 (Dashboard)
  - Fase 4 (Agenda)
  - Fase 5 (Consultas)
  - Fase 6 (HCE)
  - Fase 7 (Notificaciones)
  - Fase 8 (Perfil)
```

---

## Estimación de Esfuerzo

| Fase | Tareas | Complejidad |
|------|--------|-------------|
| 0 | 3 | Baja |
| 1 | 2 | Media |
| 2 | 4 | Alta |
| 3 | 1 | Media |
| 4 | 3 | Alta |
| 5 | 1 | Media |
| 6 | 4 | Media |
| 7 | 2 | Baja |
| 8 | 1 | Baja |
| **Total** | **21** | |

---

## Notas de Implementación

1. **Backend no bloqueante:** Las fases 3-8 dependen de endpoints que aún no existen en el backend. Se puede implementar el frontend con datos mock o usando los endpoints existentes donde sea posible.

2. **Reutilización:** El componente `MedicoCitasPage.tsx` ya existe — se modifica en lugar de crear nuevo.

3. **Auth Store:** Los cambios en el store son mínimos y no rompen funcionalidad existente.

4. **Testing:** Cada fase puede probarse independientemente después de completarse.

5. **Despliegue:** El routing completo debe estar configurado antes de que el portal sea accesible.
