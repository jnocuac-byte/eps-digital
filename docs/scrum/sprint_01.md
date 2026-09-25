---

# Bitácora Scrum — EPS Digital

**Product Owner:** (EPS digital)
**Scrum Master:** Andrés Ramos
**Tablero de trabajo:** GitHub Projects
**Periodo del Sprint:** (18/09/2026-- 25/09/2026 )

---

## 1. Acta de Sprint Planning (Planeación)

**Fecha de la reunión:** (18/09/2026)
**Asistentes:** (Juan Esteban Nocua, Santiago Pardo)

### Sprint Goal (Meta del Sprint)

Desplegar la infraestructura base de la plataforma mediante orquestación y pipeline automatizado, e inicializar la base de conocimiento vectorial para el agente.

### Historias de Usuario Comprometidas y Tareas

A continuación, se desglosa el trabajo técnico para las historias seleccionadas en este Sprint:

**H-16: Orquestación en Kubernetes (13 Pts) - Estado: In progress**
*Tareas a ejecutar:*

* Definir la arquitectura del clúster y elegir la plataforma (ej. Minikube, EKS, GKE).
* Crear los manifiestos de Deployment y Service para los 6 microservicios.
* Configurar el Ingress Controller para unificar la entrada mediante una URL única.
* Implementar sondas de salud (liveness y readiness probes) para garantizar la disponibilidad.
* Configurar Persistent Volumes (PV) y Persistent Volume Claims (PVC) para PostgreSQL y Redis.

**H-18: Base de conocimiento vectorial (8 Pts) - Estado: In progress**
*Tareas a ejecutar:*

* Seleccionar y desplegar la base de datos vectorial (ej. Pinecone, Weaviate, Qdrant, o pgvector).
* Definir el modelo de embeddings a utilizar para la representación semántica.
* Desarrollar el pipeline de ingesta de datos.
* Indexar el catálogo de especialidades médicas y las guías clínicas de triage.
* Crear un endpoint de prueba para validar la búsqueda semántica.

**H-17: Pipeline CI/CD automatizado (8 Pts) - Estado: In review**
*(Nota: El trabajo técnico ha concluido, se documentan las tareas realizadas para evidencia del incremento)*
*Tareas ejecutadas:*

* Configuración del workflow en GitHub Actions.
* Automatización de ejecución de linters y pruebas unitarias en cada Pull Request.
* Automatización del proceso de build (construcción de imágenes Docker).
* Configuración del despliegue continuo al clúster (rolling update) tras un merge a la rama `main`.

---

## 2. Acta de Sprint Review (Revisión)

**Fecha de la reunión:** 25/09/2026
**Asistentes:** Andres Ramos, Santiago Pardo, Juan Nocua

| ID | Historia | ¿Cumplió Definition of Done (DoD)? | Observaciones / Feedback de la Docente |
| --- | --- | --- | --- |
| **H-16** | Orquestación en Kubernetes | (Sí / Parcial / No) | (Espacio para observaciones) |
| **H-17** | Pipeline CI/CD automatizado | (Sí / Parcial / No) | (Espacio para observaciones) |
| **H-18** | Base de conocimiento vectorial | (Sí / Parcial / No) | (Espacio para observaciones) |

**Meta del Sprint alcanzada:** (Sí / Parcialmente / No)

---

## 3. Acta de Retrospectiva

**Fecha de la reunión:** 02/10/2026

* **¿Qué hicimos bien?**
* .


* **¿Qué no salió tan bien o qué impedimentos tuvimos?**
* .


* **Acciones de mejora para el próximo Sprint:**
* .



---

Este documento te sirve como plantilla. Cada vez que inicies un nuevo Sprint, generas uno igual ajustando las historias correspondientes y lo agregas al informe final como tu evidencia de Scrum.
