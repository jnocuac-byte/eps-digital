import json
import logging
import os
from typing import Any, Dict

import pika
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

RABBITMQ_DEFAULT_URL = "amqps://jyzkesmj:xTxbKJtX0yD97CnGVgCMxTDRATEAszTY@shark.rmq.cloudamqp.com/jyzkesmj"


def _get_rabbitmq_connection() -> pika.BlockingConnection:
    load_dotenv()
    rabbitmq_url = os.getenv("RABBITMQ_URL", RABBITMQ_DEFAULT_URL)
    params = pika.URLParameters(rabbitmq_url)
    params.heartbeat = 30
    params.blocked_connection_timeout = 30
    return pika.BlockingConnection(params)


def publicar_evento(evento: str, payload: Dict[str, Any]) -> bool:
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
        logger.info("Evento %s publicado a RabbitMQ: %s", evento, payload)
        return True
    except Exception:
        logger.exception("Error al publicar evento %s a RabbitMQ", evento)
        return False
    finally:
        if connection and connection.is_open:
            try:
                connection.close()
            except Exception:
                logger.exception("Error cerrando conexión RabbitMQ")