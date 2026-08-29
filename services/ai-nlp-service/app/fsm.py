from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

# Misma zona horaria de operacion que appointments-service (ver AGENTS.md: nunca
# usar date.today()/datetime.now() desnudos para decisiones de negocio de citas).
ZONA_BOGOTA = ZoneInfo("America/Bogota")
ANTELACION_MINIMA_MINUTOS = 60

# Estados del flujo de agendado conversacional.
SIN_INTENCION = "sin_intencion"
ESPERANDO_ESPECIALIDAD = "esperando_especialidad"
ESPERANDO_MEDICO = "esperando_medico"
ESPERANDO_SEDE = "esperando_sede"
ESPERANDO_FECHA_HORA = "esperando_fecha_hora"
ESPERANDO_CONFIRMACION = "esperando_confirmacion"
AGENDADA = "agendada"

ORDEN_ESTADOS = [
	SIN_INTENCION,
	ESPERANDO_ESPECIALIDAD,
	ESPERANDO_MEDICO,
	ESPERANDO_SEDE,
	ESPERANDO_FECHA_HORA,
	ESPERANDO_CONFIRMACION,
	AGENDADA,
]

# Tool de catalogo que se debe consultar al ENTRAR a cada estado.
TOOL_DE_ENTRADA: dict[str, str] = {
	ESPERANDO_ESPECIALIDAD: "obtener_especialidades",
	ESPERANDO_MEDICO: "obtener_medicos",
	ESPERANDO_SEDE: "obtener_sedes",
}

# Campos del borrador que se completan al AVANZAR desde cada estado.
CAMPOS_DEL_PASO: dict[str, tuple[str, ...]] = {
	ESPERANDO_ESPECIALIDAD: ("especialidad_id", "especialidad_nombre"),
	ESPERANDO_MEDICO: ("medico_id", "medico_nombre"),
	ESPERANDO_SEDE: ("sede_id", "sede_nombre"),
	ESPERANDO_FECHA_HORA: ("fecha", "hora"),
}

TODOS_LOS_CAMPOS_DEL_BORRADOR = [
	"especialidad_id", "especialidad_nombre",
	"medico_id", "medico_nombre",
	"sede_id", "sede_nombre",
	"fecha", "hora",
	"opciones_mostradas",
]

EVENTOS_VALIDOS = {
	"iniciar_agendamiento",
	"consultar_citas",
	"avanzar",
	"retroceder_un_paso",
	"cancelar_todo",
	"respuesta_invalida",
	"no_aplica",
}

# Eventos que solo tienen sentido si el usuario esta autenticado (usuario_id real,
# no el UUID cero de sesiones anonimas): agendar y consultar citas propias.
EVENTOS_QUE_REQUIEREN_USUARIO = {"iniciar_agendamiento", "consultar_citas"}


@dataclass
class ResultadoTransicion:
	"""Resultado puro de aplicar un evento sobre un estado. No toca BD ni LLM."""

	estado_nuevo: str
	campos_a_limpiar: list[str] = field(default_factory=list)
	campos_a_setear: dict[str, Any] = field(default_factory=dict)
	debe_agendar: bool = False


def _indice(estado: str) -> int:
	return ORDEN_ESTADOS.index(estado)


def aplicar_evento(
	estado_actual: str,
	evento: str,
	seleccion: dict[str, Any] | None = None,
) -> ResultadoTransicion:
	"""Calcula la transicion de la FSM para un evento dado. Funcion pura y testeable."""
	if evento not in EVENTOS_VALIDOS:
		evento = "no_aplica"

	if evento == "cancelar_todo":
		if estado_actual == SIN_INTENCION:
			return ResultadoTransicion(estado_nuevo=SIN_INTENCION)
		return ResultadoTransicion(
			estado_nuevo=SIN_INTENCION,
			campos_a_limpiar=list(TODOS_LOS_CAMPOS_DEL_BORRADOR),
		)

	if evento == "retroceder_un_paso":
		if estado_actual in (SIN_INTENCION, AGENDADA):
			return ResultadoTransicion(estado_nuevo=estado_actual)
		nuevo_estado = ORDEN_ESTADOS[_indice(estado_actual) - 1]
		# Se limpia el campo que se completo AL ENTRAR al estado actual (el que
		# se eligio en nuevo_estado), no el del estado actual (que aun esta vacio).
		campo_a_deshacer = CAMPOS_DEL_PASO.get(nuevo_estado, ())
		return ResultadoTransicion(
			estado_nuevo=nuevo_estado,
			campos_a_limpiar=list(campo_a_deshacer) + ["opciones_mostradas"],
		)

	if evento == "iniciar_agendamiento":
		if estado_actual != SIN_INTENCION:
			return ResultadoTransicion(estado_nuevo=estado_actual)
		return ResultadoTransicion(estado_nuevo=ESPERANDO_ESPECIALIDAD)

	if evento == "avanzar":
		if estado_actual in (SIN_INTENCION, AGENDADA):
			return ResultadoTransicion(estado_nuevo=estado_actual)

		campos_del_paso = CAMPOS_DEL_PASO.get(estado_actual, ())
		campos_a_setear: dict[str, Any] = {}
		if seleccion and campos_del_paso:
			for campo in campos_del_paso:
				if seleccion.get(campo) is not None:
					campos_a_setear[campo] = seleccion[campo]

		if estado_actual == ESPERANDO_CONFIRMACION:
			return ResultadoTransicion(estado_nuevo=AGENDADA, debe_agendar=True)

		nuevo_estado = ORDEN_ESTADOS[_indice(estado_actual) + 1]
		return ResultadoTransicion(
			estado_nuevo=nuevo_estado,
			campos_a_limpiar=["opciones_mostradas"],
			campos_a_setear=campos_a_setear,
		)

	# respuesta_invalida / no_aplica: no hay transicion, se queda igual.
	return ResultadoTransicion(estado_nuevo=estado_actual)


def resolver_seleccion(
	estado: str,
	seleccion_texto: str | None,
	opciones: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
	"""Mapea el texto elegido por el usuario (numero o nombre) a id+nombre reales.

	Retorna None si no se pudo resolver contra las opciones mostradas, lo que
	debe interpretarse como una seleccion invalida (pedir de nuevo).
	"""
	if estado not in CAMPOS_DEL_PASO or estado == ESPERANDO_FECHA_HORA:
		return None
	if not seleccion_texto or not opciones:
		return None

	texto = seleccion_texto.strip().lower()
	campo_id, campo_nombre = CAMPOS_DEL_PASO[estado]

	if texto.isdigit():
		idx = int(texto) - 1
		if 0 <= idx < len(opciones):
			opcion = opciones[idx]
			return {campo_id: opcion.get("id"), campo_nombre: opcion.get("nombre")}
		return None

	for opcion in opciones:
		nombre = str(opcion.get("nombre", "")).lower()
		if nombre and (texto in nombre or nombre in texto):
			return {campo_id: opcion.get("id"), campo_nombre: opcion.get("nombre")}

	return None


def tools_permitidas(estado: str) -> list[str]:
	"""Nombres de tools de catalogo que corresponden al estado (para exponer al LLM)."""
	tool_entrada = TOOL_DE_ENTRADA.get(estado)
	return [tool_entrada] if tool_entrada else []


def validar_fecha_hora(fecha_str: str, hora_str: str) -> str | None:
	"""Valida fecha/hora propuestas por el usuario para una cita.

	Retorna None si son validas, o un mensaje de error en espanol listo para
	mostrar al usuario si no lo son. Usa America/Bogota (nunca datetime.now()
	desnudo) para ser consistente con las reglas de negocio de appointments-service
	y no dejar pasar una fecha que luego el servicio de citas rechazaria.
	"""
	try:
		fecha = date.fromisoformat(fecha_str)
	except (ValueError, TypeError):
		return "Esa fecha no es valida. ¿Podrías indicarla en formato AAAA-MM-DD?"

	try:
		hora_partes = hora_str.strip().split(":")
		hora = int(hora_partes[0])
		minuto = int(hora_partes[1])
		if not (0 <= hora <= 23 and 0 <= minuto <= 59):
			raise ValueError
	except (ValueError, TypeError, IndexError):
		return "Esa hora no es valida. ¿Podrías indicarla en formato HH:MM (24 horas)?"

	ahora_bogota = datetime.now(ZONA_BOGOTA)
	hoy_bogota = ahora_bogota.date()

	if fecha < hoy_bogota:
		return "No se pueden agendar citas en fechas pasadas. ¿Qué otra fecha te gustaría?"

	if fecha == hoy_bogota:
		limite = (ahora_bogota + timedelta(minutes=ANTELACION_MINIMA_MINUTOS)).time()
		if (hora, minuto) < (limite.hour, limite.minute):
			return (
				f"Para citas el mismo día se necesitan al menos {ANTELACION_MINIMA_MINUTOS} "
				"minutos de anticipación. ¿Qué otra hora te gustaría?"
			)

	return None


_INSTRUCCIONES_POR_ESTADO = {
	SIN_INTENCION: (
		"Conversa libremente. Si el usuario expresa que quiere agendar una cita o "
		"describe sintomas, orientalo pero NO inventes datos de agendado."
	),
	ESPERANDO_ESPECIALIDAD: (
		"Ya tienes la lista de especialidades en el contexto. Presentala numerada "
		"y pide que el usuario elija una por numero o nombre."
	),
	ESPERANDO_MEDICO: (
		"Ya tienes la lista de medicos para la especialidad elegida. Presentala "
		"numerada y pide que el usuario elija uno."
	),
	ESPERANDO_SEDE: (
		"Ya tienes la lista de sedes disponibles. Presentala numerada y pide que "
		"el usuario elija una."
	),
	ESPERANDO_FECHA_HORA: (
		"Pregunta la fecha (YYYY-MM-DD) y hora (HH:MM) deseadas para la cita."
	),
	ESPERANDO_CONFIRMACION: (
		"Resume TODOS los datos ya confirmados (especialidad, medico, sede, fecha, "
		"hora) y pide confirmacion explicita antes de agendar."
	),
	AGENDADA: (
		"La cita ya fue procesada. Informa el resultado (exito o error) en lenguaje "
		"natural, sin IDs tecnicos."
	),
}


def describir_estado(estado: str, borrador: dict[str, Any]) -> str:
	"""Construye una nota de contexto (system-only, nunca mostrada al usuario)."""
	partes = [f"[Estado interno del flujo de agendado: {estado}]"]

	resumen = []
	if borrador.get("especialidad_nombre"):
		resumen.append(f"especialidad={borrador['especialidad_nombre']}")
	if borrador.get("medico_nombre"):
		resumen.append(f"medico={borrador['medico_nombre']}")
	if borrador.get("sede_nombre"):
		resumen.append(f"sede={borrador['sede_nombre']}")
	if borrador.get("fecha"):
		resumen.append(f"fecha={borrador['fecha']}")
	if borrador.get("hora"):
		resumen.append(f"hora={borrador['hora']}")
	if resumen:
		partes.append(
			"Datos ya confirmados por el usuario (NO los vuelvas a preguntar, NO los "
			"cambies por tu cuenta): " + ", ".join(resumen)
		)

	opciones = borrador.get("opciones_mostradas")
	if opciones:
		lista = "\n".join(f"{i}. {o.get('nombre')}" for i, o in enumerate(opciones, start=1))
		partes.append(
			"Opciones disponibles para este paso (NUNCA muestres IDs, solo estos "
			f"nombres numerados):\n{lista}"
		)

	partes.append(_INSTRUCCIONES_POR_ESTADO.get(estado, ""))
	return "\n".join(p for p in partes if p)
