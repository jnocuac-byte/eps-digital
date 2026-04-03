from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from .groq_client import chat_completion, clasificar_sintomas, configurar_groq
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
from .prompts import get_assistant_tools
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
	try:
		Base.metadata.create_all(bind=engine)
	except Exception as exc:
		raise RuntimeError(f"Error al inicializar la base de datos: ") from exc
	
	app.state.openai_ready = False
	app.state.openai_error = ""
	try:
		configurar_groq()
		app.state.openai_ready = True
	except ValueError as exc:
		# Si falta API key, el servicio sigue arriba pero endpoints IA devuelven 503.
		app.state.openai_error = str(exc)
	yield


app = FastAPI(
	title="AI/NLP Service",
	description="Servicio de chat y clasificacion de sintomas para EPS.",
	version="1.0.0",
	lifespan=lifespan,
)

origins = [
    "https://eps-digital-cn2h.onrender.com",  # URL Render del frontend
    "http://localhost:5173",                # Probando en local con Vite
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"], # Permite GET, POST, OPTIONS, etc.
    allow_headers=["*"], # Permite todos los headers (Authorization, Content-Type, etc.)
)

def _asegurar_openai_disponible() -> None:
	"""Valida que Groq este configurado antes de invocar funciones de IA."""
	if not app.state.openai_ready:
		detalle = app.state.openai_error or "Groq no esta configurado."
		raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detalle)


def _es_mensaje_relevante_para_clasificacion(mensaje: str) -> bool:
	"""Heuristica simple para decidir si intentar clasificacion de sintomas."""
	texto = mensaje.lower().strip()
	if len(texto) < 8:
		return False

	palabras_clave = [
		"dolor",
		"fiebre",
		"tos",
		"sangrado",
		"mareo",
		"vomito",
		"nausea",
		"presion",
		"respirar",
		"sintoma",
	]
	return any(palabra in texto for palabra in palabras_clave)


def _mapear_historial_a_mensajes_llm(mensajes_db: list[Any]) -> list[dict[str, str]]:
    """Convierte mensajes persistidos al formato role/content del modelo."""
    history: list[dict[str, str]] = []
    for mensaje in mensajes_db:
        # Normalizar roles para Groq/OpenAI
        if mensaje.remitente == "usuario":
            role = "user"
        elif mensaje.remitente == "asistente":
            role = "assistant"
        else:
            role = "user"  # fallback seguro
        
        history.append({
            "role": role,
            "content": mensaje.contenido,
        })
    return history


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def post_chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
	"""Gestiona el flujo conversacional con persistencia y clasificacion opcional."""
	_asegurar_openai_disponible()

	try:
		if payload.conversacion_id is None:
			# A falta de usuario autenticado en este punto, se usa UUID nulo temporal.
			conversacion = crear_conversacion(db, usuario_id=UUID("00000000-0000-0000-0000-000000000000"))
		else:
			conversacion = get_conversacion(db, payload.conversacion_id)
			if conversacion is None:
				raise HTTPException(
					status_code=status.HTTP_404_NOT_FOUND,
					detail="Conversacion no encontrada",
				)

		# Guarda mensaje del usuario.
		crear_mensaje(
			db,
			conversacion_id=conversacion.conversacion_id,
			remitente="usuario",
			contenido=payload.mensaje,
		)

		# Toma ultimos 10 mensajes para contexto.
		historial = get_mensajes_by_conversacion(db, conversacion.conversacion_id, limit=10)
		messages = _mapear_historial_a_mensajes_llm(historial)

		respuesta_texto, _tool_call_data = chat_completion(
			messages=messages,
			tools=get_assistant_tools(),
		)

		# Guarda respuesta del asistente.
		crear_mensaje(
			db,
			conversacion_id=conversacion.conversacion_id,
			remitente="asistente",
			contenido=respuesta_texto,
		)

		clasificacion_response: ClasificacionSintomasResponse | None = None
		if _es_mensaje_relevante_para_clasificacion(payload.mensaje):
			clasificacion_json = clasificar_sintomas(payload.mensaje)
			confianza = clasificacion_json.get("confianza")
			confianza_modelo = float(confianza) if confianza is not None else None

			existente = get_clasificacion_by_conversacion(db, conversacion.conversacion_id)
			if existente is None:
				nueva_clasificacion = crear_clasificacion(
					db,
					{
						"conversacion_id": conversacion.conversacion_id,
						"terminos_identificados": clasificacion_json.get("terminos_identificados"),
						"especialidad_sugerida": clasificacion_json.get("especialidad_sugerida"),
						"nivel_urgencia": clasificacion_json.get("nivel_urgencia") or "programable",
						"confianza_modelo": confianza_modelo,
					},
				)
				clasificacion_response = ClasificacionSintomasResponse.model_validate(
					nueva_clasificacion
				)
			else:
				# Actualiza clasificacion existente por tratarse de relacion 1:1.
				existente.terminos_identificados = clasificacion_json.get("terminos_identificados")
				existente.especialidad_sugerida = clasificacion_json.get("especialidad_sugerida")
				existente.nivel_urgencia = clasificacion_json.get("nivel_urgencia") or "programable"
				existente.confianza_modelo = (
					Decimal(str(confianza_modelo)) if confianza_modelo is not None else None
				)
				db.commit()
				db.refresh(existente)
				clasificacion_response = ClasificacionSintomasResponse.model_validate(existente)

		return ChatResponse(
			respuesta=respuesta_texto,
			conversacion_id=conversacion.conversacion_id,
			clasificacion=clasificacion_response,
		)

	except HTTPException:
		raise
	except RuntimeError as exc:
		# Errores encapsulados del cliente Groq.
		raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error interno en /chat: {exc}",
		) from exc


@app.get("/chat/conversaciones/{usuario_id}", response_model=list[ConversacionResponse], tags=["chat"])
def listar_conversaciones(usuario_id: UUID, db: Session = Depends(get_db)) -> list[ConversacionResponse]:
	"""Lista conversaciones de un usuario."""
	conversaciones = get_conversaciones_by_usuario(db, usuario_id=usuario_id)
	return [ConversacionResponse.model_validate(c) for c in conversaciones]


@app.get(
	"/chat/conversacion/{conversacion_id}/mensajes",
	response_model=list[MensajeResponse],
	tags=["chat"],
)
def listar_mensajes(conversacion_id: UUID, db: Session = Depends(get_db)) -> list[MensajeResponse]:
	"""Lista mensajes de una conversacion."""
	conversacion = get_conversacion(db, conversacion_id)
	if conversacion is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversacion no encontrada")

	mensajes = get_mensajes_by_conversacion(db, conversacion_id=conversacion_id)
	return [MensajeResponse.model_validate(m) for m in mensajes]


@app.post(
	"/chat/conversacion/{conversacion_id}/cerrar",
	response_model=ConversacionResponse,
	tags=["chat"],
)
def cerrar_chat_conversacion(conversacion_id: UUID, db: Session = Depends(get_db)) -> ConversacionResponse:
	"""Cierra una conversacion activa."""
	try:
		conversacion = cerrar_conversacion(db, conversacion_id)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

	return ConversacionResponse.model_validate(conversacion)


@app.get(
	"/chat/clasificacion/{conversacion_id}",
	response_model=ClasificacionSintomasResponse | None,
	tags=["chat"],
)
def get_clasificacion(conversacion_id: UUID, db: Session = Depends(get_db)) -> ClasificacionSintomasResponse | None:
	"""Obtiene la clasificacion de sintomas de una conversacion."""
	conversacion = get_conversacion(db, conversacion_id)
	if conversacion is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversacion no encontrada")

	clasificacion = get_clasificacion_by_conversacion(db, conversacion_id)
	if clasificacion is None:
		return None

	return ClasificacionSintomasResponse.model_validate(clasificacion)
