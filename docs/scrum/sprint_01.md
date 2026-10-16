# Bitácora Scrum — EPS Digital

**Product Owner:** EPS Digital
**Scrum Master:** Andrés Ramos
**Tablero de trabajo:** GitHub Projects
**Repositorio:** `jnocuac-byte/eps-digital`
**Rama de desarrollo de Andrés:** `Andres`
**Rama principal:** `main`

---

## 1. Sprint inicial — Infraestructura y base de conocimiento

**Periodo del Sprint:** 18/09/2026 al 25/09/2026

### 1.1. Acta de Sprint Planning — Planeación

**Fecha de la reunión:** 18/09/2026
**Asistentes:** Juan Esteban Nocua y Santiago Pardo

#### Sprint Goal — Meta del Sprint

Desplegar la infraestructura base de la plataforma mediante orquestación y un pipeline automatizado, e inicializar la base de conocimiento vectorial para el agente.

#### Historias de usuario comprometidas y tareas

**H-16: Orquestación en Kubernetes — 13 puntos**
**Estado reportado:** In progress

*Tareas a ejecutar:*

- Definir la arquitectura del clúster y seleccionar la plataforma de ejecución.
- Crear los manifiestos de Deployment y Service para los seis microservicios.
- Configurar el Ingress Controller para unificar la entrada mediante una URL.
- Implementar sondas de salud de tipo liveness y readiness.
- Configurar Persistent Volumes y Persistent Volume Claims para PostgreSQL y Redis.

**H-18: Base de conocimiento vectorial — 8 puntos**
**Estado reportado:** In progress

*Tareas a ejecutar:*

- Seleccionar y desplegar la base de datos vectorial.
- Definir el modelo de embeddings para la representación semántica.
- Desarrollar el pipeline de ingesta de datos.
- Indexar el catálogo de especialidades médicas y las guías clínicas de triage.
- Crear un endpoint de prueba para validar la búsqueda semántica.

**H-17: Pipeline CI/CD automatizado — 8 puntos**
**Estado reportado:** In review

*Trabajo técnico reportado como concluido, pendiente de revisión:*

- Configuración del workflow en GitHub Actions.
- Automatización de linters y pruebas unitarias en cada pull request.
- Automatización de la construcción de imágenes Docker.
- Configuración del despliegue continuo al clúster mediante rolling update después de integrar cambios en `main`.

### 1.2. Acta de Sprint Review — Revisión

**Fecha de la reunión:** 01/10/2026
**Asistentes:** Andrés Ramos, Santiago Pardo y Juan Nocua

| ID   | Historia                       | Cumplimiento de Definition of Done — DoD | Observaciones / Feedback de la docente                                       |
| ---- | ------------------------------ | ---------------------------------------- | ---------------------------------------------------------------------------- |
| H-16 | Orquestación en Kubernetes     | Por confirmar                            | Pendiente de registrar.                                                      |
| H-17 | Pipeline CI/CD automatizado    | Por confirmar                            | Trabajo técnico reportado en revisión; pendiente de registrar su aceptación. |
| H-18 | Base de conocimiento vectorial | Por confirmar                            | Pendiente de registrar.                                                      |

**Meta del Sprint alcanzada:** Por confirmar en el acta de revisión.

### 1.3. Acta de Retrospectiva

**Fecha de la reunión:** 02/10/2026

**¿Qué hicimos bien?**

- Pendiente de registrar los acuerdos y conclusiones de la reunión.

**¿Qué no salió tan bien o qué impedimentos tuvimos?**

- Pendiente de registrar los impedimentos identificados por el equipo.

**Acciones de mejora para el siguiente Sprint:**

- Pendiente de completar con las acciones acordadas.

---

## 2. Incremento posterior — Portal administrativo y seguridad

**Fechas de trabajo documentadas:** 11/10/2026 y 12/10/2026
**Periodo formal del Sprint:** Por definir por el equipo.
**Estado general:** Desarrollo preparado y validado localmente; pendiente de publicación, revisión e integración.

### 2.1. Objetivo del incremento

Integrar el portal administrativo de EPS Digital y completar los flujos de recuperación de contraseña y verificación en dos pasos, conservando la estructura del proyecto y preparando su funcionamiento en el entorno conectado con Supabase y Render.&#x20;

### 2.2. Historias de usuario y tareas desarrolladas

*Los identificadores y puntos de estas historias deben asignarse en GitHub Projects para mantener la numeración del backlog existente.*

**Historia: Acceso y gestión administrativa**

*Como administrador, quiero acceder a un portal de gestión para consultar y administrar el catálogo de médicos, servicios y especialidades.*

**Estado:** Implementación local finalizada; pendiente de revisión.

*Tareas ejecutadas:*

- Habilitar las rutas del portal administrativo.
- Incorporar el inicio de sesión para cuentas existentes con rol administrador.
- Integrar las pantallas de resumen, médicos, servicios, especialidades y reportes.
- Conectar las operaciones administrativas con los endpoints existentes.
- Corregir consultas y llamadas al cliente API que impedían el funcionamiento de las páginas.
- Incorporar exportación de reportes del catálogo en formato CSV.
- Mantener el diseño visual y los colores del proyecto.
- Mostrar estados de carga, errores y opciones de reintento.

**Alcance pendiente:** La gestión de cuentas administrativas y la creación de credenciales de acceso para médicos no quedaron implementadas.

**Historia: Recuperación de contraseña**

*Como usuario, quiero recuperar el acceso a mi cuenta mediante un enlace enviado al correo registrado para establecer una nueva contraseña.*

**Estado:** Implementación local finalizada; pendiente de configurar y validar el correo real.

*Tareas ejecutadas:*

- Incorporar el acceso a recuperación desde los formularios de inicio de sesión.
- Crear la pantalla de solicitud de recuperación.
- Crear la pantalla para establecer y confirmar la nueva contraseña.
- Implementar enlaces temporales de un solo uso, con vigencia de 30 minutos.
- Invalidar los enlaces anteriores cuando se solicita uno nuevo.
- Validar los requisitos de contraseña y la coincidencia de su confirmación.
- Preparar el envío mediante SendGrid y un modo local de pruebas.

**Historia: Verificación en dos pasos**

*Como usuario, quiero añadir una verificación por correo al inicio de sesión para reforzar la seguridad de mi cuenta.*

**Estado:** Implementación local finalizada; pendiente de validación en el entorno desplegado.

*Tareas ejecutadas:*

- Crear la pantalla de seguridad de la cuenta.
- Implementar la solicitud y confirmación de activación de la verificación en dos pasos.
- Incorporar la pantalla para ingresar el código recibido por correo.
- Condicionar la emisión de los tokens de sesión a la verificación correcta del segundo factor.
- Implementar códigos de seis dígitos, de un solo uso y con vigencia de 10 minutos.
- Diferenciar los códigos de activación de los códigos de inicio de sesión.
- Incorporar límites de solicitudes y bloqueo temporal por intentos incorrectos.
- Mostrar los errores de verificación en la pantalla correspondiente.

### 2.3. Integración y documentación

*Tareas ejecutadas:*

- Comparar el ZIP de trabajo con la rama `Andres`.
- Preparar la integración conservando el archivo de dependencias de esa rama.
- Ajustar la comparación de fechas de bloqueo para manejar fechas con y sin zona horaria.
- Mantener los modelos y las migraciones de base de datos existentes.
- Documentar los cambios administrativos, la recuperación de contraseña, la verificación en dos pasos y su configuración.
- Preparar un commit local para su publicación posterior.

**Documentación generada:**

- `docs/REVISION_ADMINISTRATIVA.md`
- `docs/VALIDACION_ADMIN.md`
- `docs/RECUPERACION_Y_2FA.md`

### 2.4. Revisión técnica del incremento

**Reunión formal de Sprint Review:** Pendiente de programar.
**Resultados técnicos disponibles:**

| Componente                               | Validación realizada                                    | Resultado y alcance                                                    |
| ---------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------- |
| Frontend                                 | Instalación de dependencias y compilación de producción | Correctas; permanece una advertencia de tamaño del paquete JavaScript. |
| Servicio de autenticación                | Validación de sintaxis Python                           | Correcta.                                                              |
| Recuperación y verificación en dos pasos | Ocho pruebas automatizadas                              | Aprobadas con SQLite temporal y correo simulado.                       |
| Supabase                                 | Prueba contra la base de datos real                     | Pendiente.                                                             |
| Correo                                   | Entrega real de enlaces y códigos                       | Pendiente.                                                             |
| Render                                   | Validación del incremento desplegado                    | Pendiente.                                                             |
| GitHub                                   | Publicación en `Andres` y pull request hacia `main`     | Pendiente por permisos de escritura.                                   |

**Cumplimiento de DoD:** Parcial. La implementación cuenta con validación local, pero aún requiere revisión del equipo y comprobación en el entorno desplegado.

### 2.5. Insumos para la retrospectiva

*Estos puntos corresponden al trabajo observado; quedan sujetos a discusión y acuerdo del equipo.*

**¿Qué funcionó bien?**

- Se aprovechó la estructura existente del proyecto.
- Se conservaron las dependencias de la rama `Andres`.
- Se verificaron la compilación y los flujos de autenticación antes de publicar.
- Se documentaron las funciones entregadas y las configuraciones pendientes.

**¿Qué impedimentos se presentaron?**

- La terminal no disponía de credenciales para publicar en GitHub.
- La conexión de GitHub rechazó la escritura con un error 403.
- No se completó la validación con Supabase ni el envío real de correos.
- La configuración del entorno de Render continúa pendiente.

**Acciones de mejora propuestas:**

- Verificar los permisos de escritura antes de la siguiente publicación.
- Coordinar la revisión de Juan mediante un pull request.
- Configurar y probar el servicio de correo.
- Definir criterios de aceptación y evidencias para cerrar cada historia.

---

## 3. Seguimiento y trazabilidad de actualizaciones

**Fecha de seguimiento:** 16/10/2026
**Estado:** Plan de trabajo pendiente de ejecución.

### 3.1. Registro de aportes en GitHub

Se utilizará el historial de commits y la vista Activity para consultar quién publica cambios, en qué fecha y sobre qué rama. GitHub registra esta actividad automáticamente una vez que los cambios se suben al repositorio.

Cada integrante deberá utilizar su propia cuenta y una identidad de Git correctamente configurada para facilitar la atribución de sus aportes.

### 3.2. Flujo de revisión propuesto

1. Publicar los cambios desarrollados en la rama `Andres`.
2. Crear un pull request con destino a `main`.
3. Incluir la descripción del incremento, las pruebas realizadas y las configuraciones pendientes.
4. Solicitar la revisión de Juan.
5. Atender las observaciones.
6. Integrar los cambios en `main` una vez aprobados.
7. Verificar el despliegue y registrar el resultado en GitHub Projects.

### 3.3. Configuración propuesta para la rama principal

El administrador del repositorio revisará la posibilidad de proteger `main`, exigiendo un pull request y al menos una aprobación antes de integrar cambios, según las opciones disponibles para el repositorio.

**Estado de esta configuración:** No aplicada durante este trabajo.

### 3.4. Pendientes para completar la entrega

| Pendiente                                          | Responsable propuesto                       | Evidencia esperada                                                        |
| -------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------- |
| Revisar permisos de escritura de la integración    | Propietario o administrador del repositorio | Acceso de escritura autorizado.                                           |
| Publicar el incremento en `Andres`                 | Andrés Ramos                                | Commit visible en GitHub.                                                 |
| Crear el pull request hacia `main`                 | Andrés Ramos                                | Solicitud con descripción y resultados de pruebas.                        |
| Revisar y aprobar la integración                   | Juan Nocua                                  | Revisión registrada en el pull request.                                   |
| Configurar el correo y la URL del portal en Render | Responsable del despliegue, por confirmar   | Configuración aplicada y prueba de entrega de correo.                     |
| Validar los flujos con Supabase y Render           | Equipo de desarrollo                        | Evidencias de recuperación, inicio de sesión y verificación en dos pasos. |
| Actualizar GitHub Projects y cerrar historias      | Equipo Scrum                                | Estados y criterios de aceptación actualizados.                           |

**Estado al cierre de esta bitácora:** Los cambios del portal administrativo y de seguridad están preparados y validados localmente. Su publicación en GitHub permanece pausada por solicitud del integrante; la revisión, la integración en `main` y la validación en producción siguen pendientes.
