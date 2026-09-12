import json
import os
from typing import Any, Dict

import pika
from dotenv import load_dotenv

from app.core.logger import log_event

RABBITMQ_DEFAULT_URL = "amqps://jyzkesmj:xTxbKJtX0yD97CnGVgCMxTDRATEAszTY@shark.rmq.cloudamqp.com/jyzkesmj"


def _get_rabbitmq_connection() -> pika.BlockingConnection:
    load_dotenv()
    rabbitmq_url = os.getenv("RABBITMQ_URL", RABBITMQ_DEFAULT_URL)
    log_event("AUTH", "RABBITMQ", "debug", f"Conectando a RabbitMQ")
    params = pika.URLParameters(rabbitmq_url)
    params.heartbeat = 30
    params.blocked_connection_timeout = 30
    return pika.BlockingConnection(params)


def publicar_evento(evento: str, payload: Dict[str, Any]) -> bool:
    log_event("AUTH", "RABBITMQ", "info", f"Publicando evento={evento}")
    connection = None
    try:
        connection = _get_rabbitmq_connection()
        channel = connection.channel()

        channel.queue_declare(queue=evento, durable=True)

        channel.basic_publish(
            exchange="",
            routing_key=evento,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
        log_event("AUTH", "RABBITMQ", "info", f"Evento {evento} publicado correctamente")
        return True
    except Exception as exc:
        log_event("AUTH", "RABBITMQ", "error", f"Error publicando evento {evento}: {exc}")
        return False
    finally:
        if connection and connection.is_open:
            try:
                connection.close()
                log_event("AUTH", "RABBITMQ", "debug", "Conexion RabbitMQ cerrada")
            except Exception:
                log_event("AUTH", "RABBITMQ", "warning", "Error cerrando conexion RabbitMQ")