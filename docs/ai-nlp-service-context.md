# AI-NLP Service — Contexto de Arquitectura

## Estado actual (post-Fase 1)

El servicio de IA fue rediseñado de un monolito de prompting (`groq_client.py`, 433 líneas)
a una arquitectura modular con fallback multi-provider y base de conocimiento estructurada.

### Estructura de directorios

```
services/ai-nlp-service/app/
├── core/
│   └── llm_provider.py        # LLMProviderFactory con fallback
├── agents/
│   ├── tools.py               # Tool dispatch + 5 tools HTTP
│   └── triage/
│       ├── models/output.py   # RedFlagDetection, TriageAnalysis
│       └── prompt.py          # System prompt con knowledge inyectada
├── knowledge/
│   └── triage_guide.json      # Base de conocimiento (8 especialidades)
├── main.py                    # Endpoints FastAPI
├── models.py                  # SQLAlchemy: conversacion, mensaje, clasificacion_sintomas
├── schemas.py                 # Pydantic: ChatRequest/Response
├── crud.py                    # CRUD de conversaciones
├── prompts.py                 # Prompts legacy (compatibilidad)
└── database.py                # Engine/session
```

### LLMProviderFactory — Fallback automático

```python
from app.core import init_llm_factory

# En el lifespan de FastAPI:
app.state.llm_factory = init_llm_factory()

# En los endpoints:
factory = app.state.llm_factory
respuesta, provider = factory.complete(messages, max_tokens=400)
```

**Orden de prioridad:**
1. Google Gemini Flash (`gemini-2.0-flash`) — `GEMINI_API_KEY`
2. Groq Llama 3.3 70B (`llama-3.3-70b-versatile`) — `GROQ_API_KEY`
3. Cerebras Llama 3.1 8B (`llama-3.1-8b`) — `CEREBRAS_API_KEY`
4. Mistral Small (`mistral-small-latest`) — `MISTRAL_API_KEY`

Si un proveedor retorna 429/5xx, pasa al siguiente automáticamente. Mínimo 1 proveedor requerido.

### Contrato con el Frontend (INALTERABLE)

```typescript
// Frontend: apiClient.ts
aiApi.chat(mensaje: string, conversacion_id?: string, usuario_id?: string)
  → POST /chat { mensaje, conversacion_id?, usuario_id? }
  → { respuesta: string, conversacion_id: string, clasificacion?: ClasificacionSintomasResponse }
```

Los 4 endpoints GET se mantienen sin cambios.

### Tools del asistente (function calling)

| Tool | Servicio destino | Estado |
|------|-----------------|--------|
| `obtener_especialidades` | Catalog → `GET /especialidades` | Real |
| `obtener_medicos` | Catalog → `GET /especialidades/{id}/medicos` | Real |
| `obtener_sedes` | Catalog → `GET /sedes` | Real |
| `agendar_cita` | Citas → `POST /citas` (header `X-User-ID`) | Real |
| `obtener_disponibilidad_citas` | Mock (cupos fijos) | Simulado |

### Knowledge Base (`triage_guide.json`)

JSON con la guía de triaje de la EPS:
- 3 niveles de urgencia (urgente/prioritario/programable) según Resolución 5596
- 8 especialidades con ejemplos de síntomas y criterios de derivación
- 9 criterios de banderas rojas (urgencia vital)
- Reglas de negocio (max 1000 chars entrada, max 6 mensajes historial)

Se inyecta como contexto en el system prompt del agente de triaje.

### Modelos de salida del Triage

```python
class TriageAnalysis(BaseModel):
    nivel_urgencia: Literal["urgente", "prioritario", "programable"]
    especialidad_sugerida_id: str        # ej. "cardiologia"
    especialidad_sugerida_nombre: str    # ej. "Cardiología"
    resumen_clinico: str                 # Para el médico
    red_flag: RedFlagDetection           # Detección de urgencia vital
    confianza: float                     # 0.0 - 1.0
    explicacion_al_paciente: str         # Para el paciente
```

Se transforma a `ClasificacionSintomasResponse` para el contrato del Frontend.

---

## Roadmap

### Fase 1 (COMPLETADA) ✅
- [x] `LLMProviderFactory` con fallback Gemini→Groq→Cerebras→Mistral
- [x] Knowledge base `triage_guide.json` (8 especialidades)
- [x] Modelos Pydantic `TriageAnalysis`, `RedFlagDetection`
- [x] Eliminación de `groq_client.py` (monolito)
- [x] `agents/tools.py` (tool dispatch desacoplado)
- [x] System prompt del triaje con knowledge inyectada

### Fase 2 (PRÓXIMA)
- [ ] TriageAgent como clase independiente con estado propio
- [ ] SchedulingAgent para agendamiento de citas
- [ ] Orquestador (State Machine) para routing entre agentes
- [ ] Soporte nativo de tool_calls por provider en el factory
- [ ] CLI interactivo para pruebas (`tests/interactive_cli.py`)

### Fase 3 (FUTURA)
- [ ] Guardrails médicos (filtrar diagnósticos y recetas)
- [ ] Memoria de largo plazo (resumen de conversaciones previas)
- [ ] MCP servers para catálogo y citas (vs tools HTTP directas)
- [ ] Métricas de uso y latencia por proveedor

---

## Variables de entorno

| Variable | Obligatoria | Uso |
|----------|-------------|-----|
| `DATABASE_URL` | Sí | PostgreSQL `eps_ainlp` |
| `GROQ_API_KEY` | Sí | Fallback principal LLM |
| `GEMINI_API_KEY` | No | Prioridad 1 LLM |
| `CEREBRAS_API_KEY` | No | Prioridad 3 LLM |
| `MISTRAL_API_KEY` | No | Prioridad 4 LLM |
| `CATALOG_SERVICE_URL` | Sí | Tools de especialidades/médicos/sedes |
| `CITAS_SERVICE_URL` | Sí | Tool de agendado de citas |
| `JWT_SECRET_KEY` | No | Solo si se valida JWT internamente |

---

## Gotchas conocidos

- `prompts.py` tiene `MODEL_NAME = "gpt-4o-mini"` hardcodeado pero nunca se usa (legacy)
- `obtener_disponibilidad_citas` retorna cupos hardcodeados — conectar a catalog-service en Fase 2
- El `response_format={"type": "json_object"}` solo funciona en Groq; Gemini y otros lo ignoran
- La knowledge base se carga una vez al importar `prompt.py` (cache en memoria)
- `tests/ai-nlp-test.py` está vacío — crear CLI interactivo en Fase 2
