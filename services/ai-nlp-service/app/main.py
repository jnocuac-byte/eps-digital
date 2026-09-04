from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from .core import Orchestrator
from .core.logger import log_event, setup_logger
from .core.model_provider import build_fallback_model
from .agents.triage_agent import build_triage_agent
from .agents.scheduling_agent import build_scheduling_agent

from app.crud import (
    cerrar_conversacion,
    crear_clasificacion,
    crear_conversacion,
    crear_mensaje,
    get_clasificacion_by_conversacion,
    get_conversacion,
    get_conversaciones_by_usuario,
    get_mensajes_by_conversacion,
)
from .database import get_db, Base, engine
from .schemas import (
    ChatRequest,
    ChatResponse,
    ClasificacionSintomasResponse,
    ConversacionResponse,
    MensajeResponse,
)

from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos globales del servicio al arrancar."""
    setup_logger()
    log_event("MAIN", "INIT", "info", "Iniciando AI/NLP Service (Strands Agents)...")

    try:
        Base.metadata.create_all(bind=engine)
        log_event("MAIN", "INIT", "info", "Base de datos inicializada")
    except Exception as exc:
        log_event("MAIN", "INIT", "error", f"Error al inicializar la base de datos: {exc}")
        raise RuntimeError(f"Error al inicializar la base de datos: ") from exc

    # Inicializar ModelRouter con fallback multi-provider
    try:
        app.state.model = build_fallback_model()
    except ValueError as exc:
        log_event("MAIN", "INIT", "warning", f"ModelRouter no disponible: {exc}")
        app.state.model = None

    # Inicializar agentes Strands y orquestador
    if app.state.model:
        triage_agent = build_triage_agent(app.state.model)
        scheduling_agent = build_scheduling_agent(app.state.model)
        app.state.orchestrator = Orchestrator(triage_agent, scheduling_agent)
        log_event("MAIN", "INIT", "info", "Orquestador Strands Agents inicializado")
    else:
        app.state.orchestrator = None

    # URL del servicio de citas
    app.state.citas_service_url = os.getenv("CITAS_SERVICE_URL")
    if app.state.citas_service_url:
        log_event("MAIN", "INIT", "info", f"Citas Service URL configurado: {app.state.citas_service_url}")

    log_event("MAIN", "INIT", "info", "AI/NLP Service listo")
    yield


app = FastAPI(
    title="AI/NLP Service",
    description="Servicio de chat y clasificacion de sintomas para EPS.",
    version="3.0.0",
    lifespan=lifespan,
)

origins = [
    "https://eps-digital-cn2h.onrender.com",
    "https://eps-digital-cn2h.onrender.com/",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5173/",
    "http://127.0.0.1:5173/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-User-ID"],
    max_age=600,
)


def _mapear_historial_a_mensajes_llm(mensajes_db: list[Any]) -> list[dict[str, str]]:
    """Convierte mensajes persistidos al formato role/content del modelo."""
    history: list[dict[str, str]] = []
    for mensaje in mensajes_db:
        if mensaje.remitente == "usuario":
            role = "user"
        elif mensaje.remitente == "asistente":
            role = "assistant"
        else:
            role = "user"

        history.append({"role": role, "content": mensaje.contenido})
    return history


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def post_chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Gestiona el flujo conversacional con orquestador multi-agente Strands."""
    t0 = time.time()
    log_event(
        "MAIN", "REQUEST", "info",
        f"POST /chat msg='{payload.mensaje[:50]}...' "
        f"conv={payload.conversacion_id or 'nueva'}"
    )

    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orquestador no disponible. Verifica GROQ_API_KEY o GEMINI_API_KEY.",
        )

    try:
        # 1. Gestionar conversacion
        if payload.conversacion_id is None:
            usuario_id = payload.usuario_id or UUID(
                "00000000-0000-0000-0000-000000000000"
            )
            conversacion = crear_conversacion(db, usuario_id=usuario_id)
            log_event("MAIN", "CONV", "info", f"Nueva conversacion: {conversacion.conversacion_id}")
        else:
            conversacion = get_conversacion(db, payload.conversacion_id)
            if conversacion is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversacion no encontrada",
                )
            if conversacion.estado == "cerrada":
                log_event("MAIN", "CONV", "warning", f"Conversacion cerrada: {payload.conversacion_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "La conversacion se encuentra cerrada. "
                        "Inicie una nueva interaccion sin conversacion_id."
                    ),
                )
            log_event("MAIN", "CONV", "debug", f"Conversacion existente: {conversacion.conversacion_id}")

        # 2. Persistir mensaje del usuario
        crear_mensaje(
            db,
            conversacion_id=conversacion.conversacion_id,
            remitente="usuario",
            contenido=payload.mensaje,
        )

        # 3. Construir historial (sliding window de 6 mensajes)
        historial_db = get_mensajes_by_conversacion(
            db, conversacion.conversacion_id, limit=6
        )
        history = _mapear_historial_a_mensajes_llm(historial_db)

        # 4. Procesar con el orquestador Strands
        usuario_id_str = str(payload.usuario_id) if payload.usuario_id else None
        respuesta_texto, state = await orchestrator.process(
            conversation_id=str(conversacion.conversacion_id),
            message=payload.mensaje,
            history=history,
            usuario_id=usuario_id_str,
            db=db,
        )

        # 5. Persistir respuesta del asistente
        crear_mensaje(
            db,
            conversacion_id=conversacion.conversacion_id,
            remitente="asistente",
            contenido=respuesta_texto,
        )

        elapsed = round((time.time() - t0) * 1000)
        log_event(
            "MAIN", "RESPONSE", "info",
            f"Respuesta enviada ({len(respuesta_texto)} chars, {elapsed}ms) "
            f"conv={conversacion.conversacion_id}"
        )

        # 6. Construir clasificacion desde el estado del orquestador
        clasificacion_response: ClasificacionSintomasResponse | None = None
        if state.urgency_level and state.specialty_name:
            try:
                existente = get_clasificacion_by_conversacion(
                    db, conversacion.conversacion_id
                )
                if existente is None:
                    nueva = crear_clasificacion(
                        db,
                        {
                            "conversacion_id": conversacion.conversacion_id,
                            "terminos_identificados": (
                                [state.symptoms_summary]
                                if state.symptoms_summary
                                else None
                            ),
                            "especialidad_sugerida": state.specialty_name,
                            "nivel_urgencia": state.urgency_level,
                            "confianza_modelo": 0.85,
                        },
                    )
                    clasificacion_response = (
                        ClasificacionSintomasResponse.model_validate(nueva)
                    )
                else:
                    existente.especialidad_sugerida = state.specialty_name
                    existente.nivel_urgencia = state.urgency_level
                    if state.symptoms_summary:
                        existente.terminos_identificados = [state.symptoms_summary]
                    db.commit()
                    db.refresh(existente)
                    clasificacion_response = (
                        ClasificacionSintomasResponse.model_validate(existente)
                    )
            except Exception as exc:
                log_event("MAIN", "DB", "warning", f"Error guardando clasificacion: {exc}")

        return ChatResponse(
            respuesta=respuesta_texto,
            conversacion_id=conversacion.conversacion_id,
            clasificacion=clasificacion_response,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno en /chat: {exc}",
        ) from exc


@app.get(
    "/chat/conversaciones/{usuario_id}",
    response_model=list[ConversacionResponse],
    tags=["chat"],
)
def listar_conversaciones(
    usuario_id: UUID, db: Session = Depends(get_db)
) -> list[ConversacionResponse]:
    """Lista conversaciones de un usuario."""
    conversaciones = get_conversaciones_by_usuario(db, usuario_id=usuario_id)
    return [ConversacionResponse.model_validate(c) for c in conversaciones]


@app.get(
    "/chat/conversacion/{conversacion_id}/mensajes",
    response_model=list[MensajeResponse],
    tags=["chat"],
)
def listar_mensajes(
    conversacion_id: UUID, db: Session = Depends(get_db)
) -> list[MensajeResponse]:
    """Lista mensajes de una conversacion."""
    conversacion = get_conversacion(db, conversacion_id)
    if conversacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversacion no encontrada",
        )

    mensajes = get_mensajes_by_conversacion(
        db, conversacion_id=conversacion_id
    )
    return [MensajeResponse.model_validate(m) for m in mensajes]


@app.post(
    "/chat/conversacion/{conversacion_id}/cerrar",
    response_model=ConversacionResponse,
    tags=["chat"],
)
def cerrar_chat_conversacion(
    conversacion_id: UUID, db: Session = Depends(get_db)
) -> ConversacionResponse:
    """Cierra una conversacion activa."""
    try:
        conversacion = cerrar_conversacion(db, conversacion_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return ConversacionResponse.model_validate(conversacion)


@app.get(
    "/chat/clasificacion/{conversacion_id}",
    response_model=ClasificacionSintomasResponse | None,
    tags=["chat"],
)
def get_clasificacion(
    conversacion_id: UUID, db: Session = Depends(get_db)
) -> ClasificacionSintomasResponse | None:
    """Obtiene la clasificacion de sintomas de una conversacion."""
    conversacion = get_conversacion(db, conversacion_id)
    if conversacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversacion no encontrada",
        )

    clasificacion = get_clasificacion_by_conversacion(db, conversacion_id)
    if clasificacion is None:
        return None

    return ClasificacionSintomasResponse.model_validate(clasificacion)
