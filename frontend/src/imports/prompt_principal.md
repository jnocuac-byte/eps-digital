# PROYECTO: EPS Digital - Plataforma de Asignación de Citas Médicas

## Contexto General
Plataforma web para afiliados de EPS en Colombia que permite gestionar citas médicas con asistente virtual de IA.

## Stack Tecnológico para Generar
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui + Lucide icons
- React Router DOM (rutas)
- Zustand (estado global: auth, usuario)
- TanStack Query (fetching y caché)
- Axios (HTTP client con interceptors para JWT)
- React Hook Form + Zod (formularios y validación)

## URLs de los Servicios (Producción)
- Auth Service: https://eps-auth-service.onrender.com
- User Service: https://eps-user-service.onrender.com
- Citas Service: https://eps-citas-service.onrender.com
- Catálogo Service: https://eps-catalogo-service.onrender.com
- AI/NLP Service: https://eps-ainlp-service.onrender.com
- Notificaciones Service: https://eps-notifications-service.onrender.com

## Flujo de Autenticación
1. Registro: POST /auth/register → obtiene usuario_id
2. Crear perfil: POST /usuarios con usuario_id
3. Login: POST /auth/login/documento (tipo_documento + numero_documento + password)
4. Almacenar token JWT en localStorage/sessionStorage
5. Incluir token en header Authorization: Bearer {token}

## Estructura de Navegación (6 secciones + auth)
- Inicio (pública)
- Mi Perfil (privada)
- Citas Médicas (privada) → submenús: Agendar, Ver, Cancelar/Reprogramar, Historial
- Asistente Virtual (privada)
- Servicios (pública/privada)
- Ayuda (pública)
- Iniciar Sesión / Registrarme (públicas, cambian a Cerrar Sesión cuando autenticado)

## Requisitos de Responsividad
- Desktop first (1440px)
- Tablet (768px)
- Móvil (375px)
- Menú colapsable en móvil