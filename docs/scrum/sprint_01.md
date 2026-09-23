Para formalizar la metodología Scrum y tener la evidencia clara para la presentación final, necesitas un documento que registre las ceremonias (Planning, Review, Retrospectiva). El tablero que se muestra en el archivo `image_25ac37.png` es la herramienta operativa diaria. Allí se observa que en el "Tablero Scrum - EPS Digital" las historias H-16 (Orquestación en Kubernetes) y H-18 (Base de conocimiento vectorial) están en "In progress", mientras que la H-17 (Pipeline CI/CD automatizado) ya avanzó a "In review". Además, hay 13 historias en la columna "Done" y 1 en "Testing" (H-26).

Como ahora el Scrum Master eres tú, Andrés, tu labor es mantener este registro actualizado al inicio y al final de cada Sprint. A continuación, tienes la estructura exacta en Markdown para documentar la planeación y dejar la evidencia formal.

Copia el siguiente contenido y guárdalo en tu repositorio (por ejemplo, en `docs/scrum/bitacora_sprint_1.md`):

---

# Bitácora Scrum — EPS Digital

**Product Owner:** (EPS digital)
**Scrum Master:** Andrés Ramos
**Tablero de trabajo:** GitHub Projects
**Periodo del Sprint:** (18/09/2026-- 25/09/2026 )

---

## 1. Acta de Sprint Planning (Planeación)

**Fecha de la reunión:** (18/09/2026)
**Asistentes:** Andrés Ramos (Scrum Master), (Juan Esteban Nocua, Santiago Pardo)

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

**Fecha de la reunión:** (Fecha de cierre del Sprint, idealmente con la docente)
**Asistentes:** (Nombres)

| ID | Historia | ¿Cumplió Definition of Done (DoD)? | Observaciones / Feedback de la Docente |
| --- | --- | --- | --- |
| **H-16** | Orquestación en Kubernetes | (Sí / Parcial / No) | (Espacio para observaciones) |
| **H-17** | Pipeline CI/CD automatizado | (Sí / Parcial / No) | (Espacio para observaciones) |
| **H-18** | Base de conocimiento vectorial | (Sí / Parcial / No) | (Espacio para observaciones) |

**Meta del Sprint alcanzada:** (Sí / Parcialmente / No)

---

## 3. Acta de Retrospectiva

**Fecha de la reunión:** (Fecha de cierre del Sprint, solo el equipo de desarrollo)

* **¿Qué hicimos bien?**
* (Ej: Logramos sacar adelante la historia H-17 rápidamente).


* **¿Qué no salió tan bien o qué impedimentos tuvimos?**
* (Ej: Problemas configurando los volúmenes persistentes en H-16, falta de tiempo).


* **Acciones de mejora para el próximo Sprint:**
* (Ej: Dividir las historias de 13 puntos en tareas más pequeñas durante el Planning; hacer dailies más cortas).



---

Este documento te sirve como plantilla. Cada vez que inicies un nuevo Sprint, generas uno igual ajustando las historias correspondientes y lo agregas al informe final como tu evidencia de Scrum.
