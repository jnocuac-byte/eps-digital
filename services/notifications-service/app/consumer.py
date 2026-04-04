import json
import logging
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

logger = logging.getLogger(__name__)

RABBITMQ_DEFAULT_URL = "amqps://jyzkesmj:xTxbKJtX0yD97CnGVgCMxTDRATEAszTY@shark.rmq.cloudamqp.com/jyzkesmj"
COLAS_EVENTOS = (
	"cita_confirmada",
	"cita_cancelada",
	"cita_recordatorio",
	"cuenta_creada",
)


def configurar_rabbitmq() -> Tuple[pika.BlockingConnection, str]:
	"""Conecta a RabbitMQ y retorna conexión y cola principal."""
	load_dotenv()
	rabbitmq_url = os.getenv("RABBITMQ_URL", RABBITMQ_DEFAULT_URL)

	params = pika.URLParameters(rabbitmq_url)
	params.heartbeat = 30
	params.blocked_connection_timeout = 30
	params.socket_timeout = 30
	params.connection_attempts = 3
	params.retry_delay = 3

	connection = pika.BlockingConnection(params)
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
	"""Procesa mensaje de RabbitMQ y envía el correo según el evento."""
	del properties

	event_type = getattr(method, "routing_key", "") or ""
	try:
		payload: Dict[str, Any] = json.loads(body.decode("utf-8"))
	except Exception:
		logger.exception("Mensaje inválido en cola %s: %s", event_type, body)
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	event_type = _str_value(payload, "evento", event_type) or _str_value(
		payload, "tipo_evento", event_type
	)
	destinatario = _str_value(payload, "email") or _str_value(payload, "destinatario")

	if not destinatario:
		logger.error("Evento %s sin email destinatario: %s", event_type, payload)
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	asunto = ""
	contenido_html = ""

	try:
		if event_type == "cita_confirmada":
			asunto = "Confirmación de cita - EPS Digital"
			contenido_html = confirmacion_cita(
				nombre=_str_value(payload, "nombre", "Usuario"),
				fecha=_str_value(payload, "fecha"),
				hora=_str_value(payload, "hora"),
				especialidad=_str_value(payload, "especialidad"),
				sede=_str_value(payload, "sede"),
			)
		elif event_type == "cita_cancelada":
			asunto = "Cancelación de cita - EPS Digital"
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
			logger.warning("Evento no soportado: %s. Payload: %s", event_type, payload)
			ch.basic_ack(delivery_tag=method.delivery_tag)
			return

		enviado = enviar_correo(
			destinatario=destinatario,
			asunto=asunto,
			contenido_html=contenido_html,
		)
		if not enviado:
			logger.error(
				"Falló el envío de correo para evento %s a %s.",
				event_type,
				destinatario,
			)
	except Exception:
		# Nunca detenemos el consumidor por errores de procesamiento/envío.
		logger.exception("Error procesando evento %s: %s", event_type, payload)
	finally:
		ch.basic_ack(delivery_tag=method.delivery_tag)


def iniciar_consumidor() -> None:
	"""Inicia el consumidor en bucle infinito con reconexión automática."""
	configurar_sendgrid()

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

			logger.info(
				"Consumidor iniciado. Cola principal: %s. Escuchando: %s",
				cola_principal,
				", ".join(COLAS_EVENTOS),
			)
			channel.start_consuming()
		except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelClosedByBroker):
			logger.exception(
				"Conexión RabbitMQ caída. Reintentando en 5 segundos..."
			)
			time.sleep(5)
		except KeyboardInterrupt:
			logger.info("Consumidor detenido manualmente.")
			break
		except Exception:
			logger.exception("Error inesperado en consumidor. Reintentando en 5 segundos...")
			time.sleep(5)
		finally:
			if connection and connection.is_open:
				try:
					connection.close()
				except Exception:
					logger.exception("No se pudo cerrar conexión RabbitMQ limpiamente.")


def start_background_consumer() -> threading.Thread:
	"""Ejecuta el consumidor en un thread daemon y retorna el thread."""
	thread = threading.Thread(
		target=iniciar_consumidor,
		name="rabbitmq-consumer",
		daemon=True,
	)
	thread.start()
	logger.info("Consumidor RabbitMQ ejecutándose en segundo plano.")
	return thread
