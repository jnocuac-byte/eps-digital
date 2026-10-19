# Bitácora Scrum — EPS Digital

**Product Owner:** Juan Esteban Nocua, según la guía del equipo; confirmar la asignación formal.  
**Scrum Master:** Andrés Ramos  
**Equipo de desarrollo:** Santiago Pardo, con participación de Juan Esteban Nocua y Andrés Ramos en las actividades reportadas.  
**Tablero:** GitHub Projects  
**Repositorio:** https://github.com/jnocuac-byte/eps-digital  
**Rama de trabajo de Andrés:** `Andres`  
**Entorno local:** Visual Studio Code  
**Fecha de actualización:** 16/10/2026

## 1. Alcance y fuentes de la bitácora

Este documento unifica el registro original `docs/scrum/sprint_01.md`, consultado en la rama `develop`, y el seguimiento del Sprint 2. Se apoya en la Guía del Scrum Master y Plan de Sprints, el documento ProyectoFinalEPS, los avances técnicos preparados y el reporte de Juan del 16/10/2026.

La guía establece cinco Sprints entre el 21 de septiembre y el 27 de noviembre de 2026. El trabajo anterior corresponde al incremento pre-Scrum y no se contabiliza como velocidad de los Sprints. La guía registra 93 puntos previos y una planificación pendiente de 123 puntos. H-11 aparece tanto dentro del rango histórico H-01 a H-14 como en el Sprint 2: se debe conciliar este dato con el backlog para evitar contar dos veces su trabajo. Su alcance administrativo pendiente se conserva en el Sprint 2 según el plan.

El registro original indicaba 18/09–25/09. Se conserva el 18/09 como fecha de planeación registrada y se adopta el calendario de la guía: Sprint 1 del 21/09 al 02/10 y Sprint 2 del 05/10 al 16/10. Esta conciliación no implica que se hayan celebrado reuniones adicionales.

Las fechas programadas, propuestas y resultados pendientes se distinguen de los hechos reportados. No se atribuyen aprobaciones ni observaciones a la docente sin confirmación.

## 2. Definition of Done y reglas de seguimiento

La guía exige, como mínimo, **código integrado en `develop`, probado y documentado**. Cada historia debe cumplir además su alcance y criterios de aceptación. Un avance local, una compilación correcta o un estado “In review” no bastan para declarar una historia terminada.

- En la Review se demuestra el funcionamiento y se registra la verificación con la docente.
- Solo las historias que cumplen la DoD completa aportan puntos a la velocidad. No se cuentan porcentajes ni puntos parciales de historias inconclusas.
- Los pendientes se devuelven o repriorizan en el Product Backlog y se seleccionan nuevamente en el siguiente Planning; el Sprint no se extiende.
- Las acciones de retrospectiva deben tener un responsable identificado.
- El flujo conversado `Andres` → revisión de Juan → `main` debe conciliarse con la DoD de la guía. Hasta que el equipo acuerde un cambio, se propone integrar mediante PR a `develop`, verificar la DoD y gestionar después la promoción a `main` con Juan.

## 3. Sprint 1 — Infraestructura e integración

**Periodo según la guía:** 21/09/2026 al 02/10/2026  
**Planeación registrada:** 18/09/2026  
**Asistentes registrados:** Juan Esteban Nocua y Santiago Pardo

### 3.1. Acta de Sprint Planning

**Meta original:** Desplegar la infraestructura base mediante orquestación y pipeline automatizado e inicializar la base de conocimiento vectorial.

**Meta ampliada en la guía:** Cerrar el trabajo iniciado de MVP integrado, CI/CD, base de conocimiento y accesibilidad.

| Historia | Puntos documentados | Estado en el acta original | Alcance registrado |
| --- | ---: | --- | --- |
| H-16 — Orquestación en Kubernetes | 13 | In progress | Arquitectura del clúster; Deployment y Service de seis microservicios; Ingress; sondas liveness/readiness; PV y PVC de PostgreSQL y Redis. |
| H-17 — Pipeline CI/CD automatizado | 8 | In review | Workflow de GitHub Actions; linters y pruebas en PR; construcción de imágenes Docker; despliegue mediante rolling update tras integración en main, según el reporte original. |
| H-18 — Base de conocimiento vectorial | 8 | In progress | Selección de base vectorial y embeddings; ingesta; indexación de catálogo y guías de triage; endpoint de búsqueda semántica. |
| H-15, H-26 y H-27 | 21 en conjunto, por diferencia | No documentado en el acta original | Incluidas por la guía; recuperar del tablero su desglose y evidencia de compromiso. |
| **Total del plan de la guía** | **50** | **Cierre por verificar** | El acta original detalla solamente 29 puntos. |

Los 21 puntos restantes se obtienen de 50 − 29; no constituyen una estimación individual nueva de H-15, H-26 o H-27.

### 3.2. Acta de Sprint Review

**Fecha registrada:** 01/10/2026  
**Asistentes registrados:** Andrés Ramos, Santiago Pardo y Juan Nocua.  
**Presencia y feedback de la docente:** No registrados en la fuente; pendientes de confirmar.

| Historia | ¿Cumplió DoD? | Resultado disponible y motivo |
| --- | --- | --- |
| H-16 | Por verificar | El acta la registra en desarrollo; no contiene evidencia de aceptación. |
| H-17 | Por verificar | Trabajo técnico reportado como concluido y en revisión; falta confirmar pruebas, documentación e integración exigidas por la DoD. |
| H-18 | Por verificar | El acta la registra en desarrollo; no contiene evidencia de aceptación. |
| H-15, H-26 y H-27 | Por verificar | La guía las incluye, pero el acta no registra su resultado. |

**Meta alcanzada:** Por confirmar con evidencias del cierre.  
**Puntos completados:** No determinados. No se reemplaza este dato por cero ni se presumen los 50 puntos terminados.

### 3.3. Acta de Retrospectiva

**Fecha registrada:** 02/10/2026.

El acta original dejó sin diligenciar qué funcionó bien, qué impedimentos hubo y cuáles fueron los acuerdos. No se reconstruyen esas respuestas como hechos sin confirmación del equipo.

**Acción de regularización propuesta el 16/10/2026:** Andrés Ramos recopilará los resultados y evidencias de cierre del Sprint 1 con Juan y Santiago, completará la Review y actualizará su velocidad antes de aprobar el siguiente Planning. Esta acción es posterior y no se presenta como un acuerdo tomado el 02/10.

## 4. Sprint 2 — Panel administrativo y protección del sistema

**Periodo:** 05/10/2026 al 16/10/2026  
**Fecha prevista de Planning:** 05/10/2026; celebración y asistentes por confirmar.  
**Fecha prevista de Review y Retro:** 16/10/2026; celebración, asistencia docente y aceptación por confirmar.  
**Estado del registro:** Seguimiento técnico preparado para revisión, no acta de aprobación docente.

### 4.1. Acta de Sprint Planning — Registro por validar

**Sprint Goal:** Completar el panel administrativo y proteger el sistema mediante cifrado de datos sensibles en reposo y en tránsito.

**Compromiso del plan:** H-11 y H-22, por un total de 21 puntos.

| Historia | Alcance verificado | Puntos propuestos | Participación reportada |
| --- | --- | ---: | --- |
| [H-11 — Panel administrativo](https://github.com/jnocuac-byte/eps-digital/issues/29) | Gestión de médicos, servicios y administradores, más tablero de reportes. | 8 | Andrés: preparación de interfaz e integración local. Juan: revisión prevista. |
| [H-22 — Cifrado en reposo y en tránsito](https://github.com/jnocuac-byte/eps-digital/issues/38) | Cifrado por columna en campos sensibles de HCE, llaves en Secrets, TLS en Ingress y cabeceras de seguridad. | 13 | Juan: trabajo de cifrado y diseño de rotación de claves. |
| **Total** | | **21** | |

**Nota de estimación:** La guía solo confirma el total de 21 puntos. La distribución 8/13 es una propuesta para validar con el equipo y el campo de estimación de GitHub Projects; no se afirma que haya sido acordada en el Planning. Se propone mayor esfuerzo para H-22 por el cifrado, los dos entornos, las búsquedas y la rotación segura. No se reducen estimaciones retrospectivamente para mejorar el porcentaje de cumplimiento.

**Asignaciones:** La issue H-11 figura asignada a jnocuac-byte y H-22 no tiene asignatario en la consulta realizada. Las participaciones de esta tabla proceden del trabajo reportado; el equipo debe conciliar las asignaciones en el tablero.

### 4.2. Trabajo desarrollado y pendiente

**H-11 — Panel administrativo**

Trabajo preparado durante el 11 y 12 de octubre:

- Rutas y acceso administrativo para cuentas existentes con rol administrador.
- Pantallas de resumen, médicos, servicios, especialidades y reportes del catálogo.
- Conexión con endpoints existentes y corrección de consultas al cliente API.
- Exportación CSV y estados de carga, error y reintento.
- Conservación del diseño del proyecto y de las dependencias de la rama Andres.

Pendientes: incorporación y comprobación en el proyecto de Andrés en Visual Studio Code; publicación y revisión; gestión de cuentas administrativas, incluida en el alcance de H-11 y todavía no implementada. La creación de credenciales médicas tampoco quedó implementada; confirmar su ubicación en el backlog.

**H-22 — Cifrado en reposo y en tránsito**

Según el reporte de Juan del 16/10, continúa el trabajo de cifrado a nivel de columna para historias clínicas. Se presentaron dificultades con búsquedas sobre textos cifrados y con la rotación de claves al trabajar en dos entornos. Juan está diseñando una rotación segura y prevé continuar el fin de semana.

Pendientes: completar y probar el cifrado y la rotación; aportar evidencia de gestión de llaves mediante Secrets, TLS en Ingress y cabeceras de seguridad; integrar, documentar y revisar. La intención de continuar el fin de semana no extiende el Sprint 2.

**Trabajo adicional preparado — Recuperación de contraseña y verificación en dos pasos**

- Pantallas de recuperación, restablecimiento, activación y verificación de códigos.
- Enlaces de recuperación de un solo uso, vigencia de 30 minutos y validación de contraseña.
- Códigos de seis dígitos, de un solo uso y vigencia de 10 minutos.
- Desafíos separados para activación e inicio de sesión, límites de envío y bloqueo por intentos.
- Preparación de envío mediante SendGrid y modo local de prueba.

Estas funciones son de autenticación y no demuestran por sí mismas el cumplimiento de H-22. No se les asignan identificadores ni puntos adicionales al compromiso de 21 puntos sin acuerdo del equipo.

**Documentación preparada:** `docs/REVISION_ADMINISTRATIVA.md`, `docs/VALIDACION_ADMIN.md` y `docs/RECUPERACION_Y_2FA.md`.

### 4.3. Seguimiento de avances e impedimentos

| Fecha o periodo | Avance reportado | Siguiente paso | Impedimento |
| --- | --- | --- | --- |
| 11–12/10 | Preparación del panel y flujos de autenticación; compilación y pruebas en entorno de preparación. | Incorporar y verificar en Visual Studio Code. | Publicación bloqueada por autenticación/permisos de la conexión utilizada. |
| 16/10 — Juan | Trabajo en cifrado por columna y diseño de rotación. | Probar búsquedas y rotación en ambos entornos. | Búsquedas sobre texto cifrado y coordinación de claves entre entornos. |
| 16/10 — Andrés | Organización de bitácora y del flujo de integración. | Probar localmente, crear commit y someter cambios a revisión. | Incorporación local y acceso de publicación pendientes. |

Estos registros son una síntesis de evidencias disponibles, no actas de Daily celebradas. La guía propone Dailies lunes, miércoles y viernes; sus fechas, participantes y acuerdos deben registrarse desde las reuniones reales.

### 4.4. Sprint Review — Balance técnico al 16/10

**Asistentes y presencia docente:** Pendientes de confirmar.  
**Observaciones de la docente:** Pendientes de registrar durante la revisión real.

| Historia | Resultado | ¿Cumple DoD completa? | Motivo | Puntos aceptados |
| --- | --- | --- | --- | ---: |
| H-11 | Avance parcial | No acreditada | Falta gestión de administradores, incorporación local, integración y validación del alcance completo. | 0 |
| H-22 | En desarrollo | No acreditada | Juan reporta pendientes de búsquedas y rotación; faltan evidencias completas de cifrado, Secrets, TLS y cabeceras. | 0 |

**Qué se logró verificar:** compilación del frontend, sintaxis Python y ocho pruebas de recuperación/2FA con SQLite temporal y correo simulado en el entorno de preparación. Son evidencias del trabajo de Andrés, no pruebas de cifrado de HCE ni de despliegue real.

**Qué no se completó:** cierre integral de H-11 y H-22, incorporación local de Andrés, publicación de esos cambios y validaciones con Supabase, Render y correo real.

**Meta del Sprint:** No alcanzada completamente con la evidencia disponible; existen avances parciales.  
**Puntos aceptados acreditados a la fecha:** 0 de 21, provisional hasta la Review real. No equivale a ausencia de trabajo.  
**Decisión propuesta:** mantener ambas historias abiertas y repriorizar el alcance pendiente en el siguiente Planning. Actualizar esta sección si la revisión aporta evidencia adicional de cumplimiento al cierre.

### 4.5. Retrospectiva — Propuesta para validar en reunión

**¿Qué funcionó bien?**

- Se reutilizó la arquitectura del proyecto y se conservaron dependencias.
- Se comprobaron compilación y flujos de autenticación antes de publicar.
- Juan comunicó los bloqueos de cifrado y rotación para incorporarlos al seguimiento.
- Se identificó la necesidad de separar avances técnicos de historias realmente terminadas.

**¿Qué dificultades se presentaron?**

- **Juan Nocua:** dificultades con cifrado por columna en las historias clínicas, búsquedas sobre textos cifrados y rotación de claves en dos entornos; continúa trabajando en un diseño seguro.
- **Andrés Ramos:** dificultades para publicar mediante la conexión utilizada, que devolvió error 403, y necesidad de revisar la organización de carpetas y archivos para incorporar el código en Visual Studio Code. La publicación y revisión del incremento continúan pendientes.
- **Equipo:** faltan resultados de aceptación y velocidad del Sprint 1; debe conciliarse la ruta de integración a develop/main y la estimación por historia.

**Acciones de mejora propuestas con responsables:**

| Acción | Responsable | Plazo propuesto | Evidencia de cumplimiento |
| --- | --- | --- | --- |
| Documentar una prueba de búsquedas y rotación segura en ambos entornos, con resultados y fallos pendientes. | Juan Nocua | Presentar avance en Planning del 19/10. | Resultados de pruebas vinculados a H-22. |
| Incorporar y probar el código local, verificar credenciales de publicación y abrir PR para revisión. | Andrés Ramos | Informar estado y bloqueos el 19/10; acordar fecha de cierre. | Compilación, pruebas y enlace al PR cuando se publique. |
| Completar el cierre histórico del Sprint 1 y verificar estimaciones y responsables en GitHub Projects. | Andrés Ramos | Antes de aprobar el nuevo compromiso del Sprint 3. | Review, tabla de velocidad y tablero consistentes. |
| Confirmar la ruta de integración exigida por la DoD y revisar el alcance administrativo pendiente. | Juan Nocua y Andrés Ramos | Planning del 19/10. | Acuerdo registrado en esta bitácora. |

Estas acciones tienen responsables propuestos; su aceptación debe confirmarse en la retrospectiva. No se presentan como acuerdos ya celebrados.

## 5. Tabla de velocidad y cumplimiento

| Sprint | Periodo | Puntos del plan | Puntos completados con DoD | Cumplimiento | Velocidad acumulada |
| --- | --- | ---: | --- | --- | --- |
| 1 | 21/09–02/10 | 50 | ND: cierre sin completar | ND | ND |
| 2 | 05/10–16/10 | 21 | 0 acreditados provisionalmente | 0 % provisional | ND: falta cierre de S1 y confirmación de S2 |
| 3 | 19/10–30/10 | 18 previstos | No iniciado | No aplica | No aplica |
| 4 | 02/11–13/11 | 21 previstos | No iniciado | No aplica | No aplica |
| 5 | 16/11–27/11 | 13 previstos | No iniciado | No aplica | No aplica |

**ND:** no determinado; no debe interpretarse como cero. Los Sprints futuros muestran planificación, no compromisos ya aprobados.

- Cumplimiento = puntos completados con DoD / puntos comprometidos × 100.
- Velocidad acumulada = promedio de puntos completados por Sprint cerrado y validado. Si falta el resultado de un Sprint, no se presenta un promedio global como definitivo.
- Base pendiente de la guía: 123 puntos, sujeta a conciliación de H-11 y del cierre del Sprint 1. No es posible informar un remanente definitivo con los datos actuales.
- Burndown: registrar puntos pendientes con fechas reales. No inventar una serie diaria ni convertir avances parciales en puntos terminados.

## 6. Plan de Sprints siguientes y replanificación

| Sprint | Fechas | Meta y alcance de la guía | Puntos previstos | Revisión necesaria |
| --- | --- | --- | ---: | --- |
| 3 | 19/10–30/10 | RAG con memoria y detección de urgencia: H-19 y H-20. | 18 | Evaluar prioridad, capacidad y dependencias antes de incorporar pendientes de H-11/H-22. |
| 4 | 02/11–13/11 | Interoperabilidad y auditoría: H-21 y H-23. | 21 | Revisar impactos de las decisiones del Sprint 3. |
| 5 | 16/11–27/11 | Cumplimiento legal, pruebas finales y cierre: H-24 y H-25. | 13 | Mantener espacio para sustentación y pruebas finales. |

**Propuesta para el Planning del 19/10:** revisar primero los pendientes de H-11 y H-22 y decidir qué puede comprometerse junto con, o en sustitución de, parte del alcance previsto. No sumar automáticamente 21 puntos a los 18 del Sprint 3. Mantener las fechas y registrar cualquier cambio de historias, estimaciones o meta tanto aquí como en la guía y el tablero. No se crea un Sprint 6.

## 7. Publicación, revisión y cierre documental

Andrés incorporará los cambios al proyecto en Visual Studio Code, comprobará las funciones, creará el commit y lo subirá a Andres. Juan revisará el PR. Se propone integrar a develop para cumplir la DoD vigente y promover a main según el acuerdo del equipo. No se informa ninguna integración todavía no realizada.

Este archivo está destinado a **`docs/scrum/Bitacora_Scrum.md`** y consolida el contenido de sprint_01.md. Al publicarlo, reemplazar o renombrar el archivo anterior bajo control de versiones para mantener una sola bitácora vigente y conservar su historial.

**Lista de cierre de Review y Retro:**

- [ ] Confirmar fecha, asistentes y presencia de la docente.
- [ ] Demostrar H-11 y H-22 y verificar su DoD completa.
- [ ] Registrar aceptación o rechazo, razones y feedback real de la docente.
- [ ] Confirmar al menos una acción de mejora con responsable y fecha.
- [ ] Validar los puntos por historia y actualizar la velocidad con resultados reales.
- [ ] Completar los datos faltantes del Sprint 1.
- [ ] Repriorizar pendientes y actualizar tablero y guía si cambia el plan.

**Estado del documento:** bitácora consolidada para revisión del equipo y la docente. Contiene avances comprobados, impedimentos reportados y propuestas identificadas; permanecen pendientes las confirmaciones de ceremonias, estimaciones individuales y aceptación final. No se ha publicado este documento ni el código preparado en GitHub desde esta sesión.
