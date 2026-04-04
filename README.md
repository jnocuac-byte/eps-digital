# 🏥 EPS Digital - Plataforma Tecnológica de Asignación de Citas Médicas

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-28.0-2496ED?logo=docker)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?logo=render)](https://render.com)

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Microservicios](#microservicios)
- [Tecnologías Utilizadas](#tecnologías-utilizadas)
- [Modelo de Datos](#modelo-de-datos)
- [Despliegue](#despliegue)
- [Guía de Inicio Rápido](#guía-de-inicio-rápido)
- [Documentación de la API](#documentación-de-la-api)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Equipo](#equipo)
- [Licencia](#licencia)

---

## 🎯 Visión General

**EPS Digital** es una plataforma web integral para la gestión de citas médicas en Entidades Promotoras de Salud (EPS) de Colombia. La plataforma integra **inteligencia artificial**, **automatización de procesos** y un **asistente virtual basado en NLP** para optimizar el proceso de agendamiento, reducir tiempos de espera y mejorar la experiencia del usuario afiliado.

### Problemática Abordada

Según datos de la Superintendencia Nacional de Salud, en enero de 2024 se registraron más de **110,994 quejas** de usuarios de EPS en Colombia, evidenciando un crecimiento del **42.04%** respecto al mismo período de 2023. Las principales causas incluyen:

- Procesos de agendamiento manuales e ineficientes
- Tiempos de espera de 10-15 minutos por interacción telefónica
- Falta de integración entre sistemas de EPS e IPS
- Ausencia de canales digitales accesibles 24/7

### Solución Propuesta

EPS Digital ofrece una solución completa mediante:

- 🤖 **Asistente Virtual con IA** (clasificación de síntomas y nivel de urgencia)
- 📅 **Gestión inteligente de citas** (agendar, cancelar, reprogramar, historial)
- 🏥 **Catálogo de servicios** con búsqueda y disponibilidad en tiempo real
- 👤 **Perfil de usuario** con información personal, médica y de afiliación
- 📧 **Notificaciones automáticas** vía correo electrónico
- 🔐 **Autenticación segura** con JWT y 2FA opcional

---

## 🏗️ Arquitectura del Sistema

La plataforma sigue una **arquitectura de microservicios** con los siguientes componentes:

```text
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (React + Vite)                                        │
│ https://eps-digital-cn2h.onrender.com                          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ API Gateway (Nginx)                                             │
│ Enrutamiento + Autenticación                                    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                 ┌────────────┼────────────┬────────────┬────────────┐
                 ▼            ▼            ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
            │ Auth      │ │ User      │ │ Citas     │ │ Catálogo  │ │ IA/NLP    │
            │ Service   │ │ Service   │ │ Service   │ │ Service   │ │ Service   │
            │ :8001     │ │ :8002     │ │ :8003     │ │ :8004     │ │ :8005     │
            └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
                  │             │             │             │             │
                  ▼             ▼             ▼             ▼             ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
            │ PostgreSQL│ │ PostgreSQL│ │ PostgreSQL│ │ PostgreSQL│ │ PostgreSQL│
            │ eps_auth  │ │ eps_user  │ │ eps_citas │ │eps_catalogo│ │ eps_ainlp │
            └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Notificaciones    │
                    │ Service           │
                    │ :8006             │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ RabbitMQ          │
                    │ (Mensajería)      │
                    └───────────────────┘
```

---

## 🔧 Microservicios

| Servicio | Puerto | Responsabilidad | Tecnologías |
|----------|--------|----------------|-------------|
| **Auth Service** | 8001 | Autenticación JWT, registro, 2FA, recuperación de contraseña | FastAPI, JWT, bcrypt |
| **User Service** | 8002 | Gestión de perfiles, información médica, afiliación | FastAPI, SQLAlchemy |
| **Citas Service** | 8003 | Agendar, cancelar, reprogramar, historial de citas | FastAPI, RabbitMQ |
| **Catálogo Service** | 8004 | Servicios, especialidades, médicos, disponibilidad | FastAPI, PostgreSQL |
| **IA/NLP Service** | 8005 | Chatbot, clasificación de síntomas, análisis de urgencia | FastAPI, Groq AI |
| **Notificaciones Service** | 8006 | Envío de correos (confirmaciones, recordatorios) | FastAPI, SendGrid, RabbitMQ |

---

## 💻 Tecnologías Utilizadas

### Backend

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.12 | Lenguaje principal |
| **FastAPI** | 0.135 | Framework web para microservicios |
| **SQLAlchemy** | 2.0 | ORM para base de datos |
| **PostgreSQL** | 15 | Base de datos relacional |
| **Alembic** | 1.18 | Migraciones de base de datos |
| **JWT** | - | Autenticación basada en tokens |
| **bcrypt** | - | Hashing de contraseñas |
| **RabbitMQ** | 3.12 | Message broker para comunicación asíncrona |
| **SendGrid** | - | Envío de correos electrónicos |
| **Groq AI** | - | Procesamiento de lenguaje natural (NLP) |

### Frontend

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **React** | 18.3 | Framework frontend |
| **TypeScript** | 5.x | Tipado estático |
| **Vite** | 6.3 | Build tool y servidor de desarrollo |
| **Tailwind CSS** | 4.1 | Framework de estilos |
| **shadcn/ui** | - | Componentes UI |
| **Zustand** | 5.0 | Manejo de estado global |
| **TanStack Query** | 5.96 | Fetching y caché de datos |
| **React Hook Form** | 7.55 | Manejo de formularios |
| **Zod** | 4.3 | Validación de datos |
| **Axios** | 1.14 | Cliente HTTP |

### DevOps

| Tecnología | Propósito |
|------------|-----------|
| **Docker** | Contenerización de microservicios |
| **Docker Compose** | Orquestación local |
| **GitHub Actions** | CI/CD (planificado) |
| **Render** | Despliegue en la nube (PaaS) |
| **Git Flow** | Estrategia de ramas |

---

## 📊 Modelo de Datos

### Auth Service (Base de datos: `eps_auth`)
- `credenciales`: credenciales de acceso, JWT, 2FA
- `token_recuperacion`: tokens para recuperación de contraseña
- `registro_2fa`: códigos OTP para autenticación de dos factores
- `log_autenticacion`: auditoría de eventos de autenticación

### User Service (Base de datos: `eps_user`)
- `usuarios`: datos personales del afiliado
- `informacion_medica`: tipo de sangre, alergias, enfermedades crónicas
- `afiliaciones`: tipo de afiliación, número de póliza, estado

### Citas Service (Base de datos: `eps_citas`)
- `citas`: registro de citas médicas
- `historial_estado`: trazabilidad de cambios de estado
- `recordatorios`: programación de recordatorios 24h antes

### IA/NLP Service (Base de datos: `eps_ainlp`)
- `conversacion`: sesiones de chat con el asistente
- `mensaje`: mensajes individuales de la conversación
- `clasificacion_sintomas`: resultados del análisis de síntomas

### Catálogo Service (Base de datos: `eps_catalogo`)
- `servicios`: servicios médicos disponibles
- `especialidades`: especialidades médicas
- `medicos`: información de profesionales de salud
- `medico_especialidades`: relación N:M entre médicos y especialidades
- `disponibilidad`: horarios de atención por médico
- `sedes`: sedes físicas de la EPS

---

## 🌐 Despliegue

### URLs de Producción

| Servicio | URL |
|----------|-----|
| **Frontend** | https://eps-digital-cn2h.onrender.com |
| **Auth Service** | https://eps-digital.onrender.com/docs |
| **User Service** | https://eps-user-service.onrender.com/docs |
| **Citas Service** | https://eps-appointments-service.onrender.com/docs |
| **Catálogo Service** | https://eps-catalog-service.onrender.com/docs |
| **IA/NLP Service** | https://eps-ainlp-service.onrender.com/docs |
| **Notificaciones Service** | https://eps-notification-service.onrender.com/docs |

### Infraestructura

- **Plataforma**: Render (PaaS)
- **Base de datos**: PostgreSQL (instancias independientes por servicio)
- **Contenerización**: Docker
- **Variables de entorno**: Configuradas en Render Dashboard

---

## 🚀 Guía de Inicio Rápido

### Requisitos Previos

- Docker y Docker Compose
- Node.js 18+ y npm
- Python 3.12+
- Git

### Clonar el Repositorio

```bash
git clone https://github.com/jnocuac-byte/eps-digital.git
cd eps-digital
```

### Levantar los Microservicios (Desarrollo Local)

```bash
# Para cada servicio
cd services/auth-service
docker-compose up -d --build

cd ../user-service
docker-compose up -d --build

# Repetir para cada servicio
```

### Configurar el Frontend

```bash
cd frontend
npm install
npm run dev
```

### Variables de Entorno Requeridas

#### Auth Service (`.env`)

```env
DATABASE_URL=postgresql://eps_user:eps_password@auth-db:5432/eps_auth
JWT_SECRET_KEY=tu_clave_secreta
USER_SERVICE_URL=http://user-service:8002
```

#### User Service (`.env`)

```env
DATABASE_URL=postgresql://eps_user:eps_password@user-db:5432/eps_user
JWT_SECRET_KEY=tu_clave_secreta
```

#### IA/NLP Service (`.env`)

```env
DATABASE_URL=postgresql://eps_user:eps_password@ainlp-db:5432/eps_ainlp
GROQ_API_KEY=tu_api_key_de_groq
JWT_SECRET_KEY=tu_clave_secreta
```

#### Frontend (`.env.production`)

```env
VITE_AUTH_URL=https://eps-auth-service.onrender.com
VITE_USER_URL=https://eps-user-service.onrender.com
VITE_CITAS_URL=https://eps-citas-service.onrender.com
VITE_CATALOGO_URL=https://eps-catalogo-service.onrender.com
VITE_AI_URL=https://eps-ainlp-service.onrender.com
```

---

## 📚 Documentación de la API

Cada microservicio expone su documentación interactiva en `/docs`:

| Servicio | Documentación |
|----------|---------------|
| Auth Service | https://eps-auth-service.onrender.com/docs |
| User Service | https://eps-user-service.onrender.com/docs |
| Citas Service | https://eps-citas-service.onrender.com/docs |
| Catálogo Service | https://eps-catalogo-service.onrender.com/docs |
| IA/NLP Service | https://eps-ainlp-service.onrender.com/docs |

### Endpoints Principales

#### Autenticación (Auth Service)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/register` | Registro de nuevo usuario |
| POST | `/auth/login/documento` | Inicio de sesión por documento + contraseña |
| POST | `/auth/refresh` | Renovación de token JWT |
| POST | `/auth/recover` | Solicitud de recuperación de contraseña |
| POST | `/auth/reset-password` | Restablecimiento de contraseña |
| GET | `/auth/me` | Obtener información del usuario autenticado |

#### Perfil de Usuario (User Service)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/usuarios` | Crear perfil de usuario |
| GET | `/usuarios/{usuario_id}` | Obtener perfil completo |
| GET | `/usuarios/buscar` | Buscar usuario por documento |
| PUT | `/usuarios/{usuario_id}` | Actualizar datos personales |
| GET | `/usuarios/{usuario_id}/completo` | Obtener perfil con datos médicos y afiliación |

#### Gestión de Citas (Citas Service)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/citas` | Agendar nueva cita |
| GET | `/citas/usuario/{usuario_id}` | Ver citas programadas |
| POST | `/citas/{cita_id}/cancelar` | Cancelar cita |
| POST | `/citas/{cita_id}/reprogramar` | Reprogramar cita |
| GET | `/citas/{cita_id}/historial` | Historial de cambios de estado |

#### Asistente Virtual (IA/NLP Service)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/chat` | Enviar mensaje al asistente |
| GET | `/chat/conversaciones/{usuario_id}` | Listar conversaciones del usuario |
| GET | `/chat/conversacion/{conversacion_id}/mensajes` | Obtener mensajes de una conversación |
| GET | `/chat/clasificacion/{conversacion_id}` | Obtener clasificación de síntomas |

#### Catálogo (Catálogo Service)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/servicios` | Listar servicios médicos |
| GET | `/especialidades` | Listar especialidades (con filtro por servicio) |
| GET | `/medicos` | Listar médicos (con filtro por especialidad) |
| GET | `/disponibilidades/medico/{medico_id}` | Ver disponibilidad de un médico |

---

## 📁 Estructura del Proyecto

```text
eps-digital/
├── frontend/                      # Aplicación React
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/        # Componentes reutilizables
│   │   │   ├── lib/               # Configuraciones (API, QueryClient)
│   │   │   ├── pages/             # Páginas de la aplicación
│   │   │   ├── stores/            # Zustand stores
│   │   │   ├── App.tsx
│   │   │   └── routes.tsx
│   │   ├── styles/                # Estilos globales
│   │   └── main.tsx
│   ├── .env.production
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
├── services/                      # Microservicios backend
│   ├── auth-service/              # Servicio de autenticación
│   │   ├── app/
│   │   ├── alembic/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── requirements.txt
│   ├── user-service/              # Servicio de usuarios
│   ├── appointments-service/      # Servicio de citas
│   ├── catalog-service/           # Servicio de catálogo
│   ├── ai-nlp-service/            # Servicio de IA/NLP
│   └── notifications-service/     # Servicio de notificaciones
│
├── .gitignore
└── README.md
```

---

## 👥 Equipo

| Nombre | Rol | Contacto |
|--------|-----|----------|
| Juan Esteban Nocua | Desarrollador Backend & DevOps | jnocuac@ucentral.edu.co |
| Andrés Ramos Ricaurte | Desarrollador Full Stack | aramosr@ucentral.edu.co |
| Santiago Pardo | Desarrollador Frontend | spardoa@ucentral.edu.co |

**Institución:** Universidad Central  
**Asignatura:** Práctica de Ingeniería III  
**Docente:** Juan Carlos Franco Rodriguez  
**Año:** 2026

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más información.

---

## 🙏 Agradecimientos

- Universidad Central por el respaldo académico
- GitHub Education por las herramientas gratuitas
- Render por el plan gratuito de despliegue
- Groq por las APIs de IA

---

## 📞 Contacto y Soporte

- **Frontend:** https://eps-digital-cn2h.onrender.com  
- **Repositorio:** https://github.com/jnocuac-byte/eps-digital  
- **Documentación API:** https://eps-auth-service.onrender.com/docs

---

## 🔮 Trabajo Futuro

- Implementar autenticación de dos factores (2FA) completa
- Integrar pasarela de pagos en línea
- Desarrollar aplicación móvil nativa
- Implementar HL7 FHIR para interoperabilidad
- Migrar a Kubernetes para orquestación avanzada
- Añadir pruebas automatizadas (unitarias e integración)
- Implementar monitoreo con Prometheus + Grafana

---

⭐ Si este proyecto te ha sido útil, ¡no olvides dejar una estrella en GitHub! ⭐