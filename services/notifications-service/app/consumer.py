import json
import os
import threading
import time
from typing import Any, Dict, Tuple

import pika
from dotenv import load_dotenv
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from .email_client import configurar_sendgrid, enviar_correo
from .templates import (
	bienvenida,
	cancelacion_cita,
	confirmacion_cita,
	recordatorio_cita,
)
from .core.logger import log_event

COLAS_EVENTOS = (
	"cita_confirmada",
	"cita_cancelada",
	"cita_recordatorio",
	"cuenta_creada",
)


def configurar_rabbitmq() -> Tuple[pika.BlockingConnection, str]:
	"""Conecta a RabbitMQ y retorna conexion y cola principal."""
	log_event("NOTIF", "RABBITMQ", "info", "Conectando a RabbitMQ")
	load_dotenv()
	rabbitmq_url = os.getenv("RABBITMQ_URL")

	if not rabbitmq_url:
		raise ValueError("RABBITMQ_URL no configurado")

	params = pika.URLParameters(rabbitmq_url)
	params.heartbeat = 30
	params.blocked_connection_timeout = 30
	params.socket_timeout = 30
	params.connection_attempts = 3
	params.retry_delay = 3

	connection = pika.BlockingConnection(params)
	log_event("NOTIF", "RABBITMQ", "info", "RabbitMQ conectado")
	return connection, COLAS_EVENTOS[0]


def _str_value(payload: Dict[str, Any], key: str, default: str = "") -> str:
	value = payload.get(key, default)
	return str(value) if value is not None else default


def callback(
	ch: BlockingChannel,
	method: Basic.Deliver,
	properties: BasicProperties,
	body: bytes,
) -> None:
	"""Procesa mensaje de RabbitMQ y envia el correo segun el evento."""
	del properties

	event_type = getattr(method, "routing_key", "") or ""
	log_event("NOTIF", "RABBITMQ", "info", f"Mensaje recibido en cola={event_type}")
	try:
		payload: Dict[str, Any] = json.loads(body.decode("utf-8"))
	except Exception:
		log_event("NOTIF", "RABBITMQ", "error", f"Mensaje invalido en cola {event_type}: {body}")
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	event_type = _str_value(payload, "evento", event_type) or _str_value(
		payload, "tipo_evento", event_type
	)
	destinatario = _str_value(payload, "email") or _str_value(payload, "destinatario")

	if not destinatario:
		log_event("NOTIF", "RABBITMQ", "warning", f"Evento {event_type} sin email destinatario")
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	asunto = ""
	contenido_html = ""

	try:
		if event_type == "cita_confirmada":
			asunto = "Confirmacion de cita - EPS Digital"
			contenido_html = confirmacion_cita(
				nombre=_str_value(payload, "nombre", "Usuario"),
				fecha=_str_value(payload, "fecha"),
				hora=_str_value(payload, "hora"),
				especialidad=_str_value(payload, "especialidad"),
				sede=_str_value(payload, "sede"),
			)
		elif event_type == "cita_cancelada":
			asunto = "Cancelacion de cita - EPS Digital"
			contenido_html = cancelacion_cita(
				nombre=_str_value(payload, "nombre", "Usuario"),
				fecha=_str_value(payload, "fecha"),
				hora=_str_value(payload, "hora"),
				especialidad=_str_value(payload, "especialidad"),
			)
		elif event_type == "cita_recordatorio":
			asunto = "Recordatorio de cita - EPS Digital"
			contenido_html = recordatorio_cita(
				nombre=_str_value(payload, "nombre", "Usuario"),
				fecha=_str_value(payload, "fecha"),
				hora=_str_value(payload, "hora"),
				especialidad=_str_value(payload, "especialidad"),
				sede=_str_value(payload, "sede"),
			)
		elif event_type == "cuenta_creada":
			asunto = "Bienvenido a EPS Digital"
			contenido_html = bienvenida(
				nombre=_str_value(payload, "nombre", "Usuario")
			)
		else:
			log_event("NOTIF", "RABBITMQ", "warning", f"Evento no soportado: {event_type}")
			ch.basic_ack(delivery_tag=method.delivery_tag)
			return

		log_event("NOTIF", "EMAIL", "info", f"Enviando correo para evento={event_type} a={destinatario}")
		enviado = enviar_correo(
			destinatario=destinatario,
			asunto=asunto,
			contenido_html=contenido_html,
		)
		if not enviado:
			log_event("NOTIF", "EMAIL", "error", f"Fallo envio de correo para evento {event_type} a {destinatario}")
		else:
			log_event("NOTIF", "EMAIL", "info", f"Correo enviado para evento={event_type} a={destinatario}")
	except Exception as exc:
		log_event("NOTIF", "RABBITMQ", "error", f"Error procesando evento {event_type}: {exc}")
	finally:
		ch.basic_ack(delivery_tag=method.delivery_tag)


def iniciar_consumidor() -> None:
	"""Inicia el consumidor en bucle infinito con reconexion automatica."""
	log_event("NOTIF", "RABBITMQ", "info", "Iniciando consumidor RabbitMQ")
	configurar_sendgrid()

	intentos_fallidos = 0

	while True:
		connection: pika.BlockingConnection | None = None
		try:
			connection, cola_principal = configurar_rabbitmq()
			channel = connection.channel()

			for cola in COLAS_EVENTOS:
				channel.queue_declare(queue=cola, durable=True)
				channel.basic_consume(
					queue=cola,
					on_message_callback=callback,
					auto_ack=False,
				)

			log_event("NOTIF", "RABBITMQ", "info", f"Consumidor activo. Colas: {', '.join(COLAS_EVENTOS)}")
			intentos_fallidos = 0
			channel.start_consuming()
		except KeyboardInterrupt:
			log_event("NOTIF", "RABBITMQ", "info", "Consumidor detenido manualmente")
			break
		except Exception as exc:
			intentos_fallidos += 1
			backoff = min(5 * (2 ** (intentos_fallidos - 1)), 30)
			if intentos_fallidos == 1 or intentos_fallidos % 5 == 0:
				log_event(
					"NOTIF", "RABBITMQ", "error",
					f"Conexion RabbitMQ fallida (intento {intentos_fallidos}). "
					f"Reintentando en {backoff}s... ({exc})",
				)
			else:
				log_event(
					"NOTIF", "RABBITMQ", "debug",
					f"Reconexion {intentos_fallidos}, backoff {backoff}s",
				)
			time.sleep(backoff)
		finally:
			if connection and connection.is_open:
				try:
					connection.close()
				except Exception:
					log_event("NOTIF", "RABBITMQ", "warning", "No se pudo cerrar conexion RabbitMQ limpiamente")


def start_background_consumer() -> threading.Thread | None:
	"""Ejecuta el consumidor en un thread daemon y retorna el thread.

	Si RABBITMQ_ENABLED=false, no arranca el hilo.
	"""
	load_dotenv()
	if os.getenv("RABBITMQ_ENABLED", "true").lower() == "false":
		log_event("NOTIF", "RABBITMQ", "info", "Consumidor RabbitMQ deshabilitado (RABBITMQ_ENABLED=false)")
		return None

	thread = threading.Thread(
		target=iniciar_consumidor,
		name="rabbitmq-consumer",
		daemon=True,
	)
	thread.start()
	log_event("NOTIF", "RABBITMQ", "info", "Consumidor RabbitMQ ejecutandose en segundo plano")
	return thread
