# Bitácora Scrum — EPS Digital

**Product Owner:** EPS Digital
**Scrum Master:** Andrés Ramos
**Tablero de trabajo:** GitHub Projects
**Repositorio:** `jnocuac-byte/eps-digital`
**Rama de desarrollo de Andrés:** `Andres`
**Rama principal:** `main`
**Entorno de desarrollo local:** Visual Studio Code

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
**Estado general:** Código preparado y validado en el entorno de preparación; pendiente de incorporación y comprobación en el proyecto local de Andrés, publicación y revisión.

### 2.1. Objetivo del incremento

Integrar el portal administrativo de EPS Digital y completar los flujos de recuperación de contraseña y verificación en dos pasos, conservando la estructura del proyecto y preparando su funcionamiento con Supabase y Render.

Después de comprobar el funcionamiento local, Andrés creará un commit, lo subirá a la rama `Andres` y solicitará la revisión de Juan antes de su integración en `main`.

### 2.2. Historias de usuario y tareas desarrolladas

*Los identificadores y puntos de estas historias deben asignarse en GitHub Projects para mantener la numeración del backlog existente.*

**Historia: Acceso y gestión administrativa**

*Como administrador, quiero acceder a un portal de gestión para consultar y administrar el catálogo de médicos, servicios y especialidades.*

**Estado:** Código preparado; pendiente de incorporación al proyecto local de Andrés y revisión.

*Tareas desarrolladas:*

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

**Estado:** Código preparado; pendiente de incorporación local y configuración del correo real.

*Tareas desarrolladas:*

- Incorporar el acceso a recuperación desde los formularios de inicio de sesión.
- Crear la pantalla de solicitud de recuperación.
- Crear la pantalla para establecer y confirmar la nueva contraseña.
- Implementar enlaces temporales de un solo uso, con vigencia de 30 minutos.
- Invalidar los enlaces anteriores cuando se solicita uno nuevo.
- Validar los requisitos de contraseña y la coincidencia de su confirmación.
- Preparar el envío mediante SendGrid y un modo local de pruebas.

**Historia: Verificación en dos pasos**

*Como usuario, quiero añadir una verificación por correo al inicio de sesión para reforzar la seguridad de mi cuenta.*

**Estado:** Código preparado; pendiente de incorporación local y validación en el entorno desplegado.

*Tareas desarrolladas:*

- Crear la pantalla de seguridad de la cuenta.
- Implementar la solicitud y confirmación de activación de la verificación en dos pasos.
- Incorporar la pantalla para ingresar el código recibido por correo.
- Condicionar la emisión de los tokens de sesión a la verificación correcta del segundo factor.
- Implementar códigos de seis dígitos, de un solo uso y con vigencia de 10 minutos.
- Diferenciar los códigos de activación de los códigos de inicio de sesión.
- Incorporar límites de solicitudes y bloqueo temporal por intentos incorrectos.
- Mostrar los errores de verificación en la pantalla correspondiente.

### 2.3. Integración en Visual Studio Code y documentación

*Trabajo de preparación realizado:*

- Revisar la estructura del proyecto y comparar los cambios con la rama `Andres` disponible al momento de la preparación.
- Preparar la integración conservando el archivo de dependencias de esa rama.
- Ajustar la comparación de fechas de bloqueo para manejar fechas con y sin zona horaria.
- Mantener los modelos y las migraciones de base de datos existentes.
- Documentar los cambios administrativos, la recuperación de contraseña, la verificación en dos pasos y su configuración.

*Tareas pendientes de incorporación local:*

- Revisar las importaciones, las rutas, las llamadas al API y las variables de entorno.
- Ejecutar el proyecto, comprobar las funciones incorporadas y corregir los errores identificados.
- Revisar las diferencias desde el control de versiones de Visual Studio Code.
- Crear el commit y subirlo a `Andres` cuando las comprobaciones locales sean satisfactorias.

**Documentación de apoyo preparada:**

- `docs/REVISION_ADMINISTRATIVA.md`
- `docs/VALIDACION_ADMIN.md`
- `docs/RECUPERACION_Y_2FA.md`

### 2.4. Revisión técnica del incremento

**Reunión formal de Sprint Review:** Pendiente de programar.
**Resultados técnicos disponibles y validaciones pendientes:**

| Componente                               | Validación realizada o prevista                                         | Resultado y alcance                                                    |
| ---------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Frontend                                 | Instalación de dependencias y compilación en el entorno de preparación  | Correctas; permanece una advertencia de tamaño del paquete JavaScript. |
| Servicio de autenticación                | Validación de sintaxis Python                                           | Correcta en el entorno de preparación.                                 |
| Recuperación y verificación en dos pasos | Ocho pruebas automatizadas                                              | Aprobadas con SQLite temporal y correo simulado.                       |
| Proyecto local de Andrés                 | Incorporación en Visual Studio Code, compilación y pruebas posteriores  | Pendiente.                                                             |
| Supabase                                 | Prueba contra la base de datos real                                     | Pendiente.                                                             |
| Correo                                   | Entrega real de enlaces y códigos                                       | Pendiente.                                                             |
| Render                                   | Validación del incremento desplegado                                    | Pendiente.                                                             |
| GitHub                                   | Creación y publicación del commit de Andrés y pull request hacia `main` | Pendiente de incorporación local y acceso de escritura.                |

**Cumplimiento de DoD:** Parcial. El código cuenta con validación en el entorno de preparación, pero debe comprobarse nuevamente después de incorporarlo al proyecto de Andrés. También requiere revisión del equipo y validación en el entorno desplegado.

### 2.5. Insumos para la retrospectiva

*Estos puntos corresponden al trabajo observado; quedan sujetos a discusión y acuerdo del equipo.*

**¿Qué funcionó bien?**

- Se aprovechó la estructura existente del proyecto.
- Se conservaron las dependencias de la rama `Andres`.
- Se verificaron la compilación y los flujos de autenticación en el entorno de preparación.
- Se documentaron las funciones desarrolladas y las configuraciones pendientes.

**¿Qué impedimentos se presentaron?**

- La terminal del entorno de preparación no disponía de credenciales para publicar en GitHub.
- La conexión de GitHub rechazó la escritura con un error 403.
- La incorporación de los cambios al proyecto local de Andrés continúa pendiente.
- No se completó la validación con Supabase ni el envío real de correos.
- La configuración del entorno de Render continúa pendiente.

**Acciones de mejora propuestas:**

- Verificar la conexión y los permisos antes de la siguiente publicación.
- Incorporar los cambios por componentes en Visual Studio Code y revisar las diferencias.
- Ejecutar las pruebas después de incorporar el código.
- Crear commits con descripciones claras.
- Coordinar la revisión de Juan mediante un pull request.
- Configurar y probar el servicio de correo.
- Definir criterios de aceptación y evidencias para cerrar cada historia.

---

## 3. Seguimiento y trazabilidad de actualizaciones

**Fecha de seguimiento:** 16/10/2026
**Estado:** Incorporación local y publicación pendientes.

### 3.1. Registro de aportes en GitHub

Andrés registrará las modificaciones mediante commits creados desde el proyecto local en Visual Studio Code. Después de subirlos al repositorio, el historial de commits y la vista Activity permitirán consultar la autoría, las fechas y las modificaciones publicadas.

Cada integrante deberá utilizar su propia cuenta y una identidad de Git correctamente configurada para facilitar la atribución de sus aportes.

### 3.2. Flujo de implementación y revisión propuesto

1. Ajustar los archivos existentes, conservando el trabajo previo del equipo.
2. Ejecutar el proyecto y las pruebas locales, y corregir los errores encontrados.
3. Revisar las modificaciones desde el control de versiones.
4. Crear un commit en la rama `Andres` con una descripción de las funciones incorporadas.
5. Subir el commit a GitHub mediante push.
6. Crear un pull request desde `Andres` hacia `main`, incluyendo el alcance, las pruebas y las configuraciones pendientes.
7. Solicitar la revisión de Juan y atender sus observaciones.
8. Dejar la integración en `main` a cargo de Juan después de su revisión y aprobación.
9. Verificar el despliegue y registrar el resultado en GitHub Projects.

### 3.3. Configuración propuesta para la rama principal

El administrador del repositorio revisará la posibilidad de proteger `main`, exigiendo un pull request y al menos una aprobación antes de integrar cambios, según las opciones disponibles para el repositorio.

### 3.4. Pendientes para completar la entrega

| Pendiente                                                      | Responsable propuesto                                   | Evidencia esperada                                                          |
| -------------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------- |
| Revisar la conexión y los permisos de escritura                | Andrés Ramos, con apoyo del propietario o administrador | Conexión autenticada y acceso de escritura autorizado.                      |
| Incorporar el código en Visual Studio Code                     | Andrés Ramos                                            | Carpetas, archivos y modificaciones integrados en el proyecto local.        |
| Comprobar el proyecto después de la incorporación              | Andrés Ramos, con apoyo del equipo                      | Compilación y pruebas locales con resultados registrados.                   |
| Crear el commit y subirlo a `Andres`                           | Andrés Ramos                                            | Commit visible en GitHub con descripción de los cambios.                    |
| Crear el pull request hacia `main`                             | Andrés Ramos                                            | Solicitud con alcance, resultados de pruebas y pendientes de configuración. |
| Revisar los cambios e integrarlos en `main` cuando corresponda | Juan Nocua                                              | Revisión e integración registradas en el pull request.                      |
| Configurar el correo y la URL del portal en Render             | Responsable del despliegue, por confirmar               | Configuración aplicada y prueba de entrega de correo.                       |
| Validar los flujos con Supabase y Render                       | Equipo de desarrollo                                    | Evidencias de recuperación, inicio de sesión y verificación en dos pasos.   |
| Actualizar GitHub Projects y cerrar historias                  | Equipo Scrum                                            | Estados y criterios de aceptación actualizados.                             |

**Estado al cierre de esta bitácora:** El código del portal administrativo y de seguridad está preparado y validado en el entorno utilizado para su elaboración. El siguiente paso consiste en incorporarlo al proyecto de Andrés en Visual Studio Code.
