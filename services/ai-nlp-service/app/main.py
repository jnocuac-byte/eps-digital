from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import fsm
from .groq_client import (
	chat_completion,
	clasificar_evento_fsm,
	clasificar_sintomas,
	configurar_groq,
	consultar_citas_del_usuario,
	ejecutar_funcion,
)
from .prompts import SYSTEM_PROMPT as _mensaje_sistema_base

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# UUID centinela para conversaciones sin usuario autenticado (ver post_chat).
ANONIMO_UUID = UUID("00000000-0000-0000-0000-000000000000")
from app.crud import (
	actualizar_borrador,
	cerrar_conversacion,
	crear_clasificacion,
	crear_conversacion,
	crear_mensaje,
	get_clasificacion_by_conversacion,
	get_conversacion,
	get_conversaciones_by_usuario,
	get_mensajes_by_conversacion,
	get_or_create_borrador,
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
	try:
		Base.metadata.create_all(bind=engine)
	except Exception as exc:
		raise RuntimeError(f"Error al inicializar la base de datos: ") from exc

	app.state.openai_ready = False
	app.state.openai_error = ""
	app.state.citas_service_url = None

	try:
		configurar_groq()
		app.state.openai_ready = True
	except ValueError as exc:
		app.state.openai_error = str(exc)

	citas_url = os.getenv("CITAS_SERVICE_URL")
	if citas_url:
		app.state.citas_service_url = citas_url
		logger.info(f"Citas Service URL configurado: {citas_url}")
	else:
		logger.warning("CITAS_SERVICE_URL no configurado. Funciones de citas no disponibles.")

	yield


app = FastAPI(
	title="AI/NLP Service",
	description="Servicio de chat y clasificacion de sintomas para EPS.",
	version="1.0.0",
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


def _normalizar_opciones(tool_name: str, resultado: dict[str, Any]) -> list[dict[str, Any]]:
    """Convierte el resultado crudo de una tool de catalogo en opciones id+nombre."""
    if not resultado.get("ok"):
        return []

    if tool_name == "obtener_especialidades":
        items = resultado.get("especialidades") or []
        return [
            {"id": str(i.get("especialidad_id")), "nombre": i.get("nombre")}
            for i in items
        ]

    if tool_name == "obtener_medicos":
        items = resultado.get("medicos") or []
        return [
            {
                "id": str(i.get("medico_id")),
                "nombre": f"{i.get('nombres', '')} {i.get('apellidos', '')}".strip(),
            }
            for i in items
        ]

    if tool_name == "obtener_sedes":
        items = resultado.get("sedes") or []
        return [
            {"id": str(i.get("sede_id")), "nombre": i.get("nombre")}
            for i in items
        ]

    return []


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
			usuario_id = payload.usuario_id or ANONIMO_UUID
			conversacion = crear_conversacion(db, usuario_id=usuario_id)
		else:
			conversacion = get_conversacion(db, payload.conversacion_id)
			if conversacion is None:
				raise HTTPException(
					status_code=status.HTTP_404_NOT_FOUND,
					detail="Conversacion no encontrada",
				)

		crear_mensaje(
			db,
			conversacion_id=conversacion.conversacion_id,
			remitente="usuario",
			contenido=payload.mensaje,
		)

		# --- FSM de agendado: decide el estado ANTES de pedirle texto al LLM ---
		borrador = get_or_create_borrador(db, conversacion.conversacion_id)
		# Preferimos el usuario_id de la conversacion persistida (estable durante
		# todo el flujo) sobre el del request puntual: asi un cliente que por
		# error omita usuario_id en un mensaje a mitad de flujo (bug de frontend,
		# reintento manual, etc.) no tumba un agendado que ya iba autenticado
		# desde el inicio. Si la conversacion arranco anonima, se acepta el
		# usuario_id del request como "login tardio" dentro de la misma charla.
		if conversacion.usuario_id != ANONIMO_UUID:
			usuario_id_autenticado = str(conversacion.usuario_id)
		elif payload.usuario_id:
			usuario_id_autenticado = str(payload.usuario_id)
		else:
			usuario_id_autenticado = None

		evento_json = clasificar_evento_fsm(
			estado_actual=borrador.estado,
			mensaje=payload.mensaje,
			opciones_mostradas=borrador.opciones_mostradas,
		)
		logger.info(f"Evento FSM clasificado: {evento_json} (estado actual: {borrador.estado})")

		# Agendar o consultar citas requiere una sesion autenticada real: una
		# sesion anonima (sin usuario_id) no debe poder crear ni leer citas de
		# nadie. Se degrada el evento y se le pide al usuario iniciar sesion.
		requiere_login = False
		if evento_json["evento"] in fsm.EVENTOS_QUE_REQUIEREN_USUARIO and not usuario_id_autenticado:
			requiere_login = True
			evento_json["evento"] = "no_aplica"

		# "Consultar mis citas" no es un paso de la FSM de agendado: es una
		# consulta de solo lectura que se responde con datos reales y no mueve
		# el estado del borrador (se trata como no_aplica para la FSM).
		resultado_consulta_citas: dict[str, Any] | None = None
		if evento_json["evento"] == "consultar_citas":
			resultado_consulta_citas = consultar_citas_del_usuario(usuario_id_autenticado)
			evento_json["evento"] = "no_aplica"

		seleccion_resuelta: dict[str, Any] | None = None
		mensaje_validacion_fecha: str | None = None
		if evento_json["evento"] == "avanzar":
			if borrador.estado == fsm.ESPERANDO_FECHA_HORA:
				if evento_json.get("fecha") and evento_json.get("hora"):
					mensaje_validacion_fecha = fsm.validar_fecha_hora(evento_json["fecha"], evento_json["hora"])
					if mensaje_validacion_fecha is None:
						seleccion_resuelta = {"fecha": evento_json["fecha"], "hora": evento_json["hora"]}
					else:
						evento_json["evento"] = "respuesta_invalida"
				else:
					evento_json["evento"] = "respuesta_invalida"
			else:
				seleccion_resuelta = fsm.resolver_seleccion(
					borrador.estado, evento_json.get("seleccion_texto"), borrador.opciones_mostradas,
				)
				if seleccion_resuelta is None and borrador.estado in fsm.CAMPOS_DEL_PASO:
					evento_json["evento"] = "respuesta_invalida"

		transicion = fsm.aplicar_evento(borrador.estado, evento_json["evento"], seleccion_resuelta)
		borrador = actualizar_borrador(
			db, borrador,
			estado=transicion.estado_nuevo,
			campos_a_limpiar=transicion.campos_a_limpiar,
			campos_a_setear=transicion.campos_a_setear,
		)

		resultado_agendado: dict[str, Any] | None = None
		snapshot_pre_agendado: dict[str, Any] | None = None

		if transicion.debe_agendar:
			snapshot_pre_agendado = {
				"especialidad_nombre": borrador.especialidad_nombre,
				"medico_nombre": borrador.medico_nombre,
				"sede_nombre": borrador.sede_nombre,
				"fecha": borrador.fecha,
				"hora": borrador.hora,
				"opciones_mostradas": None,
			}

			if not usuario_id_autenticado:
				# Defensa extra: nunca agendar sin una sesion autenticada real,
				# incluso si por alguna razon se llego a este punto sin ella
				# (ej. un borrador antiguo de antes de este cambio).
				resultado_agendado = {
					"ok": False,
					"error": "Necesitas iniciar sesión para poder agendar tu cita.",
				}
				borrador = actualizar_borrador(db, borrador, estado=fsm.ESPERANDO_CONFIRMACION)
			else:
				tipo_servicio = (
					"medicina_general"
					if (borrador.especialidad_nombre or "").strip().lower() == "medicina general"
					else "especialista"
				)
				resultado_agendado = ejecutar_funcion("agendar_cita", {
					"usuario_id": usuario_id_autenticado,
					"medico_id": borrador.medico_id,
					"especialidad_id": borrador.especialidad_id,
					"tipo_servicio": tipo_servicio,
					"fecha": borrador.fecha,
					"hora": borrador.hora,
					"sede_id": borrador.sede_id,
					"confirmado": True,
				})
				logger.info(f"Resultado de agendar_cita: {resultado_agendado}")

				if resultado_agendado.get("ok"):
					borrador = actualizar_borrador(
						db, borrador, estado=fsm.SIN_INTENCION,
						campos_a_limpiar=list(fsm.TODOS_LOS_CAMPOS_DEL_BORRADOR),
					)
				else:
					# El agendado fallo: se revierte a pedir confirmacion de nuevo.
					borrador = actualizar_borrador(db, borrador, estado=fsm.ESPERANDO_CONFIRMACION)

		# Si entramos a un estado que requiere catalogo y aun no lo tenemos, consultarlo ahora.
		error_catalogo: str | None = None
		tool_de_entrada = fsm.TOOL_DE_ENTRADA.get(borrador.estado)
		if tool_de_entrada and not borrador.opciones_mostradas:
			args_tool: dict[str, Any] = {}
			if tool_de_entrada == "obtener_medicos":
				args_tool = {"especialidad_id": borrador.especialidad_id}

			resultado_tool = ejecutar_funcion(tool_de_entrada, args_tool)
			opciones = _normalizar_opciones(tool_de_entrada, resultado_tool)
			if opciones:
				borrador = actualizar_borrador(
					db, borrador, estado=borrador.estado,
					campos_a_setear={"opciones_mostradas": opciones},
				)
			elif not resultado_tool.get("ok"):
				# El catalogo no respondio: no dejar que el LLM improvise una
				# lista inexistente. Se le avisa explicitamente del error.
				error_catalogo = resultado_tool.get(
					"error", "Hubo un problema consultando la información. ¿Querés intentar de nuevo?"
				)
			else:
				# Respondio bien pero no hay opciones (ej. especialidad sin
				# medicos asignados todavia).
				error_catalogo = (
					"No encontré opciones disponibles para este paso en este momento. "
					"¿Querés intentar con otra opción o usar el formulario directo?"
				)

		# --- El LLM ya no decide el flujo: solo redacta la respuesta en lenguaje natural ---
		if resultado_agendado is not None and resultado_agendado.get("ok") and snapshot_pre_agendado is not None:
			# El borrador ya se reseteo a sin_intencion; describir "agendada" con
			# los datos que se acaban de usar, no con el borrador ya vacio.
			estado_para_contexto = fsm.AGENDADA
			datos_para_contexto = snapshot_pre_agendado
		else:
			estado_para_contexto = borrador.estado
			datos_para_contexto = {
				"especialidad_nombre": borrador.especialidad_nombre,
				"medico_nombre": borrador.medico_nombre,
				"sede_nombre": borrador.sede_nombre,
				"fecha": borrador.fecha,
				"hora": borrador.hora,
				"opciones_mostradas": borrador.opciones_mostradas,
			}

		contexto_fsm = fsm.describir_estado(estado_para_contexto, datos_para_contexto)

		messages: list[dict[str, str]] = [{"role": "system", "content": _mensaje_sistema_base}]

		if estado_para_contexto == fsm.SIN_INTENCION:
			# Charla libre: aqui si ayuda dar contexto de turnos previos.
			historial = get_mensajes_by_conversacion(db, conversacion.conversacion_id, limit=6)
			messages.extend(_mapear_historial_a_mensajes_llm(historial))
		else:
			# Dentro del flujo de agendado NO se manda el historial completo: el
			# LLM tiende a repetir/continuar su propia respuesta anterior en vez
			# de reaccionar al nuevo estado (p.ej. tras una retractacion). El
			# borrador (servidor) ya es la unica fuente de verdad del progreso.
			messages.append({"role": "user", "content": payload.mensaje})

		if resultado_agendado is not None:
			messages.append({
				"role": "system",
				"content": (
					"Resultado del intento de agendar la cita (usalo para redactar la "
					f"respuesta, nunca muestres IDs tecnicos): {json.dumps(resultado_agendado, ensure_ascii=False)}"
				),
			})

		if resultado_consulta_citas is not None:
			messages.append({
				"role": "system",
				"content": (
					"El usuario pregunto por sus citas. Este es el resultado real de la "
					"consulta (usalo para responder, nunca muestres IDs tecnicos; si ok=false "
					"informa el error en lenguaje simple; si la lista de citas esta vacia dile "
					"que no tiene citas programadas): "
					f"{json.dumps(resultado_consulta_citas, ensure_ascii=False)}"
				),
			})

		if requiere_login:
			messages.append({
				"role": "system",
				"content": (
					"El usuario no tiene una sesion iniciada. Dile amablemente que necesita "
					"iniciar sesión para agendar o consultar sus citas."
				),
			})

		if mensaje_validacion_fecha:
			messages.append({
				"role": "system",
				"content": (
					f"La fecha/hora que dio el usuario no es valida. Motivo: "
					f"{mensaje_validacion_fecha} Explicaselo tal cual y pidele que intente de nuevo."
				),
			})

		if error_catalogo:
			messages.append({
				"role": "system",
				"content": (
					f"No se pudo obtener la información necesaria para este paso: {error_catalogo} "
					"NO inventes especialidades, medicos ni sedes que no te hayan sido confirmados "
					"por una funcion. Informa el problema tal cual y ofrece reintentar o usar el "
					"formulario directo."
				),
			})

		messages.append({
			"role": "system",
			"content": f"INSTRUCCION ACTUAL:\n{contexto_fsm}",
		})

		logger.info(f"Enviando chat con {len(messages)} mensajes (estado FSM: {borrador.estado}, sin tools)")
		respuesta_texto, _ = chat_completion(messages=messages, tools=None)
		logger.info(f"Respuesta generada: {respuesta_texto[:200]}...")

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
			estado_fsm=borrador.estado,
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
