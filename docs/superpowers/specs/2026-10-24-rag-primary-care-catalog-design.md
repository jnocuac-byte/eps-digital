# Diseño: catálogo RAG de atención primaria

## Objetivo

Ampliar la base vectorial de `services/ai-nlp-service` con motivos de consulta,
síndromes y diagnósticos frecuentes de atención primaria, mapeados a diez
especialidades y niveles de urgencia, sin cambiar la dimensión de embeddings
existente (`768`) ni romper el flujo RAG de `/chat`.

El contenido será orientación para triaje y derivación. No incluirá recetas,
tratamientos personalizados ni afirmaciones de diagnóstico para un paciente.

## Política de fuentes

El catálogo será curado en código y tendrá trazabilidad por registro. Se
incluirán `fuente`, `referencia` y `version`; `codigo_cie11` será opcional y
solo se almacenará cuando haya sido verificado. No se copiará masivamente
contenido protegido de la CIE-11. Las guías abiertas y verificables de
Minsalud podrán utilizarse como fuente de referencia.

## Dataset

Se creará un módulo dedicado, como
`services/ai-nlp-service/app/knowledge/data/primary_care_catalog.py`,
separado de `triage_guide.json`. Cada registro tendrá:

- `id` estable.
- `especialidad`.
- `motivo_consulta` y `terminos`.
- `diagnostico_o_sindrome`.
- `nivel_urgencia`: `urgente`, `prioritario` o `programable`.
- `criterios_derivacion` y `banderas_rojas`.
- `codigo_cie11` opcional.
- `fuente`, `referencia` y `version`.

El catálogo cubrirá Cardiología, Neurología, Pediatría, Dermatología,
Odontología, Ginecología, Medicina General, Oftalmología,
Ortopedia/Traumatología y Gastroenterología. La guía general existente seguirá
siendo una fuente independiente de fragmentos.

## Ingesta

`scripts/ingest_knowledge.py` combinará los fragmentos de
`triage_guide.json` con el catálogo. El texto indexado incluirá los términos
del paciente, la especialidad, el nivel de urgencia, criterios de derivación,
banderas rojas y metadatos de fuente. Cada embedding se generará con
`RETRIEVAL_DOCUMENT` y se validará contra `EMBEDDING_DIM = 768`.

El modo recomendado será un upsert idempotente. Se añadirá una identidad de
fuente estable, `source_key`, con índice único mediante migración Alembic.
Esto permitirá actualizar el embedding y el contenido cuando cambie un
registro sin duplicarlo. El cambio conservará la tabla existente y no
modificará la dimensión vectorial.

La CLI conservará `--dry-run` y `--append`, y añadirá opciones explícitas para
reconstrucción completa (`--replace`), tamaño de lote, pausa entre llamadas y
versión del dataset. El reemplazo completo no será el comportamiento por
defecto. La pausa será configurable para respetar los límites de Gemini; los
reintentos transitorios seguirán delegados al helper existente.

La ingesta informará procesados, insertados, actualizados, omitidos, errores y
duración. Un error permanente hará rollback de la transacción activa y no se
reportará una ingesta parcial como exitosa.

## Validación y operación

1. Ejecutar `--dry-run` y validar campos, fuentes, especialidades y niveles.
2. Ejecutar validaciones sintácticas y verificar que todos los vectores tienen
   768 dimensiones.
3. Ingestar primero en staging o una base controlada.
4. Registrar conteos iniciales y finales por fuente, especialidad y versión.
5. Repetir la misma ingesta y confirmar que no aumenta el número de filas.
6. Modificar un registro y confirmar que se actualiza, no se duplica.
7. Comparar 30 consultas representativas antes y después en
   `/api/knowledge/search`, incluyendo consultas clínicas, urgentes, no
   clínicas y ambiguas.

El criterio de rendimiento será que el p95 posterior no empeore más de 20%.
También se comprobarán errores, cantidad de resultados y similitudes. La
ingesta será un proceso operativo explícito, no parte del arranque del
servicio. Si el volumen futuro lo justifica, se analizará el plan de consulta
y se evaluará un índice vectorial, pero no se introduce como requisito de esta
fase.

## Alcance fuera de esta fase

No se descargarán fuentes remotas durante la ejecución, no se cambiará el
contrato del frontend, no se alterará el umbral RAG del chat y no se añadirá
automatización de ingesta al despliegue.
